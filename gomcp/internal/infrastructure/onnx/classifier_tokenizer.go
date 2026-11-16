//go:build onnx

package onnx

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"strings"

	"golang.org/x/text/unicode/norm"
)

// SentencePiece Unigram tokenizer for mDeBERTa-v3 / DeBERTa-v2, loaded directly
// from a HuggingFace `tokenizer.json` artifact.
//
// WHY THIS EXISTS (WS3 honesty item #4): the previous DebertaTokenizer used a
// hash of each word as a stand-in token id. Those ids do NOT correspond to the
// model's embedding table, so even a correct .onnx produced meaningless logits —
// "active" garbage. This tokenizer loads the REAL vocab (token → log-prob) and
// reproduces the SentencePiece Unigram pipeline so token ids match the exported
// model. If the artifact is absent/malformed the constructor errors, and the
// caller keeps the classifier OFFLINE rather than emitting fabricated scores.
//
// Pipeline reproduced (matches the checkpoint's tokenizer.json):
//   normalizer : Strip → NFKC → collapse runs of 2+ spaces to one
//   pre-tokenize: Metaspace (space → "▁", prepend "▁")
//   model      : Unigram, Viterbi best-segmentation over vocab log-probs, unk_id
//   post       : [CLS] + ids + [SEP]
//
// PARITY CAVEAT (documented in docs/MODEL_ARTIFACT_CONTRACT.md): the reference
// HF tokenizer applies a 300KB+ "Precompiled" charsmap for normalization. We
// approximate it with Unicode NFKC, which is identical for the overwhelming
// majority of real inputs (ASCII + common scripts) but MAY differ on a handful
// of exotic codepoints. The export script emits a parity fixture so the operator
// can verify ID agreement before going live; if byte-exact parity on adversarial
// Unicode is required, swap in a cgo HF-tokenizer binding behind this same
// interface (NewSafetyClassifier is the only construction site).

// unigramVocabEntry mirrors one ["token", logprob] pair in tokenizer.json.
type unigramVocabEntry struct {
	token  string
	logits float64
}

// tokenizerJSON is the minimal subset of HF tokenizer.json we parse.
type tokenizerJSON struct {
	AddedTokens []struct {
		ID      int    `json:"id"`
		Content string `json:"content"`
		Special bool   `json:"special"`
	} `json:"added_tokens"`
	Model struct {
		Type  string            `json:"type"`
		UnkID *int              `json:"unk_id"`
		Vocab []json.RawMessage `json:"vocab"`
	} `json:"model"`
}

// UnigramTokenizer is a SentencePiece Unigram tokenizer.
type UnigramTokenizer struct {
	vocab     map[string]int     // piece → id
	scores    map[string]float64 // piece → log-prob (Viterbi weight)
	unkID     int
	clsID     int
	sepID     int
	padID     int
	maxLength int
	minScore  float64 // fallback penalty for single chars not in vocab
}

const metaspace = "▁" // "▁"

// NewUnigramTokenizerFromFile loads a tokenizer from a HF tokenizer.json path.
// It REQUIRES a real artifact — a missing/malformed file is an error so the
// classifier stays offline rather than tokenizing with a placeholder.
func NewUnigramTokenizerFromFile(path string, maxLength int) (*UnigramTokenizer, error) {
	if path == "" {
		return nil, fmt.Errorf("tokenizer path is empty: a real tokenizer.json matching the model vocab is required (set SAFETY_CLASSIFIER_VOCAB)")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read tokenizer %q: %w", path, err)
	}
	return newUnigramTokenizerFromBytes(data, maxLength)
}

func newUnigramTokenizerFromBytes(data []byte, maxLength int) (*UnigramTokenizer, error) {
	var tj tokenizerJSON
	if err := json.Unmarshal(data, &tj); err != nil {
		return nil, fmt.Errorf("parse tokenizer.json: %w", err)
	}
	if !strings.EqualFold(tj.Model.Type, "Unigram") {
		return nil, fmt.Errorf("unsupported tokenizer model type %q (this loader supports SentencePiece Unigram, e.g. mDeBERTa-v3)", tj.Model.Type)
	}
	if len(tj.Model.Vocab) == 0 {
		return nil, fmt.Errorf("tokenizer.json has empty model.vocab")
	}

	t := &UnigramTokenizer{
		vocab:     make(map[string]int, len(tj.Model.Vocab)),
		scores:    make(map[string]float64, len(tj.Model.Vocab)),
		unkID:     -1,
		clsID:     -1,
		sepID:     -1,
		padID:     -1,
		maxLength: maxLength,
		minScore:  math.Inf(1),
	}

	// Parse the vocab: each entry is a 2-tuple [piece, logprob].
	for i, raw := range tj.Model.Vocab {
		var pair []json.RawMessage
		if err := json.Unmarshal(raw, &pair); err != nil || len(pair) != 2 {
			return nil, fmt.Errorf("tokenizer.json vocab[%d] is not a [token, score] pair", i)
		}
		var piece string
		if err := json.Unmarshal(pair[0], &piece); err != nil {
			return nil, fmt.Errorf("tokenizer.json vocab[%d] token is not a string", i)
		}
		var score float64
		if err := json.Unmarshal(pair[1], &score); err != nil {
			return nil, fmt.Errorf("tokenizer.json vocab[%d] score is not a number", i)
		}
		// First occurrence wins (ids are positional).
		if _, exists := t.vocab[piece]; !exists {
			t.vocab[piece] = i
			t.scores[piece] = score
		}
		if score < t.minScore {
			t.minScore = score
		}
	}
	if math.IsInf(t.minScore, 1) {
		t.minScore = 0
	}

	// added_tokens override ids for special tokens (e.g. [PAD]/[CLS]/[SEP]/[UNK]).
	for _, at := range tj.AddedTokens {
		t.vocab[at.Content] = at.ID
		// Special tokens have score 0 in the vocab already; keep map consistent.
		if _, ok := t.scores[at.Content]; !ok {
			t.scores[at.Content] = 0
		}
	}

	// Resolve special-token ids. unk_id is mandatory for Unigram.
	if tj.Model.UnkID != nil {
		t.unkID = *tj.Model.UnkID
	}
	if id, ok := t.vocab["[UNK]"]; ok && t.unkID < 0 {
		t.unkID = id
	}
	t.clsID = t.lookupSpecial("[CLS]")
	t.sepID = t.lookupSpecial("[SEP]")
	t.padID = t.lookupSpecial("[PAD]")

	if t.unkID < 0 {
		return nil, fmt.Errorf("tokenizer.json missing an [UNK] token / unk_id (cannot tokenize safely)")
	}
	if t.clsID < 0 || t.sepID < 0 {
		return nil, fmt.Errorf("tokenizer.json missing [CLS]/[SEP] special tokens (DeBERTa post-processing requires them)")
	}
	if t.padID < 0 {
		t.padID = 0 // DeBERTa-v2 pad_token_id is 0 by convention.
	}
	return t, nil
}

func (t *UnigramTokenizer) lookupSpecial(tok string) int {
	if id, ok := t.vocab[tok]; ok {
		return id
	}
	return -1
}

// VocabSize returns the number of distinct pieces (excludes added-token holes).
func (t *UnigramTokenizer) VocabSize() int { return len(t.vocab) }

// Encode reproduces the SentencePiece Unigram pipeline and returns the
// [CLS] … [SEP] (padded) input_ids plus the attention mask.
func (t *UnigramTokenizer) Encode(text string) (inputIDs []int64, attentionMask []int64) {
	normalized := t.normalize(text)

	// Metaspace pre-tokenizer: prepend "▁" and replace spaces with "▁".
	// (prepend_scheme=always, replacement="▁")
	pre := metaspace + strings.ReplaceAll(normalized, " ", metaspace)

	pieces := t.viterbi(pre)

	// Build [CLS] + pieces + [SEP], truncating pieces to fit maxLength.
	budget := t.maxLength - 2
	if budget < 0 {
		budget = 0
	}
	if len(pieces) > budget {
		pieces = pieces[:budget]
	}

	ids := make([]int64, 0, t.maxLength)
	ids = append(ids, int64(t.clsID))
	for _, p := range pieces {
		ids = append(ids, int64(t.vocab[p]))
	}
	ids = append(ids, int64(t.sepID))

	mask := make([]int64, len(ids))
	for i := range mask {
		mask[i] = 1
	}

	// Pad to maxLength.
	for len(ids) < t.maxLength {
		ids = append(ids, int64(t.padID))
		mask = append(mask, 0)
	}
	return ids, mask
}

// normalize applies Strip → NFKC → collapse 2+ spaces. This approximates the
// reference "Precompiled" charsmap with Unicode NFKC (see PARITY CAVEAT above).
func (t *UnigramTokenizer) normalize(text string) string {
	s := strings.TrimSpace(text)
	s = norm.NFKC.String(s)
	// Collapse runs of 2+ ASCII spaces to one (Replace { {2,} } → " ").
	for strings.Contains(s, "  ") {
		s = strings.ReplaceAll(s, "  ", " ")
	}
	return s
}

// viterbi computes the maximum-log-probability segmentation of s over the vocab
// (the standard SentencePiece Unigram decoding). Substrings absent from the
// vocab fall back to single-character [UNK] with a penalty, mirroring how the
// reference handles out-of-vocab runes (byte_fallback is false for this model).
func (t *UnigramTokenizer) viterbi(s string) []string {
	if s == "" {
		return nil
	}
	runes := []rune(s)
	n := len(runes)

	// best[i] = best score for runes[:i]; back[i] = start index of the last piece.
	negInf := math.Inf(-1)
	best := make([]float64, n+1)
	back := make([]int, n+1)
	for i := 1; i <= n; i++ {
		best[i] = negInf
		back[i] = -1
	}
	best[0] = 0

	// Unknown single-char penalty: a bit worse than the rarest known piece so
	// known segmentations are always preferred when they exist.
	unkPenalty := t.minScore - 10.0

	for end := 1; end <= n; end++ {
		for start := 0; start < end; start++ {
			if best[start] == negInf {
				continue
			}
			piece := string(runes[start:end])
			score, ok := t.scores[piece]
			if !ok {
				// Only single-rune unknown pieces are allowed as a fallback,
				// matching SentencePiece (multi-rune unknowns are never emitted).
				if end-start != 1 {
					continue
				}
				score = unkPenalty
			}
			if cand := best[start] + score; cand > best[end] {
				best[end] = cand
				back[end] = start
			}
		}
	}

	// Reconstruct pieces; map unknown single-rune pieces to the [UNK] token.
	var rev []string
	for i := n; i > 0; {
		start := back[i]
		if start < 0 {
			// Should not happen (single-rune fallback guarantees a path), but
			// stay safe: emit [UNK] for the trailing rune and continue.
			start = i - 1
		}
		piece := string(runes[start:i])
		if _, known := t.vocab[piece]; known {
			rev = append(rev, piece)
		} else {
			rev = append(rev, "[UNK]")
		}
		i = start
	}

	// Reverse into forward order.
	for l, r := 0, len(rev)-1; l < r; l, r = l+1, r-1 {
		rev[l], rev[r] = rev[r], rev[l]
	}
	return rev
}
