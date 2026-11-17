package tools

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// TestRetrievalBench measures how often the fact a query was written for lands
// in the top results of each search mode. It runs only when
// GOMCP_RETRIEVAL_BENCH points at a directory holding corpus.jsonl
// ({"id","content"} per line) and queries.jsonl ({"set","q","want"} per line):
// the corpus is not part of the repository.
//
// The embedder is the pure-Go fallback, because that is the one a build
// without the onnx tag (the gateway's) runs in production.
func TestRetrievalBench(t *testing.T) {
	dir := os.Getenv("GOMCP_RETRIEVAL_BENCH")
	if dir == "" {
		t.Skip("GOMCP_RETRIEVAL_BENCH not set")
	}
	type doc struct {
		ID      string `json:"id"`
		Content string `json:"content"`
	}
	type query struct {
		Set  string `json:"set"`
		Q    string `json:"q"`
		Want string `json:"want"`
	}
	var docs []doc
	readJSONL(t, filepath.Join(dir, "corpus.jsonl"), func(b []byte) error {
		var d doc
		err := json.Unmarshal(b, &d)
		docs = append(docs, d)
		return err
	})
	var queries []query
	readJSONL(t, filepath.Join(dir, "queries.jsonl"), func(b []byte) error {
		var q query
		err := json.Unmarshal(b, &q)
		queries = append(queries, q)
		return err
	})

	db, err := sqlite.OpenMemory()
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewFactRepo(db)
	if err != nil {
		t.Fatal(err)
	}
	svc := NewFactService(repo, nil)
	svc.SetEmbedder(vectorstore.NewFTS5Embedder())
	ctx := context.Background()

	byFactID := make(map[string]string, len(docs))
	for _, d := range docs {
		fact, err := svc.AddFact(ctx, AddFactParams{Content: d.Content, Level: int(memory.LevelDomain), Domain: "bench"})
		if err != nil {
			t.Fatalf("add %s: %v", d.ID, err)
		}
		byFactID[fact.ID] = d.ID
	}

	if len(byFactID) != len(docs) {
		t.Fatalf("corpus folded on insert: %d documents, %d facts", len(docs), len(byFactID))
	}

	type tally struct {
		n, hit1, hit5, hit10 int
		rr                   float64
	}
	type variant struct {
		label  string
		mode   SearchMode
		weight float64
	}
	defaultWeight := degradedSemanticWeight
	t.Cleanup(func() { degradedSemanticWeight = defaultWeight })
	variants := []variant{{"keyword", ModeKeyword, 0}, {"semantic", ModeSemantic, 0}}
	for _, w := range []float64{1, 0.25, 0.1, 0} {
		variants = append(variants, variant{fmt.Sprintf("hybrid@%.2f", w), ModeHybrid, w})
	}
	results := map[string]map[string]*tally{}
	for _, q := range queries {
		if results[q.Set] == nil {
			results[q.Set] = map[string]*tally{}
		}
		for _, v := range variants {
			tl := results[q.Set][v.label]
			if tl == nil {
				tl = &tally{}
				results[q.Set][v.label] = tl
			}
			degradedSemanticWeight = v.weight
			facts, err := svc.SearchFactsWithMode(ctx, q.Q, 10, v.mode)
			if err != nil {
				t.Fatalf("%s %q: %v", v.label, q.Q, err)
			}
			tl.n++
			for rank, f := range facts {
				if byFactID[f.ID] != q.Want {
					continue
				}
				if rank < 1 {
					tl.hit1++
				}
				if rank < 5 {
					tl.hit5++
				}
				tl.hit10++
				tl.rr += 1 / float64(rank+1)
				break
			}
		}
	}

	sets := make([]string, 0, len(results))
	for s := range results {
		sets = append(sets, s)
	}
	sort.Strings(sets)
	fmt.Printf("retrieval bench: %d facts, %d queries\n", len(docs), len(queries))
	for _, s := range sets {
		for _, v := range variants {
			tl := results[s][v.label]
			fmt.Printf("BENCH set=%s mode=%s n=%d hit@1=%d hit@5=%d hit@10=%d mrr@10=%.3f\n",
				s, v.label, tl.n, tl.hit1, tl.hit5, tl.hit10, tl.rr/float64(tl.n))
		}
	}
}

func readJSONL(t *testing.T, path string, each func([]byte) error) {
	t.Helper()
	f, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 1<<20), 1<<24)
	for sc.Scan() {
		if len(sc.Bytes()) == 0 {
			continue
		}
		if err := each(sc.Bytes()); err != nil {
			t.Fatalf("%s: %v", path, err)
		}
	}
	if err := sc.Err(); err != nil {
		t.Fatal(err)
	}
}
