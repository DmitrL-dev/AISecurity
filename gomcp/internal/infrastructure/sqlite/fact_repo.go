package sqlite

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"sort"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

const timeFormat = time.RFC3339Nano

const (
	sessionTurnPayloadVersion    = 2
	sessionTurnRequestRefPrefix  = "session-turn-request-v1:sha256:"
	sha256HexLength              = 64
	sessionTurnFactUpdateTrigger = "session_turn_receipt_fact_immutable_update"
	sessionTurnFactDeleteTrigger = "session_turn_receipt_fact_immutable_delete"
)

// normaliseOrigin maps a stored origin to the closed enum.
//
// A NULL, an empty string, or a value written by an older or foreign writer becomes
// OriginUnspecified rather than being passed through. That is the fail-safe direction: an
// unrecognised origin must never be mistaken for OriginUser, because OriginUser is the only
// value permitted to carry a standing instruction.
func normaliseOrigin(stored sql.NullString) memory.Origin {
	if !stored.Valid {
		return memory.OriginUnspecified
	}
	candidate := memory.Origin(stored.String)
	if !candidate.IsValid() {
		return memory.OriginUnspecified
	}
	return candidate
}

const factColumns = `id, tenant_id, project_id, content, level, domain, module, code_ref,
	CASE
		WHEN parent_id IS NULL OR parent_id = '' THEN parent_id
		WHEN EXISTS (
			SELECT 1 FROM hierarchical_facts AS exact_parent
			WHERE exact_parent.id = hierarchical_facts.parent_id
			  AND exact_parent.tenant_id = hierarchical_facts.tenant_id
			  AND exact_parent.project_id = hierarchical_facts.project_id
			  AND IFNULL(exact_parent.session_id, '') = IFNULL(hierarchical_facts.session_id, '')
		) THEN parent_id
		ELSE NULL
	END AS parent_id,
	embedding, ttl_config, created_at, valid_from, valid_until,
	is_stale, is_archived, confidence, source, session_id, origin,
	COALESCE(hit_count, 0)`

// FactRepo implements memory.FactStore using SQLite.
// Compatible with memory_bridge_v2.db schema v2.0.0.
type FactRepo struct {
	db        *DB
	factPages factPageSnapshotCache
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
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
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
			-- 'unspecified', not 'manual'. The old default asserted that a human hand-wrote the
			-- content of every row that omitted the column, including rows written by the STIX
			-- feed reader and by the add_fact tool an AGENT calls.
			source TEXT DEFAULT 'unspecified',
			session_id TEXT,
			-- Where the CONTENT came from, on the trust axis: unspecified | user | derived |
			-- external. See memory.Origin. Separate from the source column, which names
			-- the subsystem that wrote the row.
			origin TEXT NOT NULL DEFAULT 'unspecified',
			FOREIGN KEY (parent_id) REFERENCES hierarchical_facts(id)
		)`,
		// Paging cannot use hierarchical_facts.rowid as a snapshot: SQLite may
		// reuse a deleted maximum rowid. This side table owns a never-reused
		// AUTOINCREMENT generation for each currently live fact identity. Delete
		// removes the mapping; reinserting the same id receives a strictly newer
		// sequence and therefore cannot enter an older snapshot.
		`CREATE TABLE IF NOT EXISTS fact_export_sequence (
			seq INTEGER PRIMARY KEY AUTOINCREMENT,
			fact_id TEXT NOT NULL UNIQUE
		)`,
		`CREATE TABLE IF NOT EXISTS fact_stats_page_snapshots (
			snapshot_id TEXT COLLATE BINARY PRIMARY KEY CHECK (
				length(snapshot_id) = 64
				AND snapshot_id NOT GLOB '*[^0-9a-f]*'
			),
			tenant_id TEXT COLLATE BINARY NOT NULL,
			project_id TEXT COLLATE BINARY NOT NULL,
			expected_rows INTEGER NOT NULL CHECK (expected_rows > 0),
			expected_domains INTEGER NOT NULL CHECK (
				expected_domains > 0 AND expected_domains <= 10000
			),
			expected_segments INTEGER NOT NULL CHECK (
				expected_segments > 0 AND expected_segments <= 10064
			),
			serialized_bytes INTEGER NOT NULL CHECK (
				serialized_bytes > 0 AND serialized_bytes <= 33554432
			),
			expires_at_unix INTEGER NOT NULL,
			UNIQUE (tenant_id, project_id)
		)`,
		`CREATE TABLE IF NOT EXISTS fact_stats_page_snapshot_segments (
			snapshot_id TEXT COLLATE BINARY NOT NULL,
			segment_index INTEGER NOT NULL CHECK (segment_index >= 0),
			ordinal INTEGER NOT NULL CHECK (ordinal >= 0 AND ordinal < 10000),
			sha256 TEXT COLLATE BINARY NOT NULL CHECK (
				length(sha256) = 64
				AND sha256 NOT GLOB '*[^0-9a-f]*'
			),
			total_bytes INTEGER NOT NULL CHECK (
				total_bytes > 0 AND total_bytes <= 16777216
			),
			offset_bytes INTEGER NOT NULL CHECK (offset_bytes >= 0),
			data BLOB NOT NULL CHECK (
				typeof(data) = 'blob'
				AND octet_length(data) > 0
				AND octet_length(data) <= 524288
			),
			is_final INTEGER NOT NULL CHECK (is_final IN (0, 1)),
			PRIMARY KEY (snapshot_id, segment_index),
			FOREIGN KEY (snapshot_id) REFERENCES fact_stats_page_snapshots(snapshot_id)
				ON DELETE CASCADE,
			CHECK (offset_bytes + octet_length(data) <= total_bytes),
			CHECK (is_final = (offset_bytes + octet_length(data) = total_bytes))
		)`,
		// Stats snapshots are ephemeral wire state. Startup invalidates every
		// cursor and clears legacy/corrupt rows before any value can be read.
		`DELETE FROM fact_stats_page_snapshots`,
		`CREATE TRIGGER IF NOT EXISTS fact_export_sequence_insert_v1
			AFTER INSERT ON hierarchical_facts
			BEGIN
				INSERT INTO fact_export_sequence(fact_id) VALUES (NEW.id);
				DELETE FROM fact_export_sequence
					WHERE fact_id IN (
						SELECT id FROM hierarchical_facts
						WHERE parent_id = NEW.id AND id <> NEW.id
					);
				INSERT INTO fact_export_sequence(fact_id)
					SELECT id FROM hierarchical_facts
					WHERE parent_id = NEW.id AND id <> NEW.id;
			END`,
		`CREATE TRIGGER IF NOT EXISTS fact_export_sequence_delete_v1
			AFTER DELETE ON hierarchical_facts
			BEGIN
				DELETE FROM fact_export_sequence WHERE fact_id = OLD.id;
				DELETE FROM fact_export_sequence
					WHERE fact_id IN (
						SELECT id FROM hierarchical_facts
						WHERE parent_id = OLD.id AND id <> OLD.id
					);
				INSERT INTO fact_export_sequence(fact_id)
					SELECT id FROM hierarchical_facts
					WHERE parent_id = OLD.id AND id <> OLD.id;
			END`,
		// This feature is additive and unreleased, so the complete trigger gets a
		// stable versioned name from its first migration. Never DROP the current
		// trigger during startup: DDL is otherwise externally visible between the
		// autocommit DROP and CREATE, allowing a concurrent writer to mutate a fact
		// without renewing its export sequence.
		`CREATE TRIGGER IF NOT EXISTS fact_export_sequence_update_payload_v1
			AFTER UPDATE OF id, tenant_id, project_id, content, level, domain,
				module, code_ref, parent_id, embedding, ttl_config, created_at,
				valid_from, valid_until, is_stale, is_archived, confidence,
				source, session_id, origin, hit_count
			ON hierarchical_facts
			BEGIN
				DELETE FROM fact_export_sequence WHERE fact_id = OLD.id;
				INSERT INTO fact_export_sequence(fact_id) VALUES (NEW.id);
			END`,
		// factColumns masks a parent_id when its parent moves outside the child's
		// exact tenant/project/session boundary. That changes the child's exported
		// bytes even though the child row itself was not UPDATEd, so renew every
		// affected child's sequence as part of the parent boundary mutation.
		`CREATE TRIGGER IF NOT EXISTS fact_export_sequence_parent_boundary_update_v1
			AFTER UPDATE OF id, tenant_id, project_id, session_id ON hierarchical_facts
			BEGIN
				DELETE FROM fact_export_sequence
					WHERE fact_id IN (
						SELECT id FROM hierarchical_facts
						WHERE parent_id = OLD.id AND id <> OLD.id AND id <> NEW.id
					);
				INSERT INTO fact_export_sequence(fact_id)
					SELECT id FROM hierarchical_facts
					WHERE parent_id = OLD.id AND id <> OLD.id AND id <> NEW.id;
			END`,
		`DELETE FROM fact_export_sequence
			WHERE NOT EXISTS (
				SELECT 1 FROM hierarchical_facts WHERE id = fact_export_sequence.fact_id
			)`,
		`INSERT OR IGNORE INTO fact_export_sequence(fact_id)
			SELECT id FROM hierarchical_facts ORDER BY rowid ASC`,
		`CREATE TABLE IF NOT EXISTS fact_hierarchy (
			parent_id TEXT NOT NULL,
			child_id TEXT NOT NULL,
			relationship TEXT DEFAULT 'contains',
			PRIMARY KEY (parent_id, child_id),
			FOREIGN KEY (parent_id) REFERENCES hierarchical_facts(id),
			FOREIGN KEY (child_id) REFERENCES hierarchical_facts(id)
		)`,
		`CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_exact_identity
			ON hierarchical_facts(tenant_id, project_id, session_id, id)`,
		`CREATE TABLE IF NOT EXISTS session_turn_receipts (
			tenant_id TEXT NOT NULL,
			project_id TEXT NOT NULL,
			session_id TEXT NOT NULL CHECK (session_id <> ''),
			turn_id TEXT NOT NULL CHECK (
				length(turn_id) = 69 AND substr(turn_id, 1, 5) = 'turn_'
				AND substr(turn_id, 6) NOT GLOB '*[^0-9a-f]*'
			),
			fact_id TEXT NOT NULL,
			payload_version INTEGER NOT NULL CHECK (payload_version = 2),
			payload_sha256 TEXT NOT NULL CHECK (
				length(payload_sha256) = 64
				AND payload_sha256 NOT GLOB '*[^0-9a-f]*'
			),
			created_at TEXT NOT NULL,
			PRIMARY KEY (tenant_id, project_id, session_id, turn_id),
			UNIQUE (fact_id),
			FOREIGN KEY (tenant_id, project_id, session_id, fact_id)
				REFERENCES hierarchical_facts(tenant_id, project_id, session_id, id)
		)`,
		`CREATE TRIGGER IF NOT EXISTS ` + sessionTurnFactUpdateTrigger + `
			BEFORE UPDATE ON hierarchical_facts
			WHEN EXISTS (
				SELECT 1 FROM session_turn_receipts AS receipt
				WHERE receipt.tenant_id = OLD.tenant_id
				  AND receipt.project_id = OLD.project_id
				  AND receipt.session_id = OLD.session_id
				  AND receipt.fact_id = OLD.id
			)
			BEGIN
				SELECT RAISE(ABORT, 'receipt-backed session fact is immutable: update denied');
			END`,
		`CREATE TRIGGER IF NOT EXISTS ` + sessionTurnFactDeleteTrigger + `
			BEFORE DELETE ON hierarchical_facts
			WHEN EXISTS (
				SELECT 1 FROM session_turn_receipts AS receipt
				WHERE receipt.tenant_id = OLD.tenant_id
				  AND receipt.project_id = OLD.project_id
				  AND receipt.session_id = OLD.session_id
				  AND receipt.fact_id = OLD.id
			)
			BEGIN
				SELECT RAISE(ABORT, 'receipt-backed session fact is immutable: delete denied');
			END`,
		`CREATE TABLE IF NOT EXISTS embeddings_index (
			fact_id TEXT PRIMARY KEY,
			embedding BLOB NOT NULL,
			model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
			updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (fact_id) REFERENCES hierarchical_facts(id)
		)`,
		`CREATE TABLE IF NOT EXISTS domain_centroids (
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			domain TEXT NOT NULL,
			centroid BLOB NOT NULL,
			fact_count INTEGER DEFAULT 0,
			updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (tenant_id, project_id, domain)
		)`,
		`CREATE TABLE IF NOT EXISTS rlm_projects (
			tenant_id TEXT NOT NULL,
			project_id TEXT NOT NULL,
			name TEXT NOT NULL DEFAULT '',
			status TEXT NOT NULL DEFAULT 'active',
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			archived_at TEXT,
			last_accessed_at TEXT,
			PRIMARY KEY (tenant_id, project_id)
		)`,
		`CREATE TABLE IF NOT EXISTS schema_info (
			key TEXT PRIMARY KEY,
			value TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_scope ON hierarchical_facts(tenant_id, project_id)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_scope_level ON hierarchical_facts(tenant_id, project_id, level)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_scope_level_page
			ON hierarchical_facts(tenant_id, project_id, level, created_at, id)
			WHERE session_id IS NULL OR session_id = ''`,
		`CREATE INDEX IF NOT EXISTS idx_facts_scope_domain ON hierarchical_facts(tenant_id, project_id, domain)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_scope_session ON hierarchical_facts(tenant_id, project_id, session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_session_dedup ON hierarchical_facts(tenant_id, project_id, session_id, level, content)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_level ON hierarchical_facts(level)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_domain ON hierarchical_facts(domain)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_module ON hierarchical_facts(module)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_stale ON hierarchical_facts(is_stale)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_session ON hierarchical_facts(session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_source ON hierarchical_facts(source)`,
		// Deduplication looks up (scope, level, content) on every single Add. Without content in an
		// index SQLite takes the (tenant, project, level) index and then compares content row by
		// row — for a tenant holding a few thousand facts at one level that is a few thousand row
		// reads per write, which would make the fix cost more than the duplicates did.
		// IF NOT EXISTS in this list rather than in the ALTER block: it has to reach existing
		// databases too, and re-running it is free.
		`CREATE INDEX IF NOT EXISTS idx_facts_dedup ON hierarchical_facts(tenant_id, project_id, level, content)`,
	}

	// v3.3 migration: add hit_count, last_accessed_at, synapses table.
	v33Stmts := []string{
		// Safe ALTER TABLE — ignore error if column already exists.
		`ALTER TABLE hierarchical_facts ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`,
		`ALTER TABLE hierarchical_facts ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`,
		`ALTER TABLE domain_centroids ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`,
		`ALTER TABLE domain_centroids ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`,
		`ALTER TABLE rlm_projects ADD COLUMN status TEXT NOT NULL DEFAULT 'active'`,
		`ALTER TABLE rlm_projects ADD COLUMN archived_at TEXT`,
		`ALTER TABLE rlm_projects ADD COLUMN last_accessed_at TEXT`,
		`ALTER TABLE hierarchical_facts ADD COLUMN hit_count INTEGER DEFAULT 0`,
		`ALTER TABLE hierarchical_facts ADD COLUMN last_accessed_at TEXT`,
		// Existing rows become 'unspecified', which is the truth: the origin of a fact written
		// before this column existed is genuinely unknown. Backfilling them as 'user' would
		// invent provenance for historical data — the same false claim the old `source
		// DEFAULT 'manual'` was making.
		`ALTER TABLE hierarchical_facts ADD COLUMN origin TEXT NOT NULL DEFAULT 'unspecified'`,
		`CREATE TABLE IF NOT EXISTS synapses (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			fact_id_a TEXT NOT NULL,
			fact_id_b TEXT NOT NULL,
			confidence REAL DEFAULT 0.0,
			status TEXT DEFAULT 'PENDING',
			created_at TEXT DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (fact_id_a) REFERENCES hierarchical_facts(id),
			FOREIGN KEY (fact_id_b) REFERENCES hierarchical_facts(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_facts_hit_count ON hierarchical_facts(hit_count)`,
		`CREATE INDEX IF NOT EXISTS idx_rlm_projects_tenant_status ON rlm_projects(tenant_id, status)`,
		`ALTER TABLE synapses ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`,
		`ALTER TABLE synapses ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`,
		`CREATE INDEX IF NOT EXISTS idx_synapses_status ON synapses(status)`,
		`CREATE INDEX IF NOT EXISTS idx_synapses_scope_status ON synapses(tenant_id, project_id, status)`,
		`CREATE INDEX IF NOT EXISTS idx_synapses_scope_pair ON synapses(tenant_id, project_id, fact_id_a, fact_id_b)`,
	}
	for _, s := range stmts {
		if _, err := r.db.Exec(s); err != nil {
			return fmt.Errorf("exec %q: %w", s[:40], err)
		}
	}
	// v3.3: ignore errors on ALTER TABLE (column may already exist).
	for _, s := range v33Stmts {
		_, _ = r.db.Exec(s)
	}
	// Receipt validation writes and rolls back representative parent rows. Run
	// it only after every parent-column prerequisite from v3.3 exists, otherwise
	// a valid pre-v3.3 store cannot upgrade to the exact receipt schema.
	if err := r.validateSessionTurnReceiptSchema(); err != nil {
		return err
	}
	if err := r.migrateSessionTurnClaims(); err != nil {
		return err
	}
	// Export paging depends on trigger behavior rather than only trigger names.
	// CREATE TRIGGER IF NOT EXISTS deliberately preserves a live trigger during
	// rolling startup, but that also means an incompatible same-name trigger must
	// fail closed. Run the probe after v3.3 adds hit_count and after the receipt
	// schema is known usable, so an unrelated receipt incompatibility keeps its
	// precise startup diagnostic.
	if err := r.validateFactExportSequenceBehavior(); err != nil {
		return err
	}
	if err := r.migrateDomainCentroidsScope(); err != nil {
		return err
	}
	if err := r.seedProjectsFromFacts(); err != nil {
		return err
	}
	// Rows written before deduplication existed. The count is recorded rather than logged: a log
	// line at startup is read once, by whoever happened to be watching, and a store that quietly
	// shed rows should be able to say how many afterwards.
	folded, err := r.FoldExistingDuplicates(context.Background())
	if err != nil {
		return fmt.Errorf("fold pre-existing duplicates: %w", err)
	}
	if folded > 0 {
		if _, err := r.db.Exec(`INSERT OR REPLACE INTO schema_info (key, value)
			VALUES ('duplicates_folded_total',
				CAST(COALESCE((SELECT CAST(value AS INTEGER) FROM schema_info
					WHERE key = 'duplicates_folded_total'), 0) + ? AS TEXT))`, folded); err != nil {
			return fmt.Errorf("record folded duplicates: %w", err)
		}
	}
	if _, err := r.db.Exec(`INSERT OR REPLACE INTO schema_info (key, value)
		VALUES ('version', '3.4.0')`); err != nil {
		return fmt.Errorf("record schema version: %w", err)
	}
	return nil
}

// validateFactExportSequenceBehavior proves the snapshot-generation invariants
// used by exact export paging. sqlite_master text is not sufficient here:
// CREATE TRIGGER IF NOT EXISTS accepts an inert same-name trigger, and SQLite
// accepts unknown names in an UPDATE OF list. The probe therefore exercises the
// post-migration schema, including hit_count, in a transaction that is always
// rolled back.
func (r *FactRepo) validateFactExportSequenceBehavior() error {
	ctx := context.Background()
	parent := memory.NewFact("export sequence parent probe", memory.LevelProject, "schema", "migration")
	child := memory.NewFact("export sequence child probe", memory.LevelDomain, "schema", "migration")
	parent.Origin = memory.OriginBuiltin
	child.Origin = memory.OriginBuiltin
	child.ParentID = parent.ID
	seedDigest := fmt.Sprintf("%x", sha256.Sum256([]byte(parent.ID+":"+child.ID)))
	tenantID := "ExportSequenceProbeTenant-" + seedDigest[:12]
	projectID := "ExportSequenceProbeProject-" + seedDigest[12:24]
	movedProjectID := "ExportSequenceProbeMovedProject-" + seedDigest[24:36]
	now := time.Now().UTC().Round(0).Format(timeFormat)

	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("validate fact export sequence behavior: begin probe: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	insertFact := func(fact *memory.Fact, candidateProjectID string) error {
		_, err := tx.ExecContext(ctx, `INSERT INTO hierarchical_facts
			(id, tenant_id, project_id, content, level, domain, module, parent_id,
			 created_at, valid_from, is_stale, is_archived, confidence, source,
			 session_id, origin, hit_count)
			VALUES (?, ?, ?, ?, ?, ?, ?, NULLIF(?, ''), ?, ?, 0, 0, 1.0,
			 'schema_migration', NULL, 'derived', 0)`,
			fact.ID, tenantID, candidateProjectID, fact.Content, int(fact.Level),
			fact.Domain, fact.Module, fact.ParentID, now, now)
		return err
	}
	sequenceFor := func(factID string) (int64, error) {
		var sequence int64
		err := tx.QueryRowContext(ctx,
			`SELECT seq FROM fact_export_sequence WHERE fact_id = ?`, factID,
		).Scan(&sequence)
		return sequence, err
	}

	if err := insertFact(parent, projectID); err != nil {
		return fmt.Errorf("incompatible fact export sequence: parent INSERT rejected: %w", err)
	}
	parentSequence, err := sequenceFor(parent.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: INSERT trigger did not create parent mapping: %w", err)
	}
	if parentSequence <= 0 {
		return fmt.Errorf("incompatible fact export sequence: INSERT trigger created invalid parent sequence %d", parentSequence)
	}
	if err := insertFact(child, projectID); err != nil {
		return fmt.Errorf("incompatible fact export sequence: child INSERT rejected: %w", err)
	}
	childSequence, err := sequenceFor(child.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: INSERT trigger did not create a newer child mapping: %w", err)
	}
	if childSequence <= parentSequence {
		return fmt.Errorf("incompatible fact export sequence: INSERT trigger created child sequence %d after parent sequence %d", childSequence, parentSequence)
	}

	// UPDATE OF silently accepts unknown column names in SQLite. Exercise every
	// stored field that contributes to factColumns instead of trusting the DDL
	// text; this also rejects a partial same-name trigger left by an interrupted
	// or foreign migration. Setting a field to itself is intentional: UPDATE OF
	// is defined by the SET target, and every such write must invalidate a page.
	payloadColumns := []string{
		"id", "tenant_id", "project_id", "content", "level", "domain", "module",
		"code_ref", "parent_id", "embedding", "ttl_config", "created_at", "valid_from",
		"valid_until", "is_stale", "is_archived", "confidence", "source", "session_id",
		"origin", "hit_count",
	}
	updatedChildSequence := childSequence
	for _, column := range payloadColumns {
		result, err := tx.ExecContext(ctx, fmt.Sprintf(
			"UPDATE hierarchical_facts SET %s = %s WHERE id = ?", column, column,
		), child.ID)
		if err != nil {
			return fmt.Errorf("incompatible fact export sequence: payload UPDATE for %s rejected: %w", column, err)
		}
		if changed, _ := result.RowsAffected(); changed != 1 {
			return fmt.Errorf("incompatible fact export sequence: payload UPDATE for %s changed %d rows", column, changed)
		}
		candidateSequence, err := sequenceFor(child.ID)
		if err != nil {
			return fmt.Errorf("incompatible fact export sequence: payload UPDATE trigger lost mapping for %s: %w", column, err)
		}
		if candidateSequence <= updatedChildSequence {
			return fmt.Errorf("incompatible fact export sequence: payload UPDATE trigger kept sequence %d after %d for %s", candidateSequence, updatedChildSequence, column)
		}
		updatedChildSequence = candidateSequence
	}

	result, err := tx.ExecContext(ctx, `UPDATE hierarchical_facts
		SET project_id = ? WHERE id = ?`, movedProjectID, parent.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: parent boundary UPDATE rejected: %w", err)
	}
	if changed, _ := result.RowsAffected(); changed != 1 {
		return fmt.Errorf("incompatible fact export sequence: parent boundary UPDATE changed %d rows", changed)
	}
	boundaryChildSequence, err := sequenceFor(child.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: parent boundary trigger did not renew child mapping: %w", err)
	}
	if boundaryChildSequence <= updatedChildSequence {
		return fmt.Errorf("incompatible fact export sequence: parent boundary trigger kept child sequence %d after %d", boundaryChildSequence, updatedChildSequence)
	}

	// Make the child mapping the maximum sequence immediately before deletion.
	// Reinsert must then advance beyond it; a plain INTEGER PRIMARY KEY table
	// would reuse the deleted maximum and invalidate snapshot isolation.
	_, err = tx.ExecContext(ctx, `UPDATE hierarchical_facts
		SET hit_count = COALESCE(hit_count, 0) + 1 WHERE id = ?`, child.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: pre-delete UPDATE rejected: %w", err)
	}
	deletedChildSequence, err := sequenceFor(child.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: pre-delete UPDATE did not renew mapping: %w", err)
	}
	if deletedChildSequence <= boundaryChildSequence {
		return fmt.Errorf("incompatible fact export sequence: pre-delete UPDATE kept sequence %d after %d", deletedChildSequence, boundaryChildSequence)
	}
	result, err = tx.ExecContext(ctx, `DELETE FROM hierarchical_facts WHERE id = ?`, child.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: child DELETE rejected: %w", err)
	}
	if changed, _ := result.RowsAffected(); changed != 1 {
		return fmt.Errorf("incompatible fact export sequence: child DELETE changed %d rows", changed)
	}
	var childMappings int
	if err := tx.QueryRowContext(ctx,
		`SELECT COUNT(*) FROM fact_export_sequence WHERE fact_id = ?`, child.ID,
	).Scan(&childMappings); err != nil {
		return fmt.Errorf("incompatible fact export sequence: inspect deleted child mapping: %w", err)
	}
	if childMappings != 0 {
		return fmt.Errorf("incompatible fact export sequence: DELETE trigger retained %d child mappings", childMappings)
	}
	if err := insertFact(child, projectID); err != nil {
		return fmt.Errorf("incompatible fact export sequence: child reinsert rejected: %w", err)
	}
	reinsertedChildSequence, err := sequenceFor(child.ID)
	if err != nil {
		return fmt.Errorf("incompatible fact export sequence: deleted maximum sequence was reused: %w", err)
	}
	if reinsertedChildSequence <= deletedChildSequence {
		return fmt.Errorf("incompatible fact export sequence: deleted maximum sequence %d was reused as %d", deletedChildSequence, reinsertedChildSequence)
	}

	if _, err := tx.ExecContext(ctx, `DELETE FROM hierarchical_facts WHERE id IN (?, ?)`, child.ID, parent.ID); err != nil {
		return fmt.Errorf("incompatible fact export sequence: final DELETE rejected: %w", err)
	}
	var retainedMappings int
	if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM fact_export_sequence
		WHERE fact_id IN (?, ?)`, child.ID, parent.ID).Scan(&retainedMappings); err != nil {
		return fmt.Errorf("incompatible fact export sequence: inspect final mappings: %w", err)
	}
	if retainedMappings != 0 {
		return fmt.Errorf("incompatible fact export sequence: DELETE trigger retained %d final mappings", retainedMappings)
	}
	if err := tx.Rollback(); err != nil {
		return fmt.Errorf("validate fact export sequence behavior: roll back probe: %w", err)
	}
	return nil
}

type sqliteColumnShape struct {
	name       string
	declType   string
	notNull    int
	primaryKey int
	hasDefault bool
}

func (r *FactRepo) validateSessionTurnReceiptSchema() error {
	rows, err := r.db.Query(`PRAGMA table_info('session_turn_receipts')`)
	if err != nil {
		return fmt.Errorf("inspect session turn receipt columns: %w", err)
	}
	var columns []sqliteColumnShape
	for rows.Next() {
		var cid int
		var column sqliteColumnShape
		var defaultValue sql.NullString
		if err := rows.Scan(
			&cid, &column.name, &column.declType, &column.notNull, &defaultValue, &column.primaryKey,
		); err != nil {
			rows.Close()
			return fmt.Errorf("scan session turn receipt columns: %w", err)
		}
		column.declType = strings.ToUpper(column.declType)
		column.hasDefault = defaultValue.Valid
		columns = append(columns, column)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return fmt.Errorf("iterate session turn receipt columns: %w", err)
	}
	rows.Close()
	expectedColumns := []sqliteColumnShape{
		{name: "tenant_id", declType: "TEXT", notNull: 1, primaryKey: 1},
		{name: "project_id", declType: "TEXT", notNull: 1, primaryKey: 2},
		{name: "session_id", declType: "TEXT", notNull: 1, primaryKey: 3},
		{name: "turn_id", declType: "TEXT", notNull: 1, primaryKey: 4},
		{name: "fact_id", declType: "TEXT", notNull: 1},
		{name: "payload_version", declType: "INTEGER", notNull: 1},
		{name: "payload_sha256", declType: "TEXT", notNull: 1},
		{name: "created_at", declType: "TEXT", notNull: 1},
	}
	if !sameSQLiteColumnShapes(columns, expectedColumns) {
		return fmt.Errorf("incompatible session_turn_receipts schema: exact v3.4 columns required")
	}

	var childUniqueIndexCount int
	if err := r.db.QueryRow(`SELECT COUNT(*) FROM pragma_index_list(?) WHERE "unique" = 1`,
		"session_turn_receipts").Scan(&childUniqueIndexCount); err != nil {
		return fmt.Errorf("inspect session_turn_receipts unique index count: %w", err)
	}
	if childUniqueIndexCount != 2 {
		return fmt.Errorf("incompatible session_turn_receipts schema: exact unique constraints required")
	}
	childIndexes, err := r.uniqueIndexColumns("session_turn_receipts")
	if err != nil {
		return err
	}
	if !containsExactColumns(childIndexes, []string{"fact_id"}) {
		return fmt.Errorf("incompatible session_turn_receipts schema: fact_id must be unique")
	}
	if !containsExactColumns(childIndexes, []string{"tenant_id", "project_id", "session_id", "turn_id"}) {
		return fmt.Errorf("incompatible session_turn_receipts schema: exact BINARY primary key required")
	}
	parentIndexes, err := r.uniqueIndexColumns("hierarchical_facts")
	if err != nil {
		return err
	}
	var parentUniqueIndexCount int
	if err := r.db.QueryRow(`SELECT COUNT(*) FROM pragma_index_list(?) WHERE "unique" = 1`,
		"hierarchical_facts").Scan(&parentUniqueIndexCount); err != nil {
		return fmt.Errorf("inspect hierarchical_facts unique index count: %w", err)
	}
	if parentUniqueIndexCount != 2 {
		return fmt.Errorf("incompatible hierarchical_facts schema: exact unique constraints required")
	}
	if !containsExactColumns(parentIndexes, []string{"tenant_id", "project_id", "session_id", "id"}) {
		return fmt.Errorf("incompatible hierarchical_facts schema: exact receipt parent identity must be unique")
	}

	foreignKeys, err := r.sessionTurnReceiptForeignKeys()
	if err != nil {
		return err
	}
	expectedForeignKeys := []sqliteForeignKeyShape{
		{sequence: 0, table: "hierarchical_facts", from: "tenant_id", to: "tenant_id"},
		{sequence: 1, table: "hierarchical_facts", from: "project_id", to: "project_id"},
		{sequence: 2, table: "hierarchical_facts", from: "session_id", to: "session_id"},
		{sequence: 3, table: "hierarchical_facts", from: "fact_id", to: "id"},
	}
	if !sameSQLiteForeignKeys(foreignKeys, expectedForeignKeys) {
		return fmt.Errorf("incompatible session_turn_receipts schema: exact fact foreign key required")
	}
	return r.validateSessionTurnReceiptBehavior()
}

// validateSessionTurnReceiptBehavior verifies the parts of the SQLite schema that the PRAGMA
// metadata cannot describe: CHECK semantics and exact case-sensitive key comparison. Reading and
// normalising sqlite_master.sql is not sufficient here. Comments can impersonate constraints, and
// case-folding the DDL also case-folds string literals and silently approves the opposite grammar.
//
// Every probe runs in one transaction that is always rolled back, so startup validation leaves no
// synthetic rows behind. Three valid scopes intentionally reuse one session/turn pair: this also
// proves that no extra UNIQUE constraint collapsed either tenant or project out of the boundary.
func (r *FactRepo) validateSessionTurnReceiptBehavior() error {
	ctx := context.Background()
	probeFacts := []*memory.Fact{
		memory.NewFact("session receipt schema probe", memory.LevelProject, "schema", "migration"),
		memory.NewFact("session receipt empty-session probe", memory.LevelProject, "schema", "migration"),
		memory.NewFact("session receipt project-boundary probe", memory.LevelProject, "schema", "migration"),
		memory.NewFact("session receipt tenant-boundary probe", memory.LevelProject, "schema", "migration"),
	}
	for index, fact := range probeFacts {
		fact.Origin = memory.OriginBuiltin
		fact.ID = fmt.Sprintf("ReceiptProbeFact%c-%s", 'A'+rune(index), fact.ID)
	}
	seed := probeFacts[0].ID + ":" + probeFacts[1].ID
	seedDigest := fmt.Sprintf("%x", sha256.Sum256([]byte(seed)))
	tenantA := "ReceiptProbeTenantA-" + seedDigest[:12]
	tenantB := "ReceiptProbeTenantB-" + seedDigest[:12]
	projectA := "ReceiptProbeProjectA-" + seedDigest[12:24]
	projectB := "ReceiptProbeProjectB-" + seedDigest[12:24]
	sessionID := "ReceiptProbeSession-" + seedDigest[24:36]
	turnID := "turn_" + seedDigest
	payloadSHA256 := seedDigest
	now := time.Now().UTC().Round(0).Format(timeFormat)

	type parentProbe struct {
		fact                *memory.Fact
		tenantID, projectID string
		sessionID           string
	}
	parents := []parentProbe{
		{fact: probeFacts[0], tenantID: tenantA, projectID: projectA, sessionID: sessionID},
		{fact: probeFacts[1], tenantID: tenantA, projectID: projectA, sessionID: ""},
		{fact: probeFacts[2], tenantID: tenantA, projectID: projectB, sessionID: sessionID},
		{fact: probeFacts[3], tenantID: tenantB, projectID: projectA, sessionID: sessionID},
	}

	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("validate session turn receipt behavior: begin probe: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	for _, parent := range parents {
		_, err := tx.ExecContext(ctx, `INSERT INTO hierarchical_facts
			(id, tenant_id, project_id, content, level, created_at, valid_from,
			 is_stale, is_archived, confidence, source, session_id, origin)
			VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 1.0, 'session_memory', ?, 'derived')`,
			parent.fact.ID, parent.tenantID, parent.projectID, parent.fact.Content,
			int(parent.fact.Level), now, now, parent.sessionID)
		if err != nil {
			return fmt.Errorf("incompatible hierarchical_facts schema: receipt probe parent rejected: %w", err)
		}
	}

	insertReceipt := func(
		tenantID, projectID, candidateSessionID, candidateTurnID, factID string,
		payloadVersion int, candidatePayloadSHA256 string,
	) error {
		_, err := tx.ExecContext(ctx, `INSERT INTO session_turn_receipts
			(tenant_id, project_id, session_id, turn_id, fact_id,
			 payload_version, payload_sha256, created_at)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			tenantID, projectID, candidateSessionID, candidateTurnID, factID,
			payloadVersion, candidatePayloadSHA256, now)
		return err
	}

	invalidProbes := []struct {
		name                                  string
		sessionID, turnID, factID, payloadSHA string
		payloadVersion                        int
	}{
		{
			name: "empty session_id", sessionID: "", turnID: turnID,
			factID: probeFacts[1].ID, payloadVersion: sessionTurnPayloadVersion,
			payloadSHA: payloadSHA256,
		},
		{
			name: "short turn_id", sessionID: sessionID,
			turnID: turnID[:len(turnID)-1], factID: probeFacts[0].ID,
			payloadVersion: sessionTurnPayloadVersion, payloadSHA: payloadSHA256,
		},
		{
			name: "long turn_id", sessionID: sessionID,
			turnID: turnID + "a", factID: probeFacts[0].ID,
			payloadVersion: sessionTurnPayloadVersion, payloadSHA: payloadSHA256,
		},
		{
			name: "uppercase turn_id prefix", sessionID: sessionID,
			turnID: "TURN_" + seedDigest, factID: probeFacts[0].ID,
			payloadVersion: sessionTurnPayloadVersion, payloadSHA: payloadSHA256,
		},
		{
			name: "non-hex turn_id", sessionID: sessionID,
			turnID: turnID[:len(turnID)-1] + "z", factID: probeFacts[0].ID,
			payloadVersion: sessionTurnPayloadVersion, payloadSHA: payloadSHA256,
		},
		{
			name: "uppercase turn_id hex", sessionID: sessionID,
			turnID: turnID[:len(turnID)-1] + "A", factID: probeFacts[0].ID,
			payloadVersion: sessionTurnPayloadVersion, payloadSHA: payloadSHA256,
		},
		{
			name: "low payload_version", sessionID: sessionID, turnID: turnID,
			factID: probeFacts[0].ID, payloadVersion: sessionTurnPayloadVersion - 1,
			payloadSHA: payloadSHA256,
		},
		{
			name: "high payload_version", sessionID: sessionID, turnID: turnID,
			factID: probeFacts[0].ID, payloadVersion: sessionTurnPayloadVersion + 1,
			payloadSHA: payloadSHA256,
		},
		{
			name: "short payload_sha256", sessionID: sessionID, turnID: turnID,
			factID: probeFacts[0].ID, payloadVersion: sessionTurnPayloadVersion,
			payloadSHA: payloadSHA256[:len(payloadSHA256)-1],
		},
		{
			name: "long payload_sha256", sessionID: sessionID, turnID: turnID,
			factID: probeFacts[0].ID, payloadVersion: sessionTurnPayloadVersion,
			payloadSHA: payloadSHA256 + "a",
		},
		{
			name: "non-hex payload_sha256", sessionID: sessionID, turnID: turnID,
			factID: probeFacts[0].ID, payloadVersion: sessionTurnPayloadVersion,
			payloadSHA: payloadSHA256[:len(payloadSHA256)-1] + "g",
		},
		{
			name: "uppercase payload_sha256 hex", sessionID: sessionID, turnID: turnID,
			factID: probeFacts[0].ID, payloadVersion: sessionTurnPayloadVersion,
			payloadSHA: payloadSHA256[:len(payloadSHA256)-1] + "A",
		},
	}
	for _, probe := range invalidProbes {
		if err := insertReceipt(
			tenantA, projectA, probe.sessionID, probe.turnID, probe.factID,
			probe.payloadVersion, probe.payloadSHA,
		); err == nil {
			return fmt.Errorf(
				"incompatible session_turn_receipts schema: %s constraint is not enforced", probe.name,
			)
		}
	}

	validProbes := []parentProbe{parents[0], parents[2], parents[3]}
	for _, probe := range validProbes {
		if err := insertReceipt(
			probe.tenantID, probe.projectID, probe.sessionID, turnID, probe.fact.ID,
			sessionTurnPayloadVersion, payloadSHA256,
		); err != nil {
			return fmt.Errorf("incompatible session_turn_receipts schema: valid receipt rejected: %w", err)
		}
	}

	type receiptKey struct {
		tenantID, projectID, sessionID, turnID string
	}
	baseKey := receiptKey{tenantID: tenantA, projectID: projectA, sessionID: sessionID, turnID: turnID}
	receiptAliases := []receiptKey{
		{tenantID: strings.ToLower(tenantA), projectID: projectA, sessionID: sessionID, turnID: turnID},
		{tenantID: tenantA, projectID: strings.ToLower(projectA), sessionID: sessionID, turnID: turnID},
		{tenantID: tenantA, projectID: projectA, sessionID: strings.ToLower(sessionID), turnID: turnID},
		{tenantID: tenantA, projectID: projectA, sessionID: sessionID, turnID: strings.ToUpper(turnID)},
	}
	for _, alias := range receiptAliases {
		var matches int
		if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM session_turn_receipts
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
			alias.tenantID, alias.projectID, alias.sessionID, alias.turnID,
		).Scan(&matches); err != nil {
			return fmt.Errorf("validate session_turn_receipts exact comparison: %w", err)
		}
		if matches != 0 {
			return fmt.Errorf("incompatible session_turn_receipts schema: exact BINARY key comparison required")
		}
	}

	factAliases := []receiptKey{
		{tenantID: strings.ToLower(tenantA), projectID: projectA, sessionID: sessionID, turnID: probeFacts[0].ID},
		{tenantID: tenantA, projectID: strings.ToLower(projectA), sessionID: sessionID, turnID: probeFacts[0].ID},
		{tenantID: tenantA, projectID: projectA, sessionID: strings.ToLower(sessionID), turnID: probeFacts[0].ID},
		{tenantID: tenantA, projectID: projectA, sessionID: sessionID, turnID: strings.ToUpper(probeFacts[0].ID)},
	}
	for _, alias := range factAliases {
		var matches int
		if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM hierarchical_facts
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND id = ?`,
			alias.tenantID, alias.projectID, alias.sessionID, alias.turnID,
		).Scan(&matches); err != nil {
			return fmt.Errorf("validate hierarchical_facts exact comparison: %w", err)
		}
		if matches != 0 {
			return fmt.Errorf("incompatible hierarchical_facts schema: exact BINARY key comparison required")
		}
	}

	var exactMatches int
	if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		baseKey.tenantID, baseKey.projectID, baseKey.sessionID, baseKey.turnID,
	).Scan(&exactMatches); err != nil {
		return fmt.Errorf("validate session_turn_receipts exact lookup: %w", err)
	}
	if exactMatches != 1 {
		return fmt.Errorf("incompatible session_turn_receipts schema: exact receipt lookup failed")
	}

	// A v3.3 writer knows hierarchical_facts but not receipts. Once a v3.4 receipt exists, no
	// UPDATE or DELETE issued by that writer may invalidate the atomically committed pair.
	if _, err := tx.ExecContext(ctx, `UPDATE hierarchical_facts SET content = content || '-tampered'
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		probeFacts[0].ID, tenantA, projectA, sessionID,
	); err == nil {
		return fmt.Errorf("incompatible session_turn_receipts schema: receipt-backed fact UPDATE is not immutable")
	}
	// Defer the composite FK for this transaction so a DELETE rejection proves the trigger itself
	// fired. With immediate FKs, a missing DELETE trigger would be masked by the parent constraint.
	if _, err := tx.ExecContext(ctx, `PRAGMA defer_foreign_keys = ON`); err != nil {
		return fmt.Errorf("defer foreign keys for receipt-backed fact DELETE probe: %w", err)
	}
	var foreignKeysDeferred int
	if err := tx.QueryRowContext(ctx, `PRAGMA defer_foreign_keys`).Scan(&foreignKeysDeferred); err != nil {
		return fmt.Errorf("verify deferred foreign keys for receipt-backed fact DELETE probe: %w", err)
	}
	if foreignKeysDeferred != 1 {
		return fmt.Errorf("validate receipt-backed fact DELETE trigger: foreign keys were not deferred")
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		probeFacts[0].ID, tenantA, projectA, sessionID,
	); err == nil {
		return fmt.Errorf("incompatible session_turn_receipts schema: receipt-backed fact DELETE is not immutable")
	}
	var protectedContent string
	if err := tx.QueryRowContext(ctx, `SELECT content FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		probeFacts[0].ID, tenantA, projectA, sessionID,
	).Scan(&protectedContent); err != nil {
		return fmt.Errorf("validate receipt-backed fact immutability: %w", err)
	}
	if protectedContent != probeFacts[0].Content {
		return fmt.Errorf("incompatible session_turn_receipts schema: rejected UPDATE changed receipt-backed fact")
	}

	// The triggers are deliberately conditional. Legacy rows remain writable, and an erasure
	// transaction can remove the receipt before its fact. Production tenant erasure removes the
	// stopped tenant store as a whole; this probe also preserves an ordered SQL erasure path.
	result, err := tx.ExecContext(ctx, `UPDATE hierarchical_facts SET content = content || '-updated'
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ''`,
		probeFacts[1].ID, tenantA, projectA,
	)
	if err != nil {
		return fmt.Errorf("incompatible session_turn_receipts schema: non-receipt fact UPDATE rejected: %w", err)
	}
	if changed, _ := result.RowsAffected(); changed != 1 {
		return fmt.Errorf("incompatible session_turn_receipts schema: non-receipt fact UPDATE changed %d rows", changed)
	}
	result, err = tx.ExecContext(ctx, `DELETE FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ''`,
		probeFacts[1].ID, tenantA, projectA,
	)
	if err != nil {
		return fmt.Errorf("incompatible session_turn_receipts schema: non-receipt fact DELETE rejected: %w", err)
	}
	if changed, _ := result.RowsAffected(); changed != 1 {
		return fmt.Errorf("incompatible session_turn_receipts schema: non-receipt fact DELETE changed %d rows", changed)
	}

	erasureParent := parents[2]
	result, err = tx.ExecContext(ctx, `DELETE FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND fact_id = ?`,
		erasureParent.tenantID, erasureParent.projectID, erasureParent.sessionID, erasureParent.fact.ID,
	)
	if err != nil {
		return fmt.Errorf("incompatible session_turn_receipts schema: ordered receipt erasure rejected: %w", err)
	}
	if changed, _ := result.RowsAffected(); changed != 1 {
		return fmt.Errorf("incompatible session_turn_receipts schema: ordered receipt erasure changed %d rows", changed)
	}
	result, err = tx.ExecContext(ctx, `DELETE FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		erasureParent.fact.ID, erasureParent.tenantID, erasureParent.projectID, erasureParent.sessionID,
	)
	if err != nil {
		return fmt.Errorf("incompatible session_turn_receipts schema: ordered fact erasure rejected: %w", err)
	}
	if changed, _ := result.RowsAffected(); changed != 1 {
		return fmt.Errorf("incompatible session_turn_receipts schema: ordered fact erasure changed %d rows", changed)
	}
	if err := tx.Rollback(); err != nil {
		return fmt.Errorf("validate session turn receipt behavior: roll back probe: %w", err)
	}
	return nil
}

func sameSQLiteColumnShapes(left, right []sqliteColumnShape) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func (r *FactRepo) uniqueIndexColumns(table string) ([][]string, error) {
	rows, err := r.db.Query(`SELECT name, "unique", partial FROM pragma_index_list(?)`, table)
	if err != nil {
		return nil, fmt.Errorf("inspect %s indexes: %w", table, err)
	}
	var uniqueNames []string
	for rows.Next() {
		var name string
		var unique, partial int
		if err := rows.Scan(&name, &unique, &partial); err != nil {
			rows.Close()
			return nil, fmt.Errorf("scan %s indexes: %w", table, err)
		}
		if unique == 1 && partial == 0 {
			uniqueNames = append(uniqueNames, name)
		}
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, fmt.Errorf("iterate %s indexes: %w", table, err)
	}
	rows.Close()

	indexes := make([][]string, 0, len(uniqueNames))
	for _, name := range uniqueNames {
		indexRows, err := r.db.Query(
			`SELECT name, "desc", coll, key FROM pragma_index_xinfo(?) ORDER BY seqno`, name,
		)
		if err != nil {
			return nil, fmt.Errorf("inspect index %s: %w", name, err)
		}
		var columns []string
		valid := true
		for indexRows.Next() {
			var column sql.NullString
			var descending, key int
			var collation sql.NullString
			if err := indexRows.Scan(&column, &descending, &collation, &key); err != nil {
				indexRows.Close()
				return nil, fmt.Errorf("scan index %s: %w", name, err)
			}
			if key == 0 {
				continue
			}
			if !column.Valid || descending != 0 || !collation.Valid || collation.String != "BINARY" {
				valid = false
				continue
			}
			columns = append(columns, column.String)
		}
		if err := indexRows.Err(); err != nil {
			indexRows.Close()
			return nil, fmt.Errorf("iterate index %s: %w", name, err)
		}
		indexRows.Close()
		if valid {
			indexes = append(indexes, columns)
		}
	}
	return indexes, nil
}

func containsExactColumns(indexes [][]string, expected []string) bool {
	for _, columns := range indexes {
		if len(columns) != len(expected) {
			continue
		}
		matches := true
		for index := range columns {
			if columns[index] != expected[index] {
				matches = false
				break
			}
		}
		if matches {
			return true
		}
	}
	return false
}

type sqliteForeignKeyShape struct {
	id       int
	sequence int
	table    string
	from     string
	to       string
	onUpdate string
	onDelete string
	match    string
}

func (r *FactRepo) sessionTurnReceiptForeignKeys() ([]sqliteForeignKeyShape, error) {
	rows, err := r.db.Query(`PRAGMA foreign_key_list('session_turn_receipts')`)
	if err != nil {
		return nil, fmt.Errorf("inspect session turn receipt foreign keys: %w", err)
	}
	var foreignKeys []sqliteForeignKeyShape
	for rows.Next() {
		var foreignKey sqliteForeignKeyShape
		if err := rows.Scan(
			&foreignKey.id, &foreignKey.sequence, &foreignKey.table,
			&foreignKey.from, &foreignKey.to, &foreignKey.onUpdate,
			&foreignKey.onDelete, &foreignKey.match,
		); err != nil {
			rows.Close()
			return nil, fmt.Errorf("scan session turn receipt foreign keys: %w", err)
		}
		foreignKeys = append(foreignKeys, foreignKey)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, fmt.Errorf("iterate session turn receipt foreign keys: %w", err)
	}
	rows.Close()
	sort.Slice(foreignKeys, func(i, j int) bool {
		if foreignKeys[i].id == foreignKeys[j].id {
			return foreignKeys[i].sequence < foreignKeys[j].sequence
		}
		return foreignKeys[i].id < foreignKeys[j].id
	})
	return foreignKeys, nil
}

func sameSQLiteForeignKeys(left, right []sqliteForeignKeyShape) bool {
	if len(left) != len(right) {
		return false
	}
	if len(left) > 0 {
		leftID := left[0].id
		for _, foreignKey := range left {
			if foreignKey.id != leftID || foreignKey.onUpdate != "NO ACTION" ||
				foreignKey.onDelete != "NO ACTION" || foreignKey.match != "NONE" {
				return false
			}
		}
	}
	for index := range left {
		if left[index].sequence != right[index].sequence ||
			left[index].table != right[index].table || left[index].from != right[index].from ||
			left[index].to != right[index].to {
			return false
		}
	}
	return true
}

func (r *FactRepo) seedProjectsFromFacts() error {
	now := time.Now().UTC().Format(timeFormat)
	_, err := r.db.Exec(`INSERT OR IGNORE INTO rlm_projects
		(tenant_id, project_id, name, status, created_at, updated_at, last_accessed_at)
		SELECT
			COALESCE(NULLIF(tenant_id, ''), ?),
			COALESCE(NULLIF(project_id, ''), ?),
			COALESCE(NULLIF(project_id, ''), ?),
			?,
			COALESCE(MIN(created_at), ?),
			COALESCE(MAX(created_at), ?),
			COALESCE(MAX(last_accessed_at), MAX(created_at), ?)
		FROM hierarchical_facts
		GROUP BY COALESCE(NULLIF(tenant_id, ''), ?), COALESCE(NULLIF(project_id, ''), ?)`,
		rlmscope.DefaultTenantID, rlmscope.DefaultProjectID, rlmscope.DefaultProjectID,
		rlmscope.ProjectStatusActive, now, now, now,
		rlmscope.DefaultTenantID, rlmscope.DefaultProjectID)
	if err != nil {
		return fmt.Errorf("seed rlm projects from facts: %w", err)
	}
	return nil
}

func (r *FactRepo) migrateDomainCentroidsScope() error {
	var tableSQL string
	if err := r.db.QueryRow(`SELECT sql FROM sqlite_master WHERE type='table' AND name='domain_centroids'`).Scan(&tableSQL); err != nil {
		return nil
	}
	if strings.Contains(tableSQL, "PRIMARY KEY (tenant_id, project_id, domain)") {
		return nil
	}
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS domain_centroids_scoped (
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			domain TEXT NOT NULL,
			centroid BLOB NOT NULL,
			fact_count INTEGER DEFAULT 0,
			updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (tenant_id, project_id, domain)
		)`,
		`INSERT OR IGNORE INTO domain_centroids_scoped
			(tenant_id, project_id, domain, centroid, fact_count, updated_at)
			SELECT COALESCE(tenant_id, 'local'), COALESCE(project_id, 'default'),
			       domain, centroid, fact_count, updated_at
			FROM domain_centroids`,
		`DROP TABLE domain_centroids`,
		`ALTER TABLE domain_centroids_scoped RENAME TO domain_centroids`,
	}
	for _, stmt := range stmts {
		if _, err := r.db.Exec(stmt); err != nil {
			return fmt.Errorf("migrate domain_centroids scope: %w", err)
		}
	}
	return nil
}

func (r *FactRepo) ensureProject(_ context.Context, sc rlmscope.Scope) error {
	sc = sc.Normalize()
	now := time.Now().UTC().Format(timeFormat)
	_, err := r.db.Exec(`INSERT OR IGNORE INTO rlm_projects
		(tenant_id, project_id, name, status, created_at, updated_at, last_accessed_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		sc.TenantID, sc.ProjectID, sc.ProjectID, rlmscope.ProjectStatusActive, now, now, now)
	if err != nil {
		return fmt.Errorf("ensure rlm project: %w", err)
	}
	return nil
}

func (r *FactRepo) ensureProjectWritable(ctx context.Context, sc rlmscope.Scope) error {
	sc = sc.Normalize()
	if err := r.ensureProject(ctx, sc); err != nil {
		return err
	}
	status := rlmscope.ProjectStatusActive
	err := r.db.QueryRow(`SELECT status FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, sc.TenantID, sc.ProjectID).Scan(&status)
	if err != nil {
		return fmt.Errorf("check rlm project status: %w", err)
	}
	if status == rlmscope.ProjectStatusArchived {
		return fmt.Errorf("project %s is archived; activate_project before writing", sc.String())
	}
	return r.touchProject(sc)
}

func (r *FactRepo) touchProject(sc rlmscope.Scope) error {
	sc = sc.Normalize()
	now := time.Now().UTC().Format(timeFormat)
	_, err := r.db.Exec(`UPDATE rlm_projects SET last_accessed_at = ?
		WHERE tenant_id = ? AND project_id = ?`, now, sc.TenantID, sc.ProjectID)
	if err != nil {
		return fmt.Errorf("touch rlm project: %w", err)
	}
	return nil
}

func scopedFact(ctx context.Context, fact *memory.Fact) rlmscope.Scope {
	sc := rlmscope.FromContext(ctx)
	fact.TenantID = sc.TenantID
	fact.ProjectID = sc.ProjectID
	return sc
}

func (r *FactRepo) requireParentInExactBoundary(ctx context.Context, sc rlmscope.Scope, fact *memory.Fact) error {
	if fact == nil || fact.ParentID == "" {
		return nil
	}
	var count int
	err := r.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND IFNULL(session_id, '') = IFNULL(?, '')`,
		fact.ParentID, sc.TenantID, sc.ProjectID, nullStr(fact.SessionID),
	).Scan(&count)
	if err != nil {
		return fmt.Errorf("check parent fact boundary: %w", err)
	}
	if count != 1 {
		return fmt.Errorf("parent fact %s not found in exact memory boundary", fact.ParentID)
	}
	return nil
}

func requireParentInExactBoundaryTx(ctx context.Context, tx *sql.Tx, sc rlmscope.Scope, fact *memory.Fact) error {
	if fact == nil || fact.ParentID == "" {
		return nil
	}
	var count int
	err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND IFNULL(session_id, '') = IFNULL(?, '')`,
		fact.ParentID, sc.TenantID, sc.ProjectID, nullStr(fact.SessionID),
	).Scan(&count)
	if err != nil {
		return fmt.Errorf("check parent fact boundary: %w", err)
	}
	if count != 1 {
		return fmt.Errorf("parent fact %s not found in exact memory boundary", fact.ParentID)
	}
	return nil
}

// acquireProjectWriteTx is deliberately the first statement in every fact
// write transaction. Even when the insert is ignored for an existing project,
// SQLite establishes the write transaction before receipt/deduplication reads,
// so writers on separate connections cannot both observe a missing turn.
func acquireProjectWriteTx(ctx context.Context, tx *sql.Tx, sc rlmscope.Scope) (string, error) {
	sc = sc.Normalize()
	now := time.Now().UTC().Format(timeFormat)
	if _, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO rlm_projects
		(tenant_id, project_id, name, status, created_at, updated_at, last_accessed_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		sc.TenantID, sc.ProjectID, sc.ProjectID, rlmscope.ProjectStatusActive, now, now, now,
	); err != nil {
		return "", fmt.Errorf("ensure rlm project: %w", err)
	}
	return now, nil
}

// requireProjectWritableAndTouchTx runs only for a genuinely new write. A
// receipt-backed retry may reconcile after the project was archived and must
// not be rejected or refresh project activity.
func requireProjectWritableAndTouchTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	now string,
) error {
	sc = sc.Normalize()
	status := rlmscope.ProjectStatusActive
	if err := tx.QueryRowContext(ctx, `SELECT status FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, sc.TenantID, sc.ProjectID).Scan(&status); err != nil {
		return fmt.Errorf("check rlm project status: %w", err)
	}
	if status == rlmscope.ProjectStatusArchived {
		return fmt.Errorf("project %s is archived; activate_project before writing", sc.String())
	}
	if _, err := tx.ExecContext(ctx, `UPDATE rlm_projects SET last_accessed_at = ?
		WHERE tenant_id = ? AND project_id = ?`, now, sc.TenantID, sc.ProjectID); err != nil {
		return fmt.Errorf("touch rlm project: %w", err)
	}
	return nil
}

// FoldExistingDuplicates collapses duplicate rows that predate deduplication on write.
//
// Called from migrate, because a cleanup nobody runs is the defect this codebase keeps finding:
// the mechanism exists, the execution does not, and the absence looks like health. It is
// idempotent — after one pass there is nothing left to group — and cheap enough to sit in startup.
//
// Losers are ARCHIVED, not deleted. Archiving takes them out of retrieval and out of the counts,
// which is the whole point, while leaving the rows recoverable if this rule turns out to be wrong
// about a pair. A migration that deletes production rows offers no such second chance.
//
// The survivor is the oldest row of the group and inherits the most trusted origin and the highest
// confidence in it — the same rule foldIntoDuplicate applies on write, so a store cleaned by this
// pass and a store built with dedup from the start end up identical.
//
// Exact session rows are deliberately excluded. This legacy startup repair predates the exact
// session API and mutates a group in multiple statements; letting it touch session rows would make
// startup an unscoped, partially applied writer. New exact writes are deduplicated atomically in
// add, and historical exact rows remain untouched until they have a dedicated repair operation.
func (r *FactRepo) FoldExistingDuplicates(ctx context.Context) (int, error) {
	type group struct {
		tenant, project, content, domain string
		level                            int
	}
	rows, err := r.db.QueryContext(ctx, `SELECT tenant_id, project_id, content, level, IFNULL(domain, '')
		FROM hierarchical_facts
		WHERE is_archived = 0 AND is_stale = 0
		  AND (session_id IS NULL OR session_id = '')
		GROUP BY tenant_id, project_id, content, level, IFNULL(domain, '')
		HAVING COUNT(*) > 1`)
	if err != nil {
		return 0, fmt.Errorf("find duplicate groups: %w", err)
	}
	var groups []group
	for rows.Next() {
		var g group
		if err := rows.Scan(&g.tenant, &g.project, &g.content, &g.level, &g.domain); err != nil {
			rows.Close()
			return 0, fmt.Errorf("scan duplicate group: %w", err)
		}
		groups = append(groups, g)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return 0, fmt.Errorf("iterate duplicate groups: %w", err)
	}
	rows.Close()

	archived := 0
	for _, g := range groups {
		members, err := r.db.QueryContext(ctx, `SELECT id, origin, confidence FROM hierarchical_facts
			WHERE tenant_id = ? AND project_id = ? AND content = ? AND level = ?
			  AND IFNULL(domain, '') = ? AND (session_id IS NULL OR session_id = '')
			  AND is_archived = 0 AND is_stale = 0
			ORDER BY created_at ASC`,
			g.tenant, g.project, g.content, g.level, g.domain)
		if err != nil {
			return archived, fmt.Errorf("read duplicate group: %w", err)
		}
		var (
			ids        []string
			origins    []memory.Origin
			confidence float64
		)
		for members.Next() {
			var (
				id     string
				origin sql.NullString
				conf   sql.NullFloat64
			)
			if err := members.Scan(&id, &origin, &conf); err != nil {
				members.Close()
				return archived, fmt.Errorf("scan duplicate member: %w", err)
			}
			ids = append(ids, id)
			origins = append(origins, normaliseOrigin(origin))
			if conf.Valid && conf.Float64 > confidence {
				confidence = conf.Float64
			}
		}
		if err := members.Err(); err != nil {
			members.Close()
			return archived, fmt.Errorf("iterate duplicate group: %w", err)
		}
		members.Close()
		if len(ids) < 2 {
			continue
		}

		if _, err := r.db.ExecContext(ctx, `UPDATE hierarchical_facts
			SET origin = ?, confidence = ?
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND (session_id IS NULL OR session_id = '')`,
			string(memory.MostTrusted(origins...)), confidence,
			ids[0], g.tenant, g.project,
		); err != nil {
			return archived, fmt.Errorf("promote duplicate survivor: %w", err)
		}
		for _, id := range ids[1:] {
			if _, err := r.db.ExecContext(ctx, `UPDATE hierarchical_facts SET is_archived = 1
				WHERE id = ? AND tenant_id = ? AND project_id = ?
				  AND (session_id IS NULL OR session_id = '')`,
				id, g.tenant, g.project,
			); err != nil {
				return archived, fmt.Errorf("archive duplicate: %w", err)
			}
			archived++
		}
	}
	return archived, nil
}

// foldIntoDuplicate merges fact into an existing identical row and reports whether it did.
//
// «Identical» is exact content within the same scope, level and domain. Deliberately exact: a
// fuzzy match would silently drop facts that differ in a negation or a number, and losing «the
// owner does NOT want metric units» because it resembles its opposite is far worse than keeping
// two rows.
//
// Archived and stale rows are not candidates. Folding a live write into an archived row would
// resurrect nothing — the content would stay invisible to retrieval while the writer is told it
// was stored.
func (r *FactRepo) foldIntoDuplicateTx(ctx context.Context, tx *sql.Tx, sc rlmscope.Scope, fact *memory.Fact) (bool, error) {
	var (
		existingID           string
		existingOrigin       sql.NullString
		existingConf         sql.NullFloat64
		existingHasEmbedding bool
	)
	err := tx.QueryRowContext(ctx, `SELECT id, origin, confidence,
			embedding IS NOT NULL AND LENGTH(embedding) > 0
		FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND content = ? AND level = ?
		  AND IFNULL(domain, '') = IFNULL(?, '')
		  AND IFNULL(session_id, '') = IFNULL(?, '')
		  AND is_archived = 0 AND is_stale = 0
		  AND NOT EXISTS (
			SELECT 1 FROM session_turn_receipts AS receipt
			WHERE receipt.fact_id = hierarchical_facts.id
		  )
		ORDER BY created_at ASC LIMIT 1`,
		sc.TenantID, sc.ProjectID, fact.Content, int(fact.Level), nullStr(fact.Domain), nullStr(fact.SessionID),
	).Scan(&existingID, &existingOrigin, &existingConf, &existingHasEmbedding)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("look for duplicate fact: %w", err)
	}

	// MostTrusted, not LeastTrusted, and the difference is load-bearing: see memory.MostTrusted.
	merged := memory.MostTrusted(normaliseOrigin(existingOrigin), fact.Origin)

	// Confidence takes the higher of the two. A repeated statement is not less certain for having
	// been said twice, and taking the lower value would let a low-confidence restatement erode a
	// fact the store was sure of.
	confidence := fact.Confidence
	if existingConf.Valid && existingConf.Float64 > confidence {
		confidence = existingConf.Float64
	}

	result, err := tx.ExecContext(ctx, `UPDATE hierarchical_facts
		SET origin = ?, confidence = ?
		WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND IFNULL(session_id, '') = IFNULL(?, '')
		  AND content = ? AND level = ? AND IFNULL(domain, '') = IFNULL(?, '')
		  AND is_archived = 0 AND is_stale = 0`,
		string(merged), confidence,
		existingID, sc.TenantID, sc.ProjectID, nullStr(fact.SessionID),
		fact.Content, int(fact.Level), nullStr(fact.Domain),
	)
	if err != nil {
		return false, fmt.Errorf("merge duplicate fact: %w", err)
	}
	if n, _ := result.RowsAffected(); n != 1 {
		return false, fmt.Errorf("merge duplicate fact: exact memory boundary changed")
	}

	// An embedding where there was none IS new information, so the incoming one is adopted.
	//
	// Otherwise: a fact stored while the embedder was unavailable keeps a NULL vector, the same
	// sentence stored later with a vector folds into it, and the fact stays permanently invisible to
	// semantic search while both writers were told it was stored. That is the shape of defect this
	// deduplication was written to remove, reintroduced by the deduplication itself.
	//
	// Only in that direction. If the surviving row already has a vector, the incoming one was
	// computed from the same text and has nothing to add — replacing it would churn the index for
	// no gain.
	if len(fact.Embedding) > 0 && !existingHasEmbedding {
		blob, err := encodeEmbedding(fact.Embedding)
		if err != nil {
			return false, err
		}
		result, err := tx.ExecContext(ctx, `UPDATE hierarchical_facts SET embedding = ?
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND IFNULL(session_id, '') = IFNULL(?, '')
			  AND content = ? AND level = ? AND IFNULL(domain, '') = IFNULL(?, '')
			  AND is_archived = 0 AND is_stale = 0`,
			blob, existingID, sc.TenantID, sc.ProjectID, nullStr(fact.SessionID),
			fact.Content, int(fact.Level), nullStr(fact.Domain),
		)
		if err != nil {
			return false, fmt.Errorf("adopt embedding on merge: %w", err)
		}
		if n, _ := result.RowsAffected(); n != 1 {
			return false, fmt.Errorf("adopt embedding on merge: exact memory boundary changed")
		}
		result, err = tx.ExecContext(ctx, `INSERT OR REPLACE INTO embeddings_index (fact_id, embedding)
			SELECT id, ? FROM hierarchical_facts
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND IFNULL(session_id, '') = IFNULL(?, '')
			  AND content = ? AND level = ? AND IFNULL(domain, '') = IFNULL(?, '')
			  AND is_archived = 0 AND is_stale = 0`,
			blob, existingID, sc.TenantID, sc.ProjectID, nullStr(fact.SessionID),
			fact.Content, int(fact.Level), nullStr(fact.Domain),
		)
		if err != nil {
			return false, fmt.Errorf("adopt embedding index on merge: %w", err)
		}
		if n, _ := result.RowsAffected(); n != 1 {
			return false, fmt.Errorf("adopt embedding index on merge: exact memory boundary changed")
		}
	}

	// The caller's handle now names the row that exists.
	fact.ID = existingID
	fact.Origin = merged
	fact.Confidence = confidence
	return true, nil
}

// Add stores a fact, or folds it into an existing row that already says exactly the same thing.
//
// Deduplication lives here rather than in the callers because this is the one sink every write
// path reaches — nine of them at last count, from the MCP add_fact tool to the STIX feed reader.
// A check in each caller is a check that the tenth caller will not have.
//
// Measured before this existed: a 13-row store on Global held 11 distinct statements, so 15% of
// what it reported as «remembered» was the same sentence written again. That is not a storage
// concern — it is a retrieval and a reporting one. Duplicates crowd out distinct facts in any
// top-K recall, and they make every count the product shows an overstatement.
//
// When a duplicate is folded in, fact.ID is rewritten to the surviving row's id: the caller asked
// the store to remember something and is owed the identity of the row that remembers it, not an
// id that was never inserted.
func (r *FactRepo) Add(ctx context.Context, fact *memory.Fact) error {
	if fact == nil {
		return fmt.Errorf("fact is required")
	}
	if fact.SessionID != "" {
		return fmt.Errorf("session facts require the dedicated session memory API")
	}
	_, _, err := r.add(ctx, fact, "", "")
	return err
}

func validateProjectExactFactInput(fact *memory.Fact) error {
	if fact == nil {
		return fmt.Errorf("fact is required")
	}
	if err := fact.Validate(); err != nil {
		return fmt.Errorf("validate exact project fact: %w", err)
	}
	if fact.SessionID != "" || fact.ParentID != "" || fact.CodeRef != "" || fact.TTL != nil ||
		fact.ValidUntil != nil || fact.IsStale || fact.IsArchived || fact.IsGene ||
		fact.Source != "add_fact" || fact.Confidence != 1 || fact.HitCount != 0 || !fact.LastAccess.IsZero() {
		return fmt.Errorf("validate exact project fact: unsupported stored fields")
	}
	switch fact.Origin {
	case memory.OriginUser, memory.OriginDerived, memory.OriginExternal:
	default:
		return fmt.Errorf("validate exact project fact: origin must be user, derived, or external")
	}
	return nil
}

func projectExactPublicFieldsMatch(expected, stored *memory.Fact) bool {
	return expected != nil && stored != nil &&
		expected.TenantID == stored.TenantID && expected.ProjectID == stored.ProjectID &&
		stored.SessionID == "" && !stored.IsStale && !stored.IsArchived &&
		expected.Content == stored.Content && expected.Level == stored.Level &&
		expected.Domain == stored.Domain && expected.Module == stored.Module &&
		expected.Origin == stored.Origin
}

func loadProjectExactFactTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	factID string,
) (*memory.Fact, error) {
	fact, storedDataInvalid, err := scanFactDetailed(tx.QueryRowContext(ctx, `SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')`,
		factID, sc.TenantID, sc.ProjectID))
	if err != nil {
		if storedDataInvalid || errors.Is(err, sql.ErrNoRows) {
			return nil, fmt.Errorf("%w: reload durable row: %v", memory.ErrExactFactIntegrity, err)
		}
		return nil, fmt.Errorf("reload exact project fact: %w", err)
	}
	if storedDataInvalid {
		return nil, fmt.Errorf("%w: durable row contains invalid data", memory.ErrExactFactIntegrity)
	}
	return fact, nil
}

func liveProjectExactCollisionIDs(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	fact *memory.Fact,
) ([]string, error) {
	rows, err := tx.QueryContext(ctx, `SELECT id FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND content = ? AND level = ?
		  AND IFNULL(domain, '') = IFNULL(?, '')
		  AND (session_id IS NULL OR session_id = '')
		  AND is_archived = 0 AND is_stale = 0
		ORDER BY created_at ASC, id ASC LIMIT 2`,
		sc.TenantID, sc.ProjectID, fact.Content, int(fact.Level), nullStr(fact.Domain))
	if err != nil {
		return nil, fmt.Errorf("find exact project fact collision: %w", err)
	}
	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			_ = rows.Close()
			return nil, fmt.Errorf("scan exact project fact collision: %w", err)
		}
		ids = append(ids, id)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, fmt.Errorf("iterate exact project fact collisions: %w", err)
	}
	if err := rows.Close(); err != nil {
		return nil, fmt.Errorf("close exact project fact collisions: %w", err)
	}
	return ids, nil
}

// StoreProjectFactExact is the non-session project write boundary used by the
// exact MCP tool. The first statement takes SQLite's writer lock before the
// collision read, so separate gomcp processes cannot both observe absence.
// Existing rows are never folded, updated, touched, or represented by the
// caller's handle: success always returns a row decoded from this transaction.
func (r *FactRepo) StoreProjectFactExact(
	ctx context.Context,
	fact *memory.Fact,
) (*memory.Fact, bool, error) {
	sc, err := rlmscope.RequireExactProject(ctx)
	if err != nil {
		return nil, false, err
	}
	if err := validateProjectExactFactInput(fact); err != nil {
		return nil, false, err
	}
	pending := *fact
	pending.TenantID = sc.TenantID
	pending.ProjectID = sc.ProjectID
	pending.SessionID = ""
	pending.CreatedAt = pending.CreatedAt.UTC().Round(0)
	pending.ValidFrom = pending.ValidFrom.UTC().Round(0)
	pending.UpdatedAt = pending.CreatedAt

	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, false, fmt.Errorf("begin exact project fact write: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	projectNow, err := acquireProjectWriteTx(ctx, tx, sc)
	if err != nil {
		return nil, false, err
	}
	var projectStatus string
	if err := tx.QueryRowContext(ctx, `SELECT status FROM rlm_projects
		WHERE tenant_id = ? AND project_id = ?`, sc.TenantID, sc.ProjectID).Scan(&projectStatus); err != nil {
		return nil, false, fmt.Errorf("check exact project status: %w", err)
	}
	if projectStatus != rlmscope.ProjectStatusActive {
		return nil, false, fmt.Errorf("%w: status %q", memory.ErrExactFactProjectArchived, projectStatus)
	}

	collisionIDs, err := liveProjectExactCollisionIDs(ctx, tx, sc, &pending)
	if err != nil {
		return nil, false, err
	}
	if len(collisionIDs) > 1 {
		return nil, false, fmt.Errorf("%w: legacy identity resolves more than one live row", memory.ErrExactFactIntegrity)
	}
	if len(collisionIDs) == 1 {
		stored, err := loadProjectExactFactTx(ctx, tx, sc, collisionIDs[0])
		if err != nil {
			return nil, false, err
		}
		if !projectExactPublicFieldsMatch(&pending, stored) {
			return nil, false, memory.ErrExactFactConflict
		}
		if err := tx.Commit(); err != nil {
			return nil, false, fmt.Errorf("commit exact project fact replay: %w", err)
		}
		return stored, false, nil
	}

	if err := requireProjectWritableAndTouchTx(ctx, tx, sc, projectNow); err != nil {
		return nil, false, err
	}
	embeddingBlob, err := encodeEmbedding(pending.Embedding)
	if err != nil {
		return nil, false, err
	}
	_, err = tx.ExecContext(ctx, `INSERT INTO hierarchical_facts
		(id, tenant_id, project_id, content, level, domain, module, code_ref, parent_id,
		 embedding, ttl_config, created_at, valid_from, valid_until,
		 is_stale, is_archived, confidence, source, session_id, origin)
		VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, NULL, ?, ?, NULL, 0, 0, 1, 'add_fact', NULL, ?)`,
		pending.ID, sc.TenantID, sc.ProjectID, pending.Content, int(pending.Level),
		nullStr(pending.Domain), nullStr(pending.Module), embeddingBlob,
		pending.CreatedAt.Format(timeFormat), pending.ValidFrom.Format(timeFormat), string(pending.Origin))
	if err != nil {
		return nil, false, fmt.Errorf("insert exact project fact: %w", err)
	}
	if len(pending.Embedding) > 0 {
		result, err := tx.ExecContext(ctx, `INSERT INTO embeddings_index (fact_id, embedding)
			VALUES (?, ?)`, pending.ID, embeddingBlob)
		if err != nil {
			return nil, false, fmt.Errorf("insert exact project fact embedding index: %w", err)
		}
		if n, _ := result.RowsAffected(); n != 1 {
			return nil, false, fmt.Errorf("%w: embedding index insert did not affect one row", memory.ErrExactFactIntegrity)
		}
	}

	stored, err := loadProjectExactFactTx(ctx, tx, sc, pending.ID)
	if err != nil {
		return nil, false, err
	}
	if !projectExactPublicFieldsMatch(&pending, stored) {
		return nil, false, fmt.Errorf("%w: reloaded row does not attest the exact request", memory.ErrExactFactIntegrity)
	}
	if err := tx.Commit(); err != nil {
		return nil, false, fmt.Errorf("commit exact project fact write: %w", err)
	}
	return stored, true, nil
}

// sessionTurnPayloadSHA256 is the integrity digest for the complete stored fact
// and the fallback dedup identity when either side lacks a valid request ref.
// Generated identity/timestamps and the embedding are excluded because they may
// legitimately differ across a retry; caller-controlled expiry/lifecycle fields
// remain bound to the receipt.
func sessionTurnPayloadSHA256(sc rlmscope.Scope, sessionID string, fact *memory.Fact) string {
	hasher := sha256.New()
	writeString := func(value string) {
		var size [8]byte
		binary.BigEndian.PutUint64(size[:], uint64(len(value)))
		_, _ = hasher.Write(size[:])
		_, _ = hasher.Write([]byte(value))
	}
	writeString("spectorn-session-turn-fact-v2")
	for _, value := range []string{
		sc.TenantID, sc.ProjectID, sessionID, fact.Content,
		fmt.Sprintf("%d", fact.Level), fact.Domain, fact.Module, fact.CodeRef,
		fact.ParentID, fact.Source, string(fact.Origin), fmt.Sprintf("%016x", math.Float64bits(fact.Confidence)),
	} {
		writeString(value)
	}
	if fact.TTL == nil {
		writeString("ttl:absent")
	} else {
		writeString("ttl:present")
		writeString(fmt.Sprintf("%d", fact.TTL.TTLSeconds))
		writeString(fact.TTL.RefreshTrigger)
		writeString(fact.TTL.OnExpire)
	}
	if fact.ValidUntil == nil {
		writeString("valid_until:absent")
	} else {
		writeString("valid_until:present")
		writeString(fact.ValidUntil.UTC().Format(timeFormat))
	}
	writeString(fmt.Sprintf("is_stale:%t", fact.IsStale))
	writeString(fmt.Sprintf("is_archived:%t", fact.IsArchived))
	return fmt.Sprintf("%x", hasher.Sum(nil))
}

// sessionTurnRequestRef recognises the versioned request-identity carrier used
// by scoped chat. The carrier lives in CodeRef so the durable receipt schema can
// keep PayloadSHA256 dedicated to integrity of the complete stored fact.
func sessionTurnRequestRef(codeRef string) (string, bool) {
	if len(codeRef) != len(sessionTurnRequestRefPrefix)+sha256HexLength ||
		!strings.HasPrefix(codeRef, sessionTurnRequestRefPrefix) {
		return "", false
	}
	for index := len(sessionTurnRequestRefPrefix); index < len(codeRef); index++ {
		char := codeRef[index]
		if !((char >= '0' && char <= '9') || (char >= 'a' && char <= 'f')) {
			return "", false
		}
	}
	return codeRef, true
}

func lookupSessionTurnReceiptTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	sessionID, turnID string,
	incoming *memory.Fact,
	incomingFingerprint string,
) (*memory.Fact, *memory.SessionTurnReceipt, error) {
	fact, receipt, err := loadSessionTurnReceiptTx(ctx, tx, sc, sessionID, turnID)
	if err != nil || receipt == nil {
		return fact, receipt, err
	}
	incomingRequestRef, incomingHasRequestRef := sessionTurnRequestRef(incoming.CodeRef)
	storedRequestRef, storedHasRequestRef := sessionTurnRequestRef(fact.CodeRef)
	if incomingHasRequestRef && storedHasRequestRef {
		if incomingRequestRef != storedRequestRef {
			return nil, nil, memory.ErrSessionTurnConflict
		}
		return fact, receipt, nil
	}
	if receipt.PayloadSHA256 != incomingFingerprint {
		return nil, nil, memory.ErrSessionTurnConflict
	}
	return fact, receipt, nil
}

func loadSessionTurnReceiptTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	sessionID, turnID string,
) (*memory.Fact, *memory.SessionTurnReceipt, error) {
	var factID, storedFingerprint, receiptCreatedAt string
	var payloadVersion int
	row := tx.QueryRowContext(ctx, `SELECT fact_id, payload_version, payload_sha256, created_at
		FROM session_turn_receipts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		sc.TenantID, sc.ProjectID, sessionID, turnID,
	)
	if err := row.Err(); err != nil {
		return nil, nil, fmt.Errorf("read session turn receipt: %w", err)
	}
	err := row.Scan(&factID, &payloadVersion, &storedFingerprint, &receiptCreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil, nil
	}
	if err != nil {
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return nil, nil, fmt.Errorf("read session turn receipt: %w", err)
		}
		if queryErr := row.Err(); queryErr != nil {
			return nil, nil, fmt.Errorf("read session turn receipt: %w", queryErr)
		}
		return nil, nil, fmt.Errorf("%w: malformed receipt row: %v", memory.ErrSessionTurnIntegrity, err)
	}
	if payloadVersion != sessionTurnPayloadVersion {
		return nil, nil, fmt.Errorf("%w: unsupported payload version %d", memory.ErrSessionTurnIntegrity, payloadVersion)
	}
	if _, err := time.Parse(timeFormat, receiptCreatedAt); err != nil {
		return nil, nil, fmt.Errorf("%w: invalid receipt created_at: %v", memory.ErrSessionTurnIntegrity, err)
	}
	rows, err := tx.QueryContext(ctx, `SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ? AND session_id = ?`,
		factID, sc.TenantID, sc.ProjectID, sessionID)
	if err != nil {
		return nil, nil, fmt.Errorf("resolve receipt fact query: %w", err)
	}
	defer rows.Close()
	if !rows.Next() {
		if err := rows.Err(); err != nil {
			return nil, nil, fmt.Errorf("resolve receipt fact iteration: %w", err)
		}
		return nil, nil, sessionTurnFactLoadError(false, sql.ErrNoRows)
	}
	fact, storedDataInvalid, err := scanFactDetailed(rows)
	if err != nil {
		return nil, nil, sessionTurnFactLoadError(storedDataInvalid, err)
	}
	if storedDataInvalid {
		return nil, nil, fmt.Errorf("%w: stored fact payload is invalid", memory.ErrSessionTurnIntegrity)
	}
	if rows.Next() {
		return nil, nil, fmt.Errorf("%w: receipt resolved more than one fact", memory.ErrSessionTurnIntegrity)
	}
	if err := rows.Err(); err != nil {
		return nil, nil, fmt.Errorf("resolve receipt fact iteration: %w", err)
	}
	if sessionTurnPayloadSHA256(sc, sessionID, fact) != storedFingerprint {
		return nil, nil, fmt.Errorf("%w: stored payload digest mismatch", memory.ErrSessionTurnIntegrity)
	}
	return fact, &memory.SessionTurnReceipt{
		Version: 1, TurnID: turnID, FactID: factID, PayloadSHA256: storedFingerprint,
	}, nil
}

func insertSessionTurnReceiptTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	sessionID, turnID, factID, fingerprint string,
) error {
	_, err := tx.ExecContext(ctx, `INSERT INTO session_turn_receipts
		(tenant_id, project_id, session_id, turn_id, fact_id, payload_version, payload_sha256, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`, sc.TenantID, sc.ProjectID, sessionID,
		turnID, factID, sessionTurnPayloadVersion, fingerprint, time.Now().UTC().Format(timeFormat))
	if err != nil {
		return fmt.Errorf("insert session turn receipt: %w", err)
	}
	return nil
}

func (r *FactRepo) add(
	ctx context.Context,
	fact *memory.Fact,
	sessionID, turnID string,
) (*memory.SessionTurnReceipt, bool, error) {
	// Do not mutate the caller's handle until COMMIT succeeds. In particular, a failed exact write
	// must not leave SessionID stamped or an uncommitted survivor ID/origin on the in-memory Fact.
	pending := *fact
	pending.SessionID = sessionID
	if turnID != "" {
		// These fields are not independent columns on the session-turn write path.
		// Canonicalise the returned handle to the same shape a later receipt read
		// reconstructs from SQLite. Legacy and gene writes retain their existing
		// caller-visible values; only receipt-backed turns need byte-stable replay.
		pending.IsGene = false
		pending.HitCount = 0
		pending.LastAccess = time.Time{}
		pending.CreatedAt = pending.CreatedAt.UTC().Round(0)
		pending.ValidFrom = pending.ValidFrom.UTC().Round(0)
		if pending.ValidUntil != nil {
			validUntil := pending.ValidUntil.UTC().Round(0)
			pending.ValidUntil = &validUntil
		}
		pending.UpdatedAt = pending.CreatedAt
		// SQLite stores IEEE negative zero as positive zero. Canonicalise before
		// hashing and insertion so a successful keyed write remains verifiable.
		if pending.Confidence == 0 {
			pending.Confidence = 0
		}
	}
	sc := scopedFact(ctx, &pending)

	// DB's lock normally protects one statement at a time. Hold it across this transaction so all
	// users of this DB wrapper observe the write as one indivisible operation. The underlying
	// SQLite write transaction provides the same serialization against other connections/processes.
	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, false, fmt.Errorf("begin fact write: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	projectNow, err := acquireProjectWriteTx(ctx, tx, sc)
	if err != nil {
		return nil, false, err
	}
	turnFingerprint := ""
	if turnID != "" {
		turnFingerprint = sessionTurnPayloadSHA256(sc, sessionID, &pending)
		existing, receipt, err := lookupSessionTurnReceiptTx(
			ctx, tx, sc, sessionID, turnID, &pending, turnFingerprint,
		)
		if err != nil {
			return nil, false, err
		}
		if receipt != nil {
			if err := tx.Commit(); err != nil {
				return nil, false, fmt.Errorf("commit session turn reconciliation: %w", err)
			}
			*fact = *existing
			return receipt, true, nil
		}
	}
	if err := requireProjectWritableAndTouchTx(ctx, tx, sc, projectNow); err != nil {
		return nil, false, err
	}
	if err := requireParentInExactBoundaryTx(ctx, tx, sc, &pending); err != nil {
		return nil, false, err
	}
	if turnID == "" {
		folded, err := r.foldIntoDuplicateTx(ctx, tx, sc, &pending)
		if err != nil {
			return nil, false, err
		}
		if folded {
			if err := tx.Commit(); err != nil {
				return nil, false, fmt.Errorf("commit folded fact write: %w", err)
			}
			*fact = pending
			return nil, false, nil
		}
	}
	embeddingBlob, err := encodeEmbedding(pending.Embedding)
	if err != nil {
		return nil, false, err
	}
	ttlJSON, err := encodeTTL(pending.TTL)
	if err != nil {
		return nil, false, err
	}
	var validUntil *string
	if pending.ValidUntil != nil {
		s := pending.ValidUntil.Format(timeFormat)
		validUntil = &s
	}

	_, err = tx.ExecContext(ctx, `INSERT INTO hierarchical_facts
		(id, tenant_id, project_id, content, level, domain, module, code_ref, parent_id,
		 embedding, ttl_config, created_at, valid_from, valid_until,
		 is_stale, is_archived, confidence, source, session_id, origin)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		pending.ID, pending.TenantID, pending.ProjectID, pending.Content, int(pending.Level),
		nullStr(pending.Domain), nullStr(pending.Module), nullStr(pending.CodeRef),
		nullStr(pending.ParentID),
		embeddingBlob, ttlJSON,
		pending.CreatedAt.Format(timeFormat), pending.ValidFrom.Format(timeFormat), validUntil,
		boolToInt(pending.IsStale), boolToInt(pending.IsArchived),
		pending.Confidence, pending.Source, nullStr(pending.SessionID), string(pending.Origin),
	)
	if err != nil {
		return nil, false, fmt.Errorf("insert fact: %w", err)
	}

	// Also insert into embeddings_index if embedding exists.
	if len(pending.Embedding) > 0 {
		result, indexErr := tx.ExecContext(ctx, `INSERT OR REPLACE INTO embeddings_index (fact_id, embedding)
			SELECT id, ? FROM hierarchical_facts
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND IFNULL(session_id, '') = IFNULL(?, '')`,
			embeddingBlob, pending.ID, sc.TenantID, sc.ProjectID, nullStr(pending.SessionID),
		)
		err = indexErr
		if err != nil {
			return nil, false, fmt.Errorf("insert embedding index: %w", err)
		}
		if n, _ := result.RowsAffected(); n != 1 {
			return nil, false, fmt.Errorf("insert embedding index: exact memory boundary changed")
		}
	}
	if turnID != "" {
		if err := insertSessionTurnReceiptTx(
			ctx, tx, sc, sessionID, turnID, pending.ID, turnFingerprint,
		); err != nil {
			return nil, false, err
		}
	}

	if err := tx.Commit(); err != nil {
		return nil, false, fmt.Errorf("commit fact write: %w", err)
	}
	*fact = pending

	if turnID == "" {
		return nil, false, nil
	}
	return &memory.SessionTurnReceipt{
		Version: 1, TurnID: turnID, FactID: pending.ID, PayloadSHA256: turnFingerprint,
	}, false, nil
}

// AddForSession stores a fact under an exact tenant/project/session boundary.
// It refuses the legacy implicit default scope and stamps SessionID itself so a
// caller-supplied Fact cannot redirect the write after validation.
func (r *FactRepo) AddForSession(ctx context.Context, sessionID string, fact *memory.Fact) error {
	if fact == nil {
		return fmt.Errorf("fact is required")
	}
	if _, err := rlmscope.RequireSessionScope(ctx, sessionID); err != nil {
		return err
	}
	_, _, err := r.add(ctx, fact, sessionID, "")
	return err
}

// AddTurnForSession is the durable idempotency boundary for gateway turns.
// The receipt and fact row commit in the same SQLite transaction, so retrying
// after a lost acknowledgement can reconcile without creating another turn.
func (r *FactRepo) AddTurnForSession(
	ctx context.Context,
	sessionID, turnID string,
	fact *memory.Fact,
) (*memory.SessionTurnReceipt, bool, error) {
	if fact == nil {
		return nil, false, fmt.Errorf("fact is required")
	}
	if _, err := rlmscope.RequireSessionScope(ctx, sessionID); err != nil {
		return nil, false, err
	}
	if err := rlmscope.ValidateTurnID(turnID); err != nil {
		return nil, false, err
	}
	if err := validateSessionTurnPayload(fact); err != nil {
		return nil, false, err
	}
	return r.add(ctx, fact, sessionID, turnID)
}

func validateSessionTurnPayload(fact *memory.Fact) error {
	if err := fact.Validate(); err != nil {
		return fmt.Errorf("validate session turn fact: %w", err)
	}
	if math.IsNaN(fact.Confidence) || math.IsInf(fact.Confidence, 0) {
		return fmt.Errorf("validate session turn fact: confidence must be finite")
	}
	if fact.IsGene || fact.Source == "genome" {
		return fmt.Errorf("validate session turn fact: genome metadata is not valid for conversation turns")
	}
	if fact.TTL != nil && !utf8.ValidString(fact.TTL.RefreshTrigger) {
		return fmt.Errorf("validate session turn fact: ttl refresh_trigger must be valid UTF-8")
	}
	if fact.HitCount != 0 || !fact.LastAccess.IsZero() {
		return fmt.Errorf("validate session turn fact: access counters are managed by the store")
	}
	for _, timestamp := range []struct {
		name  string
		value time.Time
	}{
		{name: "created_at", value: fact.CreatedAt},
		{name: "valid_from", value: fact.ValidFrom},
	} {
		if err := validateSessionTurnTimestamp(timestamp.name, timestamp.value); err != nil {
			return err
		}
	}
	if fact.ValidUntil != nil {
		if err := validateSessionTurnTimestamp("valid_until", *fact.ValidUntil); err != nil {
			return err
		}
	}
	return nil
}

func validateSessionTurnTimestamp(name string, value time.Time) error {
	canonical := value.UTC().Round(0)
	encoded := canonical.Format(timeFormat)
	decoded, err := time.Parse(timeFormat, encoded)
	if err != nil || !decoded.Equal(canonical) {
		return fmt.Errorf("validate session turn fact: %s cannot round-trip as RFC3339Nano", name)
	}
	return nil
}

// GetTurnForSession reads an idempotency receipt without creating or touching
// project state. A missing receipt is represented as (nil, nil, nil); a
// present but corrupt/misbound receipt is an integrity error, never absence.
func (r *FactRepo) GetTurnForSession(
	ctx context.Context,
	sessionID, turnID string,
) (*memory.SessionTurnReceipt, *memory.Fact, error) {
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return nil, nil, err
	}
	if err := rlmscope.ValidateTurnID(turnID); err != nil {
		return nil, nil, err
	}
	tx, err := r.db.db.BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return nil, nil, fmt.Errorf("begin session turn lookup: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	fact, receipt, err := loadSessionTurnReceiptTx(ctx, tx, sc, sessionID, turnID)
	if err != nil {
		return nil, nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, nil, fmt.Errorf("commit session turn lookup: %w", err)
	}
	return receipt, fact, nil
}

// ListForSession returns only facts carrying the exact session key. It is used
// by internal session pipelines that need deterministic inspection without
// weakening the public search boundary.
func (r *FactRepo) ListForSession(ctx context.Context, sessionID string, includeStale bool) ([]*memory.Fact, error) {
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	query := `SELECT ` + factColumns + ` FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND is_archived = 0`
	if !includeStale {
		query += ` AND is_stale = 0`
	}
	rows, err := r.db.QueryContext(ctx, query, sc.TenantID, sc.ProjectID, sessionID)
	if err != nil {
		return nil, fmt.Errorf("list session facts: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// Get retrieves a fact by ID.
func (r *FactRepo) Get(ctx context.Context, id string) (*memory.Fact, error) {
	sc := rlmscope.FromContext(ctx)
	row := r.db.QueryRow(`SELECT `+factColumns+`
		FROM hierarchical_facts WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')`,
		id, sc.TenantID, sc.ProjectID)
	return scanFact(row)
}

// Update updates an existing fact.
func (r *FactRepo) Update(ctx context.Context, fact *memory.Fact) error {
	if fact == nil {
		return fmt.Errorf("fact is required")
	}
	if fact.SessionID != "" {
		return fmt.Errorf("session facts require the dedicated session memory API")
	}
	sc := scopedFact(ctx, fact)
	if err := r.requireParentInExactBoundary(ctx, sc, fact); err != nil {
		return err
	}
	if err := r.ensureProjectWritable(ctx, sc); err != nil {
		return err
	}
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
		tenant_id=?, project_id=?, content=?, level=?, domain=?, module=?, code_ref=?, parent_id=?,
		embedding=?, ttl_config=?, created_at=?, valid_from=?, valid_until=?,
		is_stale=?, is_archived=?, confidence=?, source=?, session_id=?, origin=?
		WHERE id=? AND tenant_id=? AND project_id=?
		  AND (session_id IS NULL OR session_id = '')`,
		fact.TenantID, fact.ProjectID, fact.Content, int(fact.Level),
		nullStr(fact.Domain), nullStr(fact.Module), nullStr(fact.CodeRef),
		nullStr(fact.ParentID),
		embeddingBlob, ttlJSON,
		fact.CreatedAt.Format(timeFormat), fact.ValidFrom.Format(timeFormat), validUntil,
		boolToInt(fact.IsStale), boolToInt(fact.IsArchived),
		fact.Confidence, fact.Source, nullStr(fact.SessionID), string(fact.Origin),
		fact.ID, sc.TenantID, sc.ProjectID,
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
	sc := rlmscope.FromContext(ctx)
	if err := r.ensureProjectWritable(ctx, sc); err != nil {
		return err
	}
	// Remove from embeddings_index first (FK).
	_, _ = r.db.Exec(`DELETE FROM embeddings_index
		WHERE fact_id IN (
			SELECT id FROM hierarchical_facts
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND (session_id IS NULL OR session_id = '')
		)`, id, sc.TenantID, sc.ProjectID)
	// Remove from fact_hierarchy.
	_, _ = r.db.Exec(`DELETE FROM fact_hierarchy
		WHERE parent_id IN (
			SELECT id FROM hierarchical_facts
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND (session_id IS NULL OR session_id = '')
		) OR child_id IN (
			SELECT id FROM hierarchical_facts
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND (session_id IS NULL OR session_id = '')
		)`, id, sc.TenantID, sc.ProjectID, id, sc.TenantID, sc.ProjectID)
	// Remove scoped synapse links that reference the fact.
	_, _ = r.db.Exec(`DELETE FROM synapses
		WHERE tenant_id = ? AND project_id = ? AND (fact_id_a = ? OR fact_id_b = ?)
		  AND EXISTS (
			SELECT 1 FROM hierarchical_facts
			WHERE id = ? AND tenant_id = ? AND project_id = ?
			  AND (session_id IS NULL OR session_id = '')
		  )`,
		sc.TenantID, sc.ProjectID, id, id, id, sc.TenantID, sc.ProjectID)
	// Remove the fact.
	result, err := r.db.Exec(`DELETE FROM hierarchical_facts
		WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')`,
		id, sc.TenantID, sc.ProjectID)
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
	sc := rlmscope.FromContext(ctx)
	var query string
	if includeStale {
		query = `SELECT ` + factColumns + `
			FROM hierarchical_facts WHERE tenant_id = ? AND project_id = ? AND domain = ?
			  AND (session_id IS NULL OR session_id = '')`
	} else {
		query = `SELECT ` + factColumns + `
			FROM hierarchical_facts WHERE tenant_id = ? AND project_id = ? AND domain = ? AND is_stale = 0
			  AND (session_id IS NULL OR session_id = '')`
	}
	rows, err := r.db.Query(query, sc.TenantID, sc.ProjectID, domain)
	if err != nil {
		return nil, fmt.Errorf("list by domain: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// ListByLevel returns all facts at a given hierarchy level.
func (r *FactRepo) ListByLevel(ctx context.Context, level memory.HierLevel) ([]*memory.Fact, error) {
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(`SELECT `+factColumns+`
		FROM hierarchical_facts WHERE tenant_id = ? AND project_id = ? AND level = ?
		  AND (session_id IS NULL OR session_id = '')`,
		sc.TenantID, sc.ProjectID, int(level))
	if err != nil {
		return nil, fmt.Errorf("list by level: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

func validateFactPageKey(key memory.FactPageKey) error {
	if key.ID == "" || key.ID != strings.TrimSpace(key.ID) || len(key.ID) > 256 {
		return fmt.Errorf("invalid fact page key id")
	}
	if key.CreatedAt == "" || key.CreatedAt != strings.TrimSpace(key.CreatedAt) || len(key.CreatedAt) > 128 {
		return fmt.Errorf("invalid fact page key created_at")
	}
	for index := 0; index < len(key.CreatedAt); index++ {
		if key.CreatedAt[index] < 0x20 || key.CreatedAt[index] > 0x7e {
			return fmt.Errorf("invalid fact page key created_at")
		}
	}
	if !validFactPageSnapshotID(key.SnapshotID) || key.Sequence <= 0 || key.Ordinal < 0 ||
		key.ExpiresAtUnix <= 0 || key.MaxCalls <= 0 ||
		key.MaxCalls > factPageSnapshotMaxCalls(
			boundedSearchStoredSnapshotHardMaxRows,
			boundedSearchStoredSnapshotHardMaxBytes,
		) {
		return fmt.Errorf("invalid fact page key snapshot position")
	}
	return nil
}

func requireFactPageScope(ctx context.Context) (rlmscope.Scope, error) {
	sc, err := rlmscope.Require(ctx)
	if err != nil {
		return rlmscope.Scope{}, err
	}
	if sc.IsDefault() {
		return sc, nil
	}
	return rlmscope.RequireExactProject(ctx)
}

func factPageManifestTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	level memory.HierLevel,
	highWater, expectedCount int64,
) ([]factPageManifestItem, error) {
	rows, err := tx.QueryContext(ctx, `SELECT hierarchical_facts.created_at,
		hierarchical_facts.id, export_seq.seq
		FROM hierarchical_facts
		JOIN fact_export_sequence AS export_seq
		  ON export_seq.fact_id COLLATE BINARY = hierarchical_facts.id COLLATE BINARY
		WHERE export_seq.seq <= ?
		  AND hierarchical_facts.tenant_id COLLATE BINARY = ?
		  AND hierarchical_facts.project_id COLLATE BINARY = ?
		  AND hierarchical_facts.level = ?
		  AND (hierarchical_facts.session_id IS NULL OR hierarchical_facts.session_id COLLATE BINARY = '')
		ORDER BY hierarchical_facts.created_at COLLATE BINARY ASC,
			hierarchical_facts.id COLLATE BINARY ASC`,
		highWater, sc.TenantID, sc.ProjectID, int(level),
	)
	if err != nil {
		return nil, fmt.Errorf("query exact fact page manifest: %w", err)
	}
	defer rows.Close()
	manifest := make([]factPageManifestItem, 0, expectedCount)
	for rows.Next() {
		var item factPageManifestItem
		if err := rows.Scan(&item.createdAt, &item.id, &item.sequence); err != nil {
			return nil, fmt.Errorf("scan exact fact page manifest: %w", err)
		}
		probe := memory.FactPageKey{
			CreatedAt: item.createdAt,
			ID:        item.id,
		}
		if probe.ID == "" || probe.ID != strings.TrimSpace(probe.ID) || len(probe.ID) > 256 ||
			probe.CreatedAt == "" || probe.CreatedAt != strings.TrimSpace(probe.CreatedAt) ||
			len(probe.CreatedAt) > 128 || item.sequence <= 0 || item.sequence > highWater {
			return nil, memory.ErrFactPageChanged
		}
		for index := 0; index < len(probe.CreatedAt); index++ {
			if probe.CreatedAt[index] < 0x20 || probe.CreatedAt[index] > 0x7e {
				return nil, memory.ErrFactPageChanged
			}
		}
		manifest = append(manifest, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate exact fact page manifest: %w", err)
	}
	if int64(len(manifest)) != expectedCount {
		return nil, fmt.Errorf("%w: fact page manifest count changed", memory.ErrFactPageChanged)
	}
	return manifest, nil
}

// ListByLevelPage performs one whole-scope metadata preflight on the initial
// call, then walks a bounded process-local content-free manifest. Every future
// row is checked by exact export sequence before its payload is materialized;
// previously delivered rows are never rescanned.
func (r *FactRepo) ListByLevelPage(
	ctx context.Context,
	level memory.HierLevel,
	maxFactBytes int,
	snapshot int64,
	expectedCount int64,
	after *memory.FactPageKey,
) (*memory.FactPage, error) {
	sc, err := requireFactPageScope(ctx)
	if err != nil {
		return nil, err
	}
	if !level.IsValid() {
		return nil, fmt.Errorf("invalid level %d", level)
	}
	maxStoredRowBytes, validMaxFactBytes := memory.FactPageMaxStoredVariableBytes(maxFactBytes)
	if !validMaxFactBytes {
		return nil, fmt.Errorf("invalid fact page max_fact_bytes")
	}
	if snapshot < 0 || expectedCount < 0 ||
		(snapshot == 0 && (expectedCount != 0 || after != nil)) ||
		(snapshot > 0 && (expectedCount == 0 || after == nil)) {
		return nil, fmt.Errorf("invalid fact page snapshot")
	}

	if snapshot == 0 {
		tx, beginErr := r.db.SqlDB().BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
		if beginErr != nil {
			return nil, fmt.Errorf("begin exact fact page manifest: %w", beginErr)
		}
		defer func() { _ = tx.Rollback() }()
		measurement, preflightErr := factPageCurrentScopePreflightTx(
			ctx, tx, sc, level, maxStoredRowBytes,
		)
		if preflightErr != nil {
			return nil, preflightErr
		}
		if measurement.rowCount == 0 {
			if err := tx.Commit(); err != nil {
				return nil, fmt.Errorf("commit empty fact page snapshot: %w", err)
			}
			return &memory.FactPage{}, nil
		}
		if err := tx.QueryRowContext(ctx, `SELECT COALESCE(MAX(seq), 0)
			FROM fact_export_sequence`).Scan(&snapshot); err != nil {
			return nil, fmt.Errorf("capture fact page snapshot high-water: %w", err)
		}
		if snapshot <= 0 {
			return nil, fmt.Errorf("%w: fact page snapshot has no export sequence", memory.ErrFactPageChanged)
		}
		manifest, manifestErr := factPageManifestTx(
			ctx, tx, sc, level, snapshot, measurement.rowCount,
		)
		if manifestErr != nil {
			return nil, manifestErr
		}
		if err := tx.Commit(); err != nil {
			return nil, fmt.Errorf("commit exact fact page manifest: %w", err)
		}
		cached, cacheErr := r.factPages.register(
			sc, level, maxFactBytes, snapshot, measurement.rowCount,
			measurement.totalStoredBytes, manifest,
		)
		if cacheErr != nil {
			return nil, cacheErr
		}
		expectedCount = measurement.rowCount
		key, keyErr := cached.key(0)
		if keyErr != nil {
			return nil, keyErr
		}
		page, pageErr := r.factPageAtKey(ctx, sc, level, maxStoredRowBytes,
			maxFactBytes, snapshot, expectedCount, key)
		if pageErr != nil {
			_ = r.factPages.release(sc, level, key)
			return nil, pageErr
		}
		return page, nil
	}

	if err := validateFactPageKey(*after); err != nil {
		return nil, err
	}
	cached, err := r.factPages.lock(
		sc, level, maxFactBytes, snapshot, expectedCount, *after,
	)
	if err != nil {
		return nil, err
	}
	defer cached.mu.Unlock()
	nextOrdinal := after.Ordinal + 1
	if nextOrdinal >= cached.expectedCount {
		return &memory.FactPage{Snapshot: snapshot, ExpectedCount: expectedCount}, nil
	}
	key, err := cached.key(nextOrdinal)
	if err != nil {
		return nil, err
	}
	return r.factPageAtKeyLocked(
		ctx, cached, sc, level, maxStoredRowBytes, maxFactBytes, key,
	)
}

func getByLevelPageKeyTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	level memory.HierLevel,
	key memory.FactPageKey,
) (*memory.Fact, error) {
	fact, _, err := scanFactDetailed(tx.QueryRowContext(ctx, `
		SELECT `+factColumns+`
		FROM fact_export_sequence AS export_seq
		JOIN hierarchical_facts
		  ON hierarchical_facts.id COLLATE BINARY = export_seq.fact_id COLLATE BINARY
		WHERE export_seq.seq = ?
		  AND export_seq.fact_id COLLATE BINARY = ?
		  AND hierarchical_facts.tenant_id COLLATE BINARY = ?
		  AND hierarchical_facts.project_id COLLATE BINARY = ?
		  AND hierarchical_facts.level = ?
		  AND hierarchical_facts.created_at COLLATE BINARY = ?
		  AND hierarchical_facts.id COLLATE BINARY = ?
		  AND (hierarchical_facts.session_id IS NULL OR hierarchical_facts.session_id COLLATE BINARY = '')`,
		key.Sequence, key.ID, sc.TenantID, sc.ProjectID, int(level), key.CreatedAt, key.ID,
	))
	if errors.Is(err, sql.ErrNoRows) {
		return nil, fmt.Errorf("%w: fact page record not found", memory.ErrFactPageChanged)
	}
	if err != nil {
		return nil, fmt.Errorf("reload exact fact page record: %w", err)
	}
	return fact, nil
}

func (r *FactRepo) factPageAtKey(
	ctx context.Context,
	sc rlmscope.Scope,
	level memory.HierLevel,
	maxStoredRowBytes int64,
	maxFactBytes int,
	snapshot, expectedCount int64,
	key memory.FactPageKey,
) (*memory.FactPage, error) {
	cached, err := r.factPages.lock(
		sc, level, maxFactBytes, snapshot, expectedCount, key,
	)
	if err != nil {
		return nil, err
	}
	defer cached.mu.Unlock()
	return r.factPageAtKeyLocked(
		ctx, cached, sc, level, maxStoredRowBytes, maxFactBytes, key,
	)
}

func (r *FactRepo) factPageAtKeyLocked(
	ctx context.Context,
	cached *factPageSnapshot,
	sc rlmscope.Scope,
	level memory.HierLevel,
	maxStoredRowBytes int64,
	maxFactBytes int,
	key memory.FactPageKey,
) (*memory.FactPage, error) {
	tx, err := r.db.SqlDB().BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return nil, fmt.Errorf("begin exact fact page row: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := factPageExactRowPreflightTx(
		ctx, tx, sc, level, maxStoredRowBytes, key,
	); err != nil {
		return nil, err
	}
	fact, err := getByLevelPageKeyTx(ctx, tx, sc, level, key)
	if err != nil {
		return nil, err
	}
	if fact.ID != key.ID || fact.TenantID != sc.TenantID || fact.ProjectID != sc.ProjectID ||
		fact.Level != level || fact.SessionID != "" {
		return nil, memory.ErrFactPageChanged
	}
	serialized, err := json.Marshal(fact)
	if err != nil {
		return nil, fmt.Errorf("encode exact fact page record: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit exact fact page row: %w", err)
	}
	page := &memory.FactPage{
		Snapshot:      cached.highWater,
		ExpectedCount: cached.expectedCount,
		Key:           key,
		Fact:          fact,
		HasMore:       key.Ordinal+1 < cached.expectedCount,
	}
	if len(serialized) > maxFactBytes {
		page.Record = &memory.FactPageRecord{
			Key: key, FactID: key.ID, TotalBytes: len(serialized),
		}
		return page, nil
	}
	payload := cacheFactPagePayloadLocked(cached, key, serialized)
	page.Record, err = factPageFrameLocked(payload, 0)
	if err != nil {
		return nil, err
	}
	return page, nil
}

// GetByLevelPageKey reloads an in-progress fact fragment without broadening
// the snapshot, level, project or non-session boundary encoded in its cursor.
func (r *FactRepo) GetByLevelPageKey(
	ctx context.Context,
	level memory.HierLevel,
	maxFactBytes int,
	snapshot int64,
	expectedCount int64,
	key memory.FactPageKey,
	offset int,
) (*memory.FactPageRecord, error) {
	sc, err := requireFactPageScope(ctx)
	if err != nil {
		return nil, err
	}
	if !level.IsValid() {
		return nil, fmt.Errorf("invalid level %d", level)
	}
	maxStoredRowBytes, validMaxFactBytes := memory.FactPageMaxStoredVariableBytes(maxFactBytes)
	if !validMaxFactBytes {
		return nil, fmt.Errorf("invalid fact page max_fact_bytes")
	}
	if snapshot <= 0 || expectedCount <= 0 || offset < 0 {
		return nil, fmt.Errorf("invalid fact page snapshot")
	}
	if err := validateFactPageKey(key); err != nil {
		return nil, err
	}
	cached, err := r.factPages.lock(
		sc, level, maxFactBytes, snapshot, expectedCount, key,
	)
	if err != nil {
		return nil, err
	}
	defer cached.mu.Unlock()
	if cached.payload == nil || cached.payload.ordinal != key.Ordinal || cached.payload.key != key {
		return nil, memory.ErrFactPageChanged
	}
	tx, err := r.db.SqlDB().BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return nil, fmt.Errorf("begin exact fact page reload: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := factPageExactRowPreflightTx(ctx, tx, sc, level, maxStoredRowBytes, key); err != nil {
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit exact fact page reload: %w", err)
	}
	return factPageFrameLocked(cached.payload, offset)
}

// ReleaseFactPage removes a completed immutable manifest. Missing/expired
// snapshots stay typed so callers never silently restart a walk.
func (r *FactRepo) ReleaseFactPage(
	ctx context.Context,
	level memory.HierLevel,
	key memory.FactPageKey,
) error {
	sc, err := requireFactPageScope(ctx)
	if err != nil {
		return err
	}
	if !level.IsValid() {
		return fmt.Errorf("invalid level %d", level)
	}
	if err := validateFactPageKey(key); err != nil {
		return err
	}
	return r.factPages.release(sc, level, key)
}

// ListDomains returns distinct domain names.
func (r *FactRepo) ListDomains(ctx context.Context) ([]string, error) {
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(`SELECT DISTINCT domain FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND domain IS NOT NULL AND domain != ''
		  AND (session_id IS NULL OR session_id = '')`,
		sc.TenantID, sc.ProjectID)
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
	sc := rlmscope.FromContext(ctx)
	var query string
	if includeArchived {
		query = `SELECT ` + factColumns + `
			FROM hierarchical_facts WHERE tenant_id = ? AND project_id = ? AND is_stale = 1
			  AND (session_id IS NULL OR session_id = '')`
	} else {
		query = `SELECT ` + factColumns + `
			FROM hierarchical_facts WHERE tenant_id = ? AND project_id = ? AND is_stale = 1 AND is_archived = 0
			  AND (session_id IS NULL OR session_id = '')`
	}
	rows, err := r.db.Query(query, sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("get stale: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// Search ranks facts by term overlap with the query.
//
// It used to be `content LIKE '%' || query || '%'` with the whole query as one blob, and that shape
// was measured against live data on 2026-08-20. Six queries over six stored facts:
//
//	"bash читает файл по смещению"   verbatim phrase        found
//	"портит хвост"                   verbatim phrase        found
//	"прогон"                         single word            found, 3 facts
//	"править прогон"                 both words in one fact NOTHING
//	"скрипт выполняется править"     all three in one fact  NOTHING
//	"Портит Хвост"                   same phrase, capitals  NOTHING
//
// Two defects, both in one line. A multi-word query could only match a verbatim contiguous phrase,
// so any natural question missed by construction; and SQLite's LIKE folds case for ASCII only, so a
// capitalised Cyrillic word never matched its stored lowercase form. The mode is named `keyword` and
// was doing neither keywords nor case-insensitivity.
//
// Ranked in Go rather than SQL because case folding for Cyrillic is not available to SQLite's LIKE or
// lower() at all, and because the ranking wants term counts. The scan is linear over the scope, which
// is the same trade `SearchByVector` below already documents and accepts for this corpus size.
//
// Three tiers, so a near-miss degrades instead of falling off a cliff:
//
//	the whole phrase appears   → strongest, preserves the old behaviour as the best case
//	every term appears         → the usual meaning of a keyword search
//	some terms appear          → ranked by how many, so a question with one unknown word still lands
func (r *FactRepo) Search(ctx context.Context, query string, limit int) ([]*memory.Fact, error) {
	return r.search(ctx, "", query, limit)
}

// SearchForSession performs keyword recall inside one exact conversation
// boundary. session_id = ? (rather than LIKE, COALESCE, or an in-memory filter)
// is load-bearing: legacy NULL/empty rows and sibling sessions never enter the
// candidate set.
func (r *FactRepo) SearchForSession(ctx context.Context, sessionID, query string, limit int) ([]*memory.Fact, error) {
	if _, err := rlmscope.RequireSessionScope(ctx, sessionID); err != nil {
		return nil, err
	}
	return r.search(ctx, sessionID, query, limit)
}

func (r *FactRepo) search(ctx context.Context, sessionID, query string, limit int) ([]*memory.Fact, error) {
	if limit <= 0 {
		limit = 50
	}
	if strings.TrimSpace(query) == "" {
		return nil, nil
	}

	sc := rlmscope.FromContext(ctx)
	querySQL := `SELECT ` + factColumns + `
		FROM hierarchical_facts WHERE tenant_id = ? AND project_id = ?`
	queryArgs := []any{sc.TenantID, sc.ProjectID}
	if sessionID != "" {
		querySQL += ` AND session_id = ? AND is_archived = 0 AND is_stale = 0`
		queryArgs = append(queryArgs, sessionID)
	} else {
		querySQL += ` AND (session_id IS NULL OR session_id = '')`
	}
	rows, err := r.db.QueryContext(ctx, querySQL, queryArgs...)
	if err != nil {
		return nil, fmt.Errorf("search: %w", err)
	}
	defer rows.Close()
	candidates, err := scanFacts(rows)
	if err != nil {
		return nil, err
	}

	return rankKeywordMatches(candidates, query, limit, sessionID != ""), nil
}

// searchTerms splits a query into lowercased terms worth matching.
//
// Single characters and two-letter function words are dropped: with the OR tier below, a term like
// «и» or «в» matches nearly every fact and would rank noise above the answer. Three characters is
// the floor the pack loader already uses for its own literals.
func searchTerms(query string) []string {
	fields := strings.FieldsFunc(strings.ToLower(query), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
	seen := make(map[string]struct{}, len(fields))
	terms := make([]string, 0, len(fields))
	for _, f := range fields {
		if len([]rune(f)) < 3 {
			continue
		}
		if _, dup := seen[f]; dup {
			continue
		}
		seen[f] = struct{}{}
		terms = append(terms, f)
	}
	return terms
}

// SearchByVector ranks facts by cosine similarity to queryVec.
// Skips facts without an embedding or with mismatched dimensionality.
// Archived facts are excluded. Linear scan over all candidates — fine
// for the current corpus size; HNSW/FAISS is a later concern.
func (r *FactRepo) SearchByVector(ctx context.Context, queryVec []float64, limit int) ([]*memory.Fact, error) {
	return r.searchByVector(ctx, "", queryVec, limit)
}

// SearchByVectorForSession performs semantic recall inside one exact
// tenant/project/session boundary. It never admits legacy facts whose
// session_id is NULL or empty.
func (r *FactRepo) SearchByVectorForSession(ctx context.Context, sessionID string, queryVec []float64, limit int) ([]*memory.Fact, error) {
	if _, err := rlmscope.RequireSessionScope(ctx, sessionID); err != nil {
		return nil, err
	}
	return r.searchByVector(ctx, sessionID, queryVec, limit)
}

func (r *FactRepo) searchByVector(ctx context.Context, sessionID string, queryVec []float64, limit int) ([]*memory.Fact, error) {
	if len(queryVec) == 0 {
		return nil, nil
	}
	if limit <= 0 {
		limit = 50
	}
	sc := rlmscope.FromContext(ctx)
	querySQL := `SELECT ` + factColumns + `
		FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND embedding IS NOT NULL AND is_archived = 0`
	queryArgs := []any{sc.TenantID, sc.ProjectID}
	if sessionID != "" {
		querySQL += ` AND session_id = ? AND is_stale = 0`
		queryArgs = append(queryArgs, sessionID)
	} else {
		querySQL += ` AND (session_id IS NULL OR session_id = '')`
	}
	rows, err := r.db.QueryContext(ctx, querySQL, queryArgs...)
	if err != nil {
		return nil, fmt.Errorf("search by vector: %w", err)
	}
	defer rows.Close()
	candidates, err := scanFacts(rows)
	if err != nil {
		return nil, err
	}

	type scored struct {
		f   *memory.Fact
		sim float64
	}
	ranked := make([]scored, 0, len(candidates))
	for _, f := range candidates {
		if len(f.Embedding) != len(queryVec) {
			continue
		}
		sim := vectorstore.CosineSimilarity(queryVec, f.Embedding)
		ranked = append(ranked, scored{f, sim})
	}
	if sessionID != "" {
		sort.Slice(ranked, func(i, j int) bool {
			if ranked[i].sim != ranked[j].sim {
				return ranked[i].sim > ranked[j].sim
			}
			if !ranked[i].f.CreatedAt.Equal(ranked[j].f.CreatedAt) {
				return ranked[i].f.CreatedAt.After(ranked[j].f.CreatedAt)
			}
			return ranked[i].f.ID < ranked[j].f.ID
		})
	} else {
		// Preserve legacy vector-search ordering; exact session recall alone has the conversation
		// recency contract above.
		sort.Slice(ranked, func(i, j int) bool { return ranked[i].sim > ranked[j].sim })
	}

	if limit > len(ranked) {
		limit = len(ranked)
	}
	out := make([]*memory.Fact, limit)
	for i := 0; i < limit; i++ {
		out[i] = ranked[i].f
	}
	return out, nil
}

// GetExpired returns facts whose TTL has expired.
func (r *FactRepo) GetExpired(ctx context.Context) ([]*memory.Fact, error) {
	sc := rlmscope.FromContext(ctx)
	// Get all facts with TTL config, check expiry in Go.
	rows, err := r.db.Query(`SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND ttl_config IS NOT NULL AND ttl_config != ''
		  AND (session_id IS NULL OR session_id = '')`,
		sc.TenantID, sc.ProjectID)
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
	sc := rlmscope.FromContext(ctx)
	if err := r.ensureProjectWritable(ctx, sc); err != nil {
		return err
	}
	now := time.Now().Format(timeFormat)
	result, err := r.db.Exec(`UPDATE hierarchical_facts SET created_at = ?
		WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')`,
		now, id, sc.TenantID, sc.ProjectID)
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
	sc := rlmscope.FromContext(ctx)
	stats := &memory.FactStoreStats{
		ByLevel:  make(map[memory.HierLevel]int),
		ByDomain: make(map[string]int),
		ByOrigin: make(map[memory.Origin]int),
	}

	// Total legacy facts — every non-session row, archived included. Session
	// memory has a separate exact API and must not contaminate project-wide stats.
	row := r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')`,
		sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.TotalFacts); err != nil {
		return nil, err
	}

	// Archived, and what is left. Reported separately rather than folded into the total: after
	// deduplication the difference between the two IS the result, and a single number hides it.
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND is_archived = 1
		  AND (session_id IS NULL OR session_id = '')`, sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.ArchivedCount); err != nil {
		return nil, err
	}
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND is_archived = 0 AND is_stale = 0
		  AND (session_id IS NULL OR session_id = '')`,
		sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.LiveFacts); err != nil {
		return nil, err
	}

	// By origin, over live facts only. Counting archived rows here would report trust the store no
	// longer acts on.
	originRows, err := r.db.Query(`SELECT origin, COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND is_archived = 0 AND is_stale = 0
		  AND (session_id IS NULL OR session_id = '')
		GROUP BY origin`, sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, err
	}
	for originRows.Next() {
		var (
			origin sql.NullString
			count  int
		)
		if err := originRows.Scan(&origin, &count); err != nil {
			originRows.Close()
			return nil, err
		}
		// Through normaliseOrigin so an unrecognised value is counted as unspecified rather than
		// appearing as its own category — the same fail-safe the read path applies.
		stats.ByOrigin[normaliseOrigin(origin)] += count
	}
	if err := originRows.Err(); err != nil {
		originRows.Close()
		return nil, err
	}
	originRows.Close()

	// Stale count.
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND is_stale = 1
		  AND (session_id IS NULL OR session_id = '')`, sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.StaleCount); err != nil {
		return nil, err
	}

	// With embeddings.
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND embedding IS NOT NULL
		  AND (session_id IS NULL OR session_id = '')`, sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.WithEmbeddings); err != nil {
		return nil, err
	}

	// By level.
	rows, err := r.db.Query(`SELECT level, COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')
		GROUP BY level`, sc.TenantID, sc.ProjectID)
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
	rows2, err := r.db.Query(`SELECT domain, COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND domain IS NOT NULL AND domain != ''
		  AND (session_id IS NULL OR session_id = '')
		GROUP BY domain`, sc.TenantID, sc.ProjectID)
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

	// Gene count (Genome Layer).
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND source = 'genome'
		  AND (session_id IS NULL OR session_id = '')`, sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.GeneCount); err != nil {
		return nil, err
	}

	// v3.3: Cold count (hit_count=0, created >30 days ago, not gene, not archived).
	thirtyDaysAgo := time.Now().AddDate(0, 0, -30).Format(timeFormat)
	row = r.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND hit_count = 0 AND created_at < ?
		  AND source != 'genome' AND is_archived = 0
		  AND (session_id IS NULL OR session_id = '')`,
		sc.TenantID, sc.ProjectID, thirtyDaysAgo)
	if err := row.Scan(&stats.ColdCount); err != nil {
		// Ignore if column doesn't exist yet.
		stats.ColdCount = 0
	}

	return stats, rows2.Err()
}

// --- helpers ---

type factRowScanner interface {
	Scan(dest ...any) error
	Err() error
}

func scanFact(row factRowScanner) (*memory.Fact, error) {
	fact, _, err := scanFactDetailed(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, memory.ErrFactNotFound
	}
	return fact, err
}

// scanFactDetailed distinguishes malformed stored payloads from operational
// query failures. Receipt reconciliation treats missing/malformed committed
// data as integrity loss, but must preserve cancellation, I/O, and driver
// causes so callers do not misreport infrastructure failure as corruption.
func scanFactDetailed(row factRowScanner) (*memory.Fact, bool, error) {
	if err := row.Err(); err != nil {
		return nil, false, fmt.Errorf("query fact: %w", err)
	}
	var f memory.Fact
	var levelInt int
	var tenantID, projectID, domain, module, codeRef, parentID, sessionID sql.NullString
	var embeddingBlob []byte
	var ttlJSON sql.NullString
	var createdAt, validFrom string
	var validUntil sql.NullString
	var isStale, isArchived int
	// NullString rather than string: a database whose column predates the NOT NULL constraint
	// can still hold NULL, and an empty origin would land outside the closed enum.
	var originStr sql.NullString

	err := row.Scan(&f.ID, &tenantID, &projectID, &f.Content, &levelInt,
		&domain, &module, &codeRef, &parentID,
		&embeddingBlob, &ttlJSON,
		&createdAt, &validFrom, &validUntil,
		&isStale, &isArchived, &f.Confidence, &f.Source, &sessionID, &originStr,
		// Must match `factColumns` exactly, and there are two scanners over one column list — this
		// singular one is the easy half to forget, and forgetting it makes `Get` fail at runtime with
		// a column-count error rather than at build time.
		&f.HitCount,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, false, fmt.Errorf("scan fact: %w", err)
		}
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return nil, false, fmt.Errorf("scan fact: %w", err)
		}
		if queryErr := row.Err(); queryErr != nil {
			return nil, false, fmt.Errorf("query fact: %w", queryErr)
		}
		return nil, true, fmt.Errorf("scan fact: %w", err)
	}

	storedOriginInvalid := !originStr.Valid || !memory.Origin(originStr.String).IsValid()
	f.Origin = normaliseOrigin(originStr)
	f.Level = memory.HierLevel(levelInt)
	f.TenantID = tenantID.String
	f.ProjectID = projectID.String
	f.Domain = domain.String
	f.Module = module.String
	f.CodeRef = codeRef.String
	f.ParentID = parentID.String
	f.SessionID = sessionID.String
	f.IsStale = isStale != 0
	f.IsArchived = isArchived != 0
	f.IsGene = f.Source == "genome" // Genome Layer: auto-detect from source

	f.CreatedAt, err = time.Parse(timeFormat, createdAt)
	if err != nil {
		return nil, true, fmt.Errorf("decode created_at: %w", err)
	}
	f.ValidFrom, err = time.Parse(timeFormat, validFrom)
	if err != nil {
		return nil, true, fmt.Errorf("decode valid_from: %w", err)
	}
	f.UpdatedAt = f.CreatedAt // We don't have a separate updated_at column in the DB schema.

	if validUntil.Valid {
		t, err := time.Parse(timeFormat, validUntil.String)
		if err != nil {
			return nil, true, fmt.Errorf("decode valid_until: %w", err)
		}
		f.ValidUntil = &t
	}

	if len(embeddingBlob) > 0 {
		if err := json.Unmarshal(embeddingBlob, &f.Embedding); err != nil {
			return nil, true, fmt.Errorf("decode embedding: %w", err)
		}
	}

	if ttlJSON.Valid && ttlJSON.String != "" {
		f.TTL = &memory.TTLConfig{}
		if err := json.Unmarshal([]byte(ttlJSON.String), f.TTL); err != nil {
			return nil, true, fmt.Errorf("decode ttl_config: %w", err)
		}
	}

	return &f, storedOriginInvalid, nil
}

func sessionTurnFactLoadError(storedDataInvalid bool, err error) error {
	if storedDataInvalid || errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("%w: resolve receipt fact: %v", memory.ErrSessionTurnIntegrity, err)
	}
	return fmt.Errorf("resolve receipt fact: %w", err)
}

func scanFacts(rows *sql.Rows) ([]*memory.Fact, error) {
	var facts []*memory.Fact
	for rows.Next() {
		var f memory.Fact
		var levelInt int
		var tenantID, projectID, domain, module, codeRef, parentID, sessionID sql.NullString
		var embeddingBlob []byte
		var ttlJSON sql.NullString
		var createdAt, validFrom string
		var validUntil sql.NullString
		var isStale, isArchived int
		var originStr sql.NullString

		err := rows.Scan(&f.ID, &tenantID, &projectID, &f.Content, &levelInt,
			&domain, &module, &codeRef, &parentID,
			&embeddingBlob, &ttlJSON,
			&createdAt, &validFrom, &validUntil,
			&isStale, &isArchived, &f.Confidence, &f.Source, &sessionID, &originStr,
			// `hit_count` was written by TouchFact and read by nothing but the GC's WHERE clause, so
			// `Fact.HitCount` — declared as «v3.3: context access counter» — was zero on every fact
			// ever loaded. Ranking's frequency term reads a per-process map instead, which starts
			// empty, so a fact used ninety times across earlier sessions scored exactly like one never
			// used. Reading the column is half the repair; the other half is in the context engine.
			&f.HitCount,
		)
		if err != nil {
			return nil, fmt.Errorf("scan fact row: %w", err)
		}

		f.Origin = normaliseOrigin(originStr)
		f.Level = memory.HierLevel(levelInt)
		f.TenantID = tenantID.String
		f.ProjectID = projectID.String
		f.Domain = domain.String
		f.Module = module.String
		f.CodeRef = codeRef.String
		f.ParentID = parentID.String
		f.SessionID = sessionID.String
		f.IsStale = isStale != 0
		f.IsArchived = isArchived != 0
		f.IsGene = f.Source == "genome" // Genome Layer: auto-detect from source
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
var _ memory.SessionFactStore = (*FactRepo)(nil)
var _ memory.ProjectExactFactStore = (*FactRepo)(nil)

// ListGenes returns all genome facts (immutable survival invariants).
func (r *FactRepo) ListGenes(ctx context.Context) ([]*memory.Fact, error) {
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(`SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ? AND source = 'genome'
		  AND (session_id IS NULL OR session_id = '')
		ORDER BY created_at ASC`, sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("list genes: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// --- v3.3 Context GC ---

// TouchFact increments hit_count and updates last_accessed_at.
func (r *FactRepo) TouchFact(ctx context.Context, id string) error {
	sc := rlmscope.FromContext(ctx)
	if err := r.ensureProjectWritable(ctx, sc); err != nil {
		return err
	}
	now := time.Now().Format(timeFormat)
	result, err := r.db.Exec(`UPDATE hierarchical_facts
		SET hit_count = COALESCE(hit_count, 0) + 1, last_accessed_at = ?
		WHERE id = ? AND tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')`,
		now, id, sc.TenantID, sc.ProjectID)
	if err != nil {
		return fmt.Errorf("touch fact: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("fact %s not found", id)
	}
	return nil
}

// GetColdFacts returns facts with hit_count=0, created >30 days ago.
// Genes (source='genome') and archived facts are excluded.
func (r *FactRepo) GetColdFacts(ctx context.Context, limit int) ([]*memory.Fact, error) {
	if limit <= 0 {
		limit = 50
	}
	sc := rlmscope.FromContext(ctx)
	thirtyDaysAgo := time.Now().AddDate(0, 0, -30).Format(timeFormat)
	rows, err := r.db.Query(`SELECT `+factColumns+`
		FROM hierarchical_facts
		WHERE tenant_id = ? AND project_id = ?
		  AND (session_id IS NULL OR session_id = '')
		  AND COALESCE(hit_count, 0) = 0
		  AND created_at < ?
		  AND source != 'genome'
		  AND is_archived = 0
		ORDER BY created_at ASC
		LIMIT ?`, sc.TenantID, sc.ProjectID, thirtyDaysAgo, limit)
	if err != nil {
		return nil, fmt.Errorf("get cold facts: %w", err)
	}
	defer rows.Close()
	return scanFacts(rows)
}

// CompressFacts archives originals and creates a summary fact.
// Genes (source='genome') are silently skipped.
func (r *FactRepo) CompressFacts(ctx context.Context, ids []string, summary string) (string, error) {
	if len(ids) == 0 {
		return "", fmt.Errorf("no fact IDs provided")
	}
	if summary == "" {
		return "", fmt.Errorf("summary text is required")
	}
	sc := rlmscope.FromContext(ctx)
	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return "", fmt.Errorf("begin compression: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	now, err := acquireProjectWriteTx(ctx, tx, sc)
	if err != nil {
		return "", err
	}
	if err := requireProjectWritableAndTouchTx(ctx, tx, sc, now); err != nil {
		return "", err
	}
	// Read only authority/scoping metadata once per distinct input. The same
	// transaction owns these reads, the archives, deduplication and summary write.
	var domain string
	var level memory.HierLevel
	var inputOrigins []memory.Origin
	selected := make([]string, 0, len(ids))
	seen := make(map[string]bool, len(ids))
	for _, id := range ids {
		if seen[id] {
			continue
		}
		seen[id] = true
		var factLevel int
		var factDomain, origin, source sql.NullString
		err := tx.QueryRowContext(ctx, `SELECT level,domain,origin,source FROM hierarchical_facts
   WHERE id=? AND tenant_id=? AND project_id=? AND (session_id IS NULL OR session_id='')`, id, sc.TenantID, sc.ProjectID).Scan(&factLevel, &factDomain, &origin, &source)
		if errors.Is(err, sql.ErrNoRows) {
			continue
		}
		if err != nil {
			return "", fmt.Errorf("read compression input: %w", err)
		}
		if source.String == "genome" {
			continue
		}
		if len(selected) == 0 {
			domain = factDomain.String
			level = memory.HierLevel(factLevel)
		}
		inputOrigins = append(inputOrigins, normaliseOrigin(origin))
		selected = append(selected, id)
	}
	if len(selected) == 0 {
		return "", fmt.Errorf("no facts were archived (all genes or not found)")
	}
	summaryFact := memory.NewFact(summary, level, domain, "")
	summaryFact.Source = "consolidation"
	summaryFact.Origin = memory.LeastTrusted(append(inputOrigins, memory.OriginDerived)...)
	scopedFact(ctx, summaryFact)
	if err := summaryFact.Validate(); err != nil {
		return "", fmt.Errorf("validate summary fact: %w", err)
	}
	for _, id := range selected {
		result, err := tx.ExecContext(ctx, `UPDATE hierarchical_facts SET is_archived=1
   WHERE id=? AND tenant_id=? AND project_id=? AND (session_id IS NULL OR session_id='') AND source!='genome'`, id, sc.TenantID, sc.ProjectID)
		if err != nil {
			return "", fmt.Errorf("archive compression input: %w", err)
		}
		affected, err := result.RowsAffected()
		if err != nil || affected != 1 {
			return "", fmt.Errorf("compression input boundary changed")
		}
	}
	folded, err := r.foldIntoDuplicateTx(ctx, tx, sc, summaryFact)
	if err != nil {
		return "", fmt.Errorf("fold summary fact: %w", err)
	}
	if !folded {
		_, err := tx.ExecContext(ctx, `INSERT INTO hierarchical_facts
   (id,tenant_id,project_id,content,level,domain,module,created_at,valid_from,is_stale,is_archived,confidence,source,origin)
   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`, summaryFact.ID, sc.TenantID, sc.ProjectID, summaryFact.Content, int(summaryFact.Level),
			nullStr(summaryFact.Domain), nullStr(summaryFact.Module), summaryFact.CreatedAt.Format(timeFormat), summaryFact.ValidFrom.Format(timeFormat),
			0, 0, summaryFact.Confidence, summaryFact.Source, string(summaryFact.Origin))
		if err != nil {
			return "", fmt.Errorf("create summary fact: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return "", fmt.Errorf("commit compression: %w", err)
	}
	return summaryFact.ID, nil
}
