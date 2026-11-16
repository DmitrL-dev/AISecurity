package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"sort"
	"strings"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

const (
	boundedSearchStoredRowHardMaxBytes      int64 = 16 * 1024 * 1024
	boundedSearchStoredSnapshotHardMaxBytes int64 = 32 * 1024 * 1024
	boundedSearchStoredSnapshotHardMaxRows        = 10_000
	boundedSearchStoredFactIDHardMaxBytes         = 256
)

// This expression intentionally uses octet_length(column), whose SQLite
// implementation can read TEXT/BLOB byte lengths from record metadata without
// loading the value. Do not replace it with length(cast(column AS blob)).
const boundedSearchStoredVariableBytesSQL = `
	COALESCE(octet_length(id), 0)
	+ COALESCE(octet_length(tenant_id), 0)
	+ COALESCE(octet_length(project_id), 0)
	+ COALESCE(octet_length(content), 0)
	+ COALESCE(octet_length(domain), 0)
	+ COALESCE(octet_length(module), 0)
	+ COALESCE(octet_length(code_ref), 0)
	+ COALESCE(octet_length(parent_id), 0)
	+ COALESCE(octet_length(embedding), 0)
	+ COALESCE(octet_length(ttl_config), 0)
	+ COALESCE(octet_length(created_at), 0)
	+ COALESCE(octet_length(valid_from), 0)
	+ COALESCE(octet_length(valid_until), 0)
	+ COALESCE(octet_length(source), 0)
	+ COALESCE(octet_length(session_id), 0)
	+ COALESCE(octet_length(origin), 0)`

type boundedSearchSnapshot struct {
	tx *sql.Tx
	sc rlmscope.Scope
}

// WithBoundedSearchSnapshot establishes a SQLite read snapshot with a
// metadata-only size preflight before the callback can select factColumns.
// Initial searches measure the whole exact non-session scope. Continuations
// pass their frozen IDs and therefore ignore unrelated post-freeze inserts.
func (r *FactRepo) WithBoundedSearchSnapshot(
	ctx context.Context,
	factIDs []string,
	run func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error),
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	if run == nil {
		return nil, nil, fmt.Errorf("bounded search callback is required")
	}
	sc, err := boundedSearchExactScope(ctx)
	if err != nil {
		return nil, nil, err
	}
	whereSQL, args, err := boundedSearchSelection(sc, factIDs)
	if err != nil {
		return nil, nil, err
	}
	tx, err := r.db.SqlDB().BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return nil, nil, fmt.Errorf("begin bounded search snapshot: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	var rowCount, maxIDBytes, maxRowBytes, totalBytes int64
	query := `WITH measured AS (
		SELECT octet_length(id) AS id_bytes,
			` + boundedSearchStoredVariableBytesSQL + ` AS stored_variable_bytes
		FROM hierarchical_facts
		WHERE ` + whereSQL + `
	)
	SELECT COUNT(*), COALESCE(MAX(id_bytes), 0),
		COALESCE(MAX(stored_variable_bytes), 0),
		COALESCE(SUM(stored_variable_bytes), 0)
	FROM measured`
	if err := tx.QueryRowContext(ctx, query, args...).Scan(
		&rowCount, &maxIDBytes, &maxRowBytes, &totalBytes,
	); err != nil {
		return nil, nil, fmt.Errorf("preflight bounded search snapshot: %w", err)
	}
	if maxIDBytes > boundedSearchStoredFactIDHardMaxBytes {
		return nil, &memory.BoundedSearchStoredOversize{
			Kind:           memory.BoundedSearchStoredIdentityOversizeKind,
			StoredBytes:    maxIDBytes,
			MaxStoredBytes: boundedSearchStoredFactIDHardMaxBytes,
		}, nil
	}
	if maxRowBytes > boundedSearchStoredRowHardMaxBytes {
		return nil, &memory.BoundedSearchStoredOversize{
			Kind:           memory.BoundedSearchStoredRowOversizeKind,
			StoredBytes:    maxRowBytes,
			MaxStoredBytes: boundedSearchStoredRowHardMaxBytes,
		}, nil
	}
	if totalBytes > boundedSearchStoredSnapshotHardMaxBytes {
		return nil, &memory.BoundedSearchStoredOversize{
			Kind:           memory.BoundedSearchStoredScopeOversizeKind,
			StoredBytes:    totalBytes,
			MaxStoredBytes: boundedSearchStoredSnapshotHardMaxBytes,
		}, nil
	}
	if rowCount > boundedSearchStoredSnapshotHardMaxRows {
		return nil, nil, fmt.Errorf("bounded search snapshot row count exceeds hard limit")
	}

	facts, err := run(&boundedSearchSnapshot{tx: tx, sc: sc})
	if err != nil {
		return nil, nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, nil, fmt.Errorf("commit bounded search snapshot: %w", err)
	}
	return facts, nil, nil
}

func boundedSearchExactScope(ctx context.Context) (rlmscope.Scope, error) {
	sc, err := rlmscope.Require(ctx)
	if err != nil {
		return rlmscope.Scope{}, err
	}
	if sc.IsDefault() {
		return rlmscope.RequireExactDefault(ctx)
	}
	return rlmscope.RequireExactProject(ctx)
}

func boundedSearchSelection(sc rlmscope.Scope, factIDs []string) (string, []any, error) {
	whereSQL := `tenant_id COLLATE BINARY = ?
		AND project_id COLLATE BINARY = ?
		AND (session_id IS NULL OR session_id COLLATE BINARY = '')`
	args := []any{sc.TenantID, sc.ProjectID}
	if factIDs == nil {
		return whereSQL, args, nil
	}
	if len(factIDs) == 0 || len(factIDs) > 100 {
		return "", nil, fmt.Errorf("frozen bounded search IDs must contain 1 through 100 values")
	}
	seen := make(map[string]struct{}, len(factIDs))
	placeholders := make([]string, len(factIDs))
	for index, id := range factIDs {
		if id == "" || len(id) > boundedSearchStoredFactIDHardMaxBytes {
			return "", nil, fmt.Errorf("invalid frozen bounded search fact ID")
		}
		if _, duplicate := seen[id]; duplicate {
			return "", nil, fmt.Errorf("duplicate frozen bounded search fact ID")
		}
		seen[id] = struct{}{}
		placeholders[index] = "?"
		args = append(args, id)
	}
	whereSQL += ` AND id COLLATE BINARY IN (` + strings.Join(placeholders, ",") + `)`
	return whereSQL, args, nil
}

func (s *boundedSearchSnapshot) Search(
	ctx context.Context,
	query string,
	limit int,
) ([]*memory.Fact, error) {
	if limit <= 0 {
		limit = 50
	}
	terms := searchTerms(query)
	phrase := strings.ToLower(strings.TrimSpace(query))
	if phrase == "" {
		return nil, nil
	}
	rows, err := s.tx.QueryContext(ctx, `SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND (session_id IS NULL OR session_id COLLATE BINARY = '')
          AND is_stale = 0 AND is_archived = 0`,
		s.sc.TenantID, s.sc.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("bounded keyword search: %w", err)
	}
	defer rows.Close()
	candidates, err := scanFacts(rows)
	if err != nil {
		return nil, err
	}
	type scored struct {
		fact  *memory.Fact
		score int
	}
	ranked := make([]scored, 0, len(candidates))
	for _, fact := range candidates {
		lowered := strings.ToLower(fact.Content)
		matched := 0
		for _, term := range terms {
			if strings.Contains(lowered, term) {
				matched++
			}
		}
		score := 0
		switch {
		case strings.Contains(lowered, phrase):
			score = 1_000_000 + matched
		case len(terms) > 0 && matched == len(terms):
			score = 1_000 + matched
		case matched > 0:
			score = matched
		}
		if score > 0 {
			ranked = append(ranked, scored{fact: fact, score: score})
		}
	}
	sort.SliceStable(ranked, func(i, j int) bool {
		if ranked[i].score != ranked[j].score {
			return ranked[i].score > ranked[j].score
		}
		return ranked[i].fact.ID < ranked[j].fact.ID
	})
	if limit > len(ranked) {
		limit = len(ranked)
	}
	out := make([]*memory.Fact, limit)
	for index := range out {
		out[index] = ranked[index].fact
	}
	return out, nil
}

func (s *boundedSearchSnapshot) SearchByVector(
	ctx context.Context,
	queryVec []float64,
	limit int,
) ([]*memory.Fact, error) {
	if len(queryVec) == 0 {
		return nil, nil
	}
	if limit <= 0 {
		limit = 50
	}
	rows, err := s.tx.QueryContext(ctx, `SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND embedding IS NOT NULL
		  AND is_archived = 0
		  AND (session_id IS NULL OR session_id COLLATE BINARY = '')
          AND is_stale = 0 AND is_archived = 0`,
		s.sc.TenantID, s.sc.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("bounded vector search: %w", err)
	}
	defer rows.Close()
	candidates, err := scanFacts(rows)
	if err != nil {
		return nil, err
	}
	type scored struct {
		fact       *memory.Fact
		similarity float64
	}
	ranked := make([]scored, 0, len(candidates))
	for _, fact := range candidates {
		if len(fact.Embedding) != len(queryVec) {
			continue
		}
		ranked = append(ranked, scored{
			fact: fact, similarity: vectorstore.CosineSimilarity(queryVec, fact.Embedding),
		})
	}
	// This deliberately matches legacy project-wide vector ordering, including
	// its lack of a tie-breaker.
	sort.Slice(ranked, func(i, j int) bool { return ranked[i].similarity > ranked[j].similarity })
	if limit > len(ranked) {
		limit = len(ranked)
	}
	out := make([]*memory.Fact, limit)
	for index := range out {
		out[index] = ranked[index].fact
	}
	return out, nil
}

func (s *boundedSearchSnapshot) Get(ctx context.Context, id string) (*memory.Fact, error) {
	return scanFact(s.tx.QueryRowContext(ctx, `SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE id COLLATE BINARY = ?
		  AND tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND (session_id IS NULL OR session_id COLLATE BINARY = '')
          AND is_stale = 0 AND is_archived = 0`,
		id, s.sc.TenantID, s.sc.ProjectID))
}
