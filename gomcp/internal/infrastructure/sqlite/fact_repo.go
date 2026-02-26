package sqlite

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
)

const timeFormat = time.RFC3339Nano

// FactRepo implements memory.FactStore using SQLite.
// Compatible with memory_bridge_v2.db schema v2.0.0.
type FactRepo struct {
	db *DB
}

// NewFactRepo creates a FactRepo and ensures the schema exists.
func NewFactRepo(db *DB) (*FactRepo, error) {
	repo := &FactRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("fact repo migrate: %w", err)
	}
	return repo, nil
}

func (r *FactRepo) migrate() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS hierarchical_facts (
			id TEXT PRIMARY KEY,
			content TEXT NOT NULL,
			level INTEGER NOT NULL DEFAULT 0,
			domain TEXT,
			module TEXT,
			code_ref TEXT,
			parent_id TEXT,
			embedding BLOB,
			ttl_config TEXT,
			created_at TEXT NOT NULL,
			valid_from TEXT NOT NULL,
			valid_until TEXT,
			is_stale INTEGER DEFAULT 0,
			is_archived INTEGER DEFAULT 0,
			confidence REAL DEFAULT 1.0,
			source TEXT DEFAULT 'manual',
			session_id TEXT,
			FOREIGN KEY (parent_id) REFERENCES hierarchical_facts(id)
		)`,
		`CREATE TABLE IF NOT EXISTS fact_hierarchy (
			parent_id TEXT NOT NULL,
			child_id TEXT NOT NULL,
			relationship TEXT DEFAULT 'contains',
			PRIMARY KEY (parent_id, child_id),
			FOREIGN KEY (parent_id) REFERENCES hierarchical_facts(id),
			FOREIGN KEY (child_id) REFERENCES hierarchical_facts(id)
		)`,
		`CREATE TABLE IF NOT EXISTS embeddings_index (
			fact_id TEXT PRIMARY KEY,
			embedding BLOB NOT NULL,
			model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
			updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (fact_id) REFERENCES hierarchical_facts(id)
		)`,
		`CREATE TABLE IF NOT EXISTS domain_centroids (
			domain TEXT PRIMARY KEY,
			centroid BLOB NOT NULL,
			fact_count INTEGER DEFAULT 0,
			updated_at TEXT DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS schema_info (
			key TEXT PRIMARY KEY,
			value TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_level ON hierarchical_facts(level)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_domain ON hierarchical_facts(domain)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_module ON hierarchical_facts(module)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_stale ON hierarchical_facts(is_stale)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_session ON hierarchical_facts(session_id)`,
		`INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', '2.0.0')`,
	}
	for _, s := range stmts {
		if _, err := r.db.Exec(s); err != nil {
			return fmt.Errorf("exec %q: %w", s[:40], err)
		}
	}
	return nil
}

// Add inserts a new fact.
func (r *FactRepo) Add(ctx context.Context, fact *memory.Fact) error {
	embeddingBlob, err := encodeEmbedding(fact.Embedding)
	if err != nil {
		return err
	}
	ttlJSON, err := encodeTTL(fact.TTL)
	if err != nil {
		return err
	}
	var validUntil *string
	if fact.ValidUntil != nil {
		s := fact.ValidUntil.Format(timeFormat)
		validUntil = &s
	}

	_, err = r.db.Exec(`INSERT INTO hierarchical_facts
		(id, content, level, domain, module, code_ref, parent_id,
		 embedding, ttl_config, created_at, valid_from, valid_until,
		 is_stale, is_archived, confidence, source, session_id)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		fact.ID, fact.Content, int(fact.Level),
		nullStr(fact.Domain), nullStr(fact.Module), nullStr(fact.CodeRef),
		nullStr(fact.ParentID),
		embeddingBlob, ttlJSON,
		fact.CreatedAt.Format(timeFormat), fact.ValidFrom.Format(timeFormat), validUntil,
		boolToInt(fact.IsStale), boolToInt(fact.IsArchived),
		fact.Confidence, fact.Source, nullStr(fact.SessionID),
	)
	if err != nil {
		return fmt.Errorf("insert fact: %w", err)
	}

	// Also insert into embeddings_index if embedding exists.
	if len(fact.Embedding) > 0 {
		_, err = r.db.Exec(`INSERT OR REPLACE INTO embeddings_index (fact_id, embedding) VALUES (?, ?)`,
			fact.ID, embeddingBlob)
		if err != nil {
			return fmt.Errorf("insert embedding index: %w", err)
		}
	}

	return nil
}

// Get retrieves a fact by ID.
func (r *FactRepo) Get(ctx context.Context, id string) (*memory.Fact, error) {
	row := r.db.QueryRow(`SELECT id, content, level, domain, module, code_ref, parent_id,
		embedding, ttl_config, created_at, valid_from, valid_until,
		is_stale, is_archived, confidence, source, session_id
		FROM hierarchical_facts WHERE id = ?`, id)
	return scanFact(row)
}

// Update updates an existing fact.
func (r *FactRepo) Update(ctx context.Context, fact *memory.Fact) error {
	embeddingBlob, err := encodeEmbedding(fact.Embedding)
	if err != nil {
		return err
	}
	ttlJSON, err := encodeTTL(fact.TTL)
	if err != nil {
		return err
	}
	var validUntil *string
	if fact.ValidUntil != nil {
		s := fact.ValidUntil.Format(timeFormat)
		validUntil = &s
	}

	result, err := r.db.Exec(`UPDATE hierarchical_facts SET
		content=?, level=?, domain=?, module=?, code_ref=?, parent_id=?,
		embedding=?, ttl_config=?, created_at=?, valid_from=?, valid_until=?,
		is_stale=?, is_archived=?, confidence=?, source=?, session_id=?
		WHERE id=?`,
		fact.Content, int(fact.Level),
		nullStr(fact.Domain), nullStr(fact.Module), nullStr(fact.CodeRef),
		nullStr(fact.ParentID),
		embeddingBlob, ttlJSON,
		fact.CreatedAt.Format(timeFormat), fact.ValidFrom.Format(timeFormat), validUntil,
		boolToInt(fact.IsStale), boolToInt(fact.IsArchived),
		fact.Confidence, fact.Source, nullStr(fact.SessionID),
		fact.ID,
	)
	if err != nil {
		return fmt.Errorf("update fact: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("fact %s not found", fact.ID)
	}
	return nil
}

// Delete removes a fact by ID.
func (r *FactRepo) Delete(ctx context.Context, id string) error {
	// Remove from embeddings_index first (FK).
	_, _ = r.db.Exec(`DELETE FROM embeddings_index WHERE fact_id = ?`, id)
	// Remove from fact_hierarchy.
	_, _ = r.db.Exec(`DELETE FROM fact_hierarchy WHERE parent_id = ? OR child_id = ?`, id, id)
	// Remove the fact.
	result, err := r.db.Exec(`DELETE FROM hierarchical_facts WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete fact: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("fact %s not found", id)
	}
	return nil
}

// ListByDomain returns facts in a domain, optionally including stale ones.
func (r *FactRepo) ListByDomain(ctx context.Context, domain string, includeStale bool) ([]*memory.Fact, error) {
	var query string
	if includeStale {
		query = `SELECT id, content, level, domain, module, code_ref, parent_id,
			embedding, ttl_config, created_at, valid_from, valid_until,
			is_stale, is_archived, confidence, source, session_id
			FROM hierarchical_facts WHERE domain = ?`
	} else {
		query = `SELECT id, content, level, domain, module, code_ref, parent_id,
			embedding, ttl_config, created_at, valid_from, valid_until,
			is_stale, is_archived, confidence, source, session_id
			FROM hierarchical_facts WHERE domain = ? AND is_stale = 0`
	}
	rows, err := r.db.Query(query, domain)
	if err != nil {
		return nil, fmt.Errorf("list by domain: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// ListByLevel returns all facts at a given hierarchy level.
func (r *FactRepo) ListByLevel(ctx context.Context, level memory.HierLevel) ([]*memory.Fact, error) {
	rows, err := r.db.Query(`SELECT id, content, level, domain, module, code_ref, parent_id,
		embedding, ttl_config, created_at, valid_from, valid_until,
		is_stale, is_archived, confidence, source, session_id
		FROM hierarchical_facts WHERE level = ?`, int(level))
	if err != nil {
		return nil, fmt.Errorf("list by level: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// ListDomains returns distinct domain names.
func (r *FactRepo) ListDomains(ctx context.Context) ([]string, error) {
	rows, err := r.db.Query(`SELECT DISTINCT domain FROM hierarchical_facts WHERE domain IS NOT NULL AND domain != ''`)
	if err != nil {
		return nil, fmt.Errorf("list domains: %w", err)
	}
	defer rows.Close()

	var domains []string
	for rows.Next() {
		var d string
		if err := rows.Scan(&d); err != nil {
			return nil, err
		}
		domains = append(domains, d)
	}
	return domains, rows.Err()
}

// GetStale returns stale facts, optionally including archived ones.
func (r *FactRepo) GetStale(ctx context.Context, includeArchived bool) ([]*memory.Fact, error) {
	var query string
	if includeArchived {
		query = `SELECT id, content, level, domain, module, code_ref, parent_id,
			embedding, ttl_config, created_at, valid_from, valid_until,
			is_stale, is_archived, confidence, source, session_id
			FROM hierarchical_facts WHERE is_stale = 1`
	} else {
		query = `SELECT id, content, level, domain, module, code_ref, parent_id,
			embedding, ttl_config, created_at, valid_from, valid_until,
			is_stale, is_archived, confidence, source, session_id
			FROM hierarchical_facts WHERE is_stale = 1 AND is_archived = 0`
	}
	rows, err := r.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("get stale: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// Search performs a LIKE-based text search on fact content.
func (r *FactRepo) Search(ctx context.Context, query string, limit int) ([]*memory.Fact, error) {
	if limit <= 0 {
		limit = 50
	}
	rows, err := r.db.Query(`SELECT id, content, level, domain, module, code_ref, parent_id,
		embedding, ttl_config, created_at, valid_from, valid_until,
		is_stale, is_archived, confidence, source, session_id
		FROM hierarchical_facts WHERE content LIKE ? LIMIT ?`,
		"%"+query+"%", limit)
	if err != nil {
		return nil, fmt.Errorf("search: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// GetExpired returns facts whose TTL has expired.
func (r *FactRepo) GetExpired(ctx context.Context) ([]*memory.Fact, error) {
	// Get all facts with TTL config, check expiry in Go.
	rows, err := r.db.Query(`SELECT id, content, level, domain, module, code_ref, parent_id,
		embedding, ttl_config, created_at, valid_from, valid_until,
		is_stale, is_archived, confidence, source, session_id
		FROM hierarchical_facts WHERE ttl_config IS NOT NULL AND ttl_config != ''`)
	if err != nil {
		return nil, fmt.Errorf("get expired: %w", err)
	}
	defer rows.Close()

	all, err := scanFacts(rows)
	if err != nil {
		return nil, err
	}

	var expired []*memory.Fact
	for _, f := range all {
		if f.TTL != nil && f.TTL.IsExpired(f.CreatedAt) {
			expired = append(expired, f)
		}
	}
	return expired, nil
}

// RefreshTTL resets the created_at timestamp for a fact (effectively refreshing its TTL).
func (r *FactRepo) RefreshTTL(ctx context.Context, id string) error {
	now := time.Now().Format(timeFormat)
	result, err := r.db.Exec(`UPDATE hierarchical_facts SET created_at = ? WHERE id = ?`, now, id)
	if err != nil {
		return fmt.Errorf("refresh ttl: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("fact %s not found", id)
	}
	return nil
}

// Stats returns aggregate statistics about the fact store.
func (r *FactRepo) Stats(ctx context.Context) (*memory.FactStoreStats, error) {
	stats := &memory.FactStoreStats{
		ByLevel:  make(map[memory.HierLevel]int),
		ByDomain: make(map[string]int),
	}

	// Total facts.
	row := r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts`)
	if err := row.Scan(&stats.TotalFacts); err != nil {
		return nil, err
	}

	// Stale count.
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts WHERE is_stale = 1`)
	if err := row.Scan(&stats.StaleCount); err != nil {
		return nil, err
	}

	// With embeddings.
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts WHERE embedding IS NOT NULL`)
	if err := row.Scan(&stats.WithEmbeddings); err != nil {
		return nil, err
	}

	// By level.
	rows, err := r.db.Query(`SELECT level, COUNT(*) FROM hierarchical_facts GROUP BY level`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var level, count int
		if err := rows.Scan(&level, &count); err != nil {
			return nil, err
		}
		stats.ByLevel[memory.HierLevel(level)] = count
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	// By domain.
	rows2, err := r.db.Query(`SELECT domain, COUNT(*) FROM hierarchical_facts WHERE domain IS NOT NULL AND domain != '' GROUP BY domain`)
	if err != nil {
		return nil, err
	}
	defer rows2.Close()
	for rows2.Next() {
		var domain string
		var count int
		if err := rows2.Scan(&domain, &count); err != nil {
			return nil, err
		}
		stats.ByDomain[domain] = count
	}
	return stats, rows2.Err()
}

// --- helpers ---

func scanFact(row *sql.Row) (*memory.Fact, error) {
	var f memory.Fact
	var levelInt int
	var domain, module, codeRef, parentID, sessionID sql.NullString
	var embeddingBlob []byte
	var ttlJSON sql.NullString
	var createdAt, validFrom string
	var validUntil sql.NullString
	var isStale, isArchived int

	err := row.Scan(&f.ID, &f.Content, &levelInt,
		&domain, &module, &codeRef, &parentID,
		&embeddingBlob, &ttlJSON,
		&createdAt, &validFrom, &validUntil,
		&isStale, &isArchived, &f.Confidence, &f.Source, &sessionID,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("fact not found")
		}
		return nil, fmt.Errorf("scan fact: %w", err)
	}

	f.Level = memory.HierLevel(levelInt)
	f.Domain = domain.String
	f.Module = module.String
	f.CodeRef = codeRef.String
	f.ParentID = parentID.String
	f.SessionID = sessionID.String
	f.IsStale = isStale != 0
	f.IsArchived = isArchived != 0

	f.CreatedAt, _ = time.Parse(timeFormat, createdAt)
	f.ValidFrom, _ = time.Parse(timeFormat, validFrom)
	f.UpdatedAt = f.CreatedAt // We don't have a separate updated_at column in the DB schema.

	if validUntil.Valid {
		t, _ := time.Parse(timeFormat, validUntil.String)
		f.ValidUntil = &t
	}

	if len(embeddingBlob) > 0 {
		if err := json.Unmarshal(embeddingBlob, &f.Embedding); err != nil {
			return nil, fmt.Errorf("decode embedding: %w", err)
		}
	}

	if ttlJSON.Valid && ttlJSON.String != "" {
		f.TTL = &memory.TTLConfig{}
		if err := json.Unmarshal([]byte(ttlJSON.String), f.TTL); err != nil {
			return nil, fmt.Errorf("decode ttl_config: %w", err)
		}
	}

	return &f, nil
}

func scanFacts(rows *sql.Rows) ([]*memory.Fact, error) {
	var facts []*memory.Fact
	for rows.Next() {
		var f memory.Fact
		var levelInt int
		var domain, module, codeRef, parentID, sessionID sql.NullString
		var embeddingBlob []byte
		var ttlJSON sql.NullString
		var createdAt, validFrom string
		var validUntil sql.NullString
		var isStale, isArchived int

		err := rows.Scan(&f.ID, &f.Content, &levelInt,
			&domain, &module, &codeRef, &parentID,
			&embeddingBlob, &ttlJSON,
			&createdAt, &validFrom, &validUntil,
			&isStale, &isArchived, &f.Confidence, &f.Source, &sessionID,
		)
		if err != nil {
			return nil, fmt.Errorf("scan fact row: %w", err)
		}

		f.Level = memory.HierLevel(levelInt)
		f.Domain = domain.String
		f.Module = module.String
		f.CodeRef = codeRef.String
		f.ParentID = parentID.String
		f.SessionID = sessionID.String
		f.IsStale = isStale != 0
		f.IsArchived = isArchived != 0
		f.CreatedAt, _ = time.Parse(timeFormat, createdAt)
		f.ValidFrom, _ = time.Parse(timeFormat, validFrom)
		f.UpdatedAt = f.CreatedAt

		if validUntil.Valid {
			t, _ := time.Parse(timeFormat, validUntil.String)
			f.ValidUntil = &t
		}

		if len(embeddingBlob) > 0 {
			if err := json.Unmarshal(embeddingBlob, &f.Embedding); err != nil {
				return nil, fmt.Errorf("decode embedding: %w", err)
			}
		}

		if ttlJSON.Valid && ttlJSON.String != "" {
			f.TTL = &memory.TTLConfig{}
			if err := json.Unmarshal([]byte(ttlJSON.String), f.TTL); err != nil {
				return nil, fmt.Errorf("decode ttl_config: %w", err)
			}
		}

		facts = append(facts, &f)
	}
	return facts, rows.Err()
}

func encodeEmbedding(embedding []float64) ([]byte, error) {
	if len(embedding) == 0 {
		return nil, nil
	}
	data, err := json.Marshal(embedding)
	if err != nil {
		return nil, fmt.Errorf("encode embedding: %w", err)
	}
	return data, nil
}

func encodeTTL(ttl *memory.TTLConfig) (*string, error) {
	if ttl == nil {
		return nil, nil
	}
	data, err := json.Marshal(ttl)
	if err != nil {
		return nil, fmt.Errorf("encode ttl: %w", err)
	}
	s := string(data)
	return &s, nil
}

func nullStr(s string) sql.NullString {
	if s == "" {
		return sql.NullString{}
	}
	return sql.NullString{String: s, Valid: true}
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

// Ensure FactRepo implements memory.FactStore.
var _ memory.FactStore = (*FactRepo)(nil)
