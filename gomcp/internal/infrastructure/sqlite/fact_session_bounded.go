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

type boundedSessionSearchSnapshot struct {
	tx            *sql.Tx
	sc            rlmscope.Scope
	sessionID     string
	frozenFactIDs map[string]struct{}
}

// WithBoundedSessionSearchSnapshot measures the exact eligible session scope
// using SQLite record metadata before any factColumns value can be selected.
// The preflight and all callback reads share one read transaction.
func (r *FactRepo) WithBoundedSessionSearchSnapshot(
	ctx context.Context,
	sessionID string,
	factIDs []string,
	run func(memory.BoundedSearchSnapshot) ([]*memory.Fact, error),
) ([]*memory.Fact, *memory.BoundedSearchStoredOversize, error) {
	if run == nil {
		return nil, nil, fmt.Errorf("bounded session search callback is required")
	}
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return nil, nil, err
	}
	whereSQL, args, err := boundedSessionSearchSelection(sc, sessionID, factIDs)
	if err != nil {
		return nil, nil, err
	}
	tx, err := r.db.SqlDB().BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return nil, nil, fmt.Errorf("begin bounded session search snapshot: %w", err)
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
		return nil, nil, fmt.Errorf("preflight bounded session search snapshot: %w", err)
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
		return nil, nil, fmt.Errorf("bounded session search snapshot row count exceeds hard limit")
	}

	var frozenFactIDs map[string]struct{}
	if factIDs != nil {
		frozenFactIDs = make(map[string]struct{}, len(factIDs))
		for _, id := range factIDs {
			frozenFactIDs[id] = struct{}{}
		}
	}
	facts, err := run(&boundedSessionSearchSnapshot{
		tx: tx, sc: sc, sessionID: sessionID, frozenFactIDs: frozenFactIDs,
	})
	if err != nil {
		return nil, nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, nil, fmt.Errorf("commit bounded session search snapshot: %w", err)
	}
	return facts, nil, nil
}

func boundedSessionSearchSelection(
	sc rlmscope.Scope,
	sessionID string,
	factIDs []string,
) (string, []any, error) {
	whereSQL := `tenant_id COLLATE BINARY = ?
		AND project_id COLLATE BINARY = ?
		AND session_id COLLATE BINARY = ?
		AND is_archived = 0
		AND is_stale = 0`
	args := []any{sc.TenantID, sc.ProjectID, sessionID}
	if factIDs == nil {
		return whereSQL, args, nil
	}
	if len(factIDs) == 0 || len(factIDs) > 100 {
		return "", nil, fmt.Errorf("frozen bounded session search IDs must contain 1 through 100 values")
	}
	seen := make(map[string]struct{}, len(factIDs))
	placeholders := make([]string, len(factIDs))
	for index, id := range factIDs {
		if id == "" || len(id) > boundedSearchStoredFactIDHardMaxBytes {
			return "", nil, fmt.Errorf("invalid frozen bounded session search fact ID")
		}
		if _, duplicate := seen[id]; duplicate {
			return "", nil, fmt.Errorf("duplicate frozen bounded session search fact ID")
		}
		seen[id] = struct{}{}
		placeholders[index] = "?"
		args = append(args, id)
	}
	whereSQL += ` AND id COLLATE BINARY IN (` + strings.Join(placeholders, ",") + `)`
	return whereSQL, args, nil
}

func (s *boundedSessionSearchSnapshot) Search(
	ctx context.Context,
	query string,
	limit int,
) ([]*memory.Fact, error) {
	if s.frozenFactIDs != nil {
		return nil, fmt.Errorf("ranked search is unavailable in a frozen session continuation snapshot")
	}
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
		  AND session_id COLLATE BINARY = ?
		  AND is_archived = 0
		  AND is_stale = 0`,
		s.sc.TenantID, s.sc.ProjectID, s.sessionID)
	if err != nil {
		return nil, fmt.Errorf("bounded session keyword search: %w", err)
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
		if !ranked[i].fact.CreatedAt.Equal(ranked[j].fact.CreatedAt) {
			return ranked[i].fact.CreatedAt.After(ranked[j].fact.CreatedAt)
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

func (s *boundedSessionSearchSnapshot) SearchByVector(
	ctx context.Context,
	queryVec []float64,
	limit int,
) ([]*memory.Fact, error) {
	if s.frozenFactIDs != nil {
		return nil, fmt.Errorf("vector search is unavailable in a frozen session continuation snapshot")
	}
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
		  AND session_id COLLATE BINARY = ?
		  AND embedding IS NOT NULL
		  AND is_archived = 0
		  AND is_stale = 0`,
		s.sc.TenantID, s.sc.ProjectID, s.sessionID)
	if err != nil {
		return nil, fmt.Errorf("bounded session vector search: %w", err)
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
	sort.Slice(ranked, func(i, j int) bool {
		if ranked[i].similarity != ranked[j].similarity {
			return ranked[i].similarity > ranked[j].similarity
		}
		if !ranked[i].fact.CreatedAt.Equal(ranked[j].fact.CreatedAt) {
			return ranked[i].fact.CreatedAt.After(ranked[j].fact.CreatedAt)
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

func (s *boundedSessionSearchSnapshot) Get(ctx context.Context, id string) (*memory.Fact, error) {
	if s.frozenFactIDs != nil {
		if _, allowed := s.frozenFactIDs[id]; !allowed {
			return nil, fmt.Errorf("fact is outside the frozen session continuation allowlist")
		}
	}
	return scanFact(s.tx.QueryRowContext(ctx, `SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE id COLLATE BINARY = ?
		  AND tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND session_id COLLATE BINARY = ?
		  AND is_archived = 0
		  AND is_stale = 0`,
		id, s.sc.TenantID, s.sc.ProjectID, s.sessionID))
}

// GetForSession performs an exact point lookup for bounded continuation
// revalidation. Unlike FactRepo.Get it requires a non-empty session predicate.
func (r *FactRepo) GetForSession(
	ctx context.Context,
	sessionID, factID string,
) (*memory.Fact, error) {
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if factID == "" {
		return nil, fmt.Errorf("fact id is required")
	}
	row := r.db.QueryRowContext(ctx, `SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		factID, sc.TenantID, sc.ProjectID, sessionID)
	return scanFact(row)
}
