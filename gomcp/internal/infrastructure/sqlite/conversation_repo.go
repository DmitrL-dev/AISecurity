package sqlite

import (
	"context"
	"fmt"
	"strings"
	"time"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// ConversationEntry is a single message captured from a Claude Code (or any
// other) conversation transcript. It is the L4-transient layer of the Crystal
// memory hierarchy: raw, ordered, lossless, but expected to decay or be
// distilled into denser L3/L2 facts over time.
type ConversationEntry struct {
	ID        int64     `json:"id"`
	TenantID  string    `json:"tenant_id,omitempty"`
	ProjectID string    `json:"project_id,omitempty"`
	SessionID string    `json:"session_id"`
	Role      string    `json:"role"` // user | assistant | system
	Content   string    `json:"content"`
	MsgIndex  int       `json:"msg_index"` // monotonic position inside the session
	Timestamp time.Time `json:"timestamp"`
	Metadata  string    `json:"metadata,omitempty"` // optional JSON blob
	Distilled bool      `json:"distilled"`
}

// ConversationLogRepo persists raw conversation transcripts for later
// distillation into hierarchical_facts. Designed to be append-only —
// no UPDATE except the distilled flag, no DELETE except via Prune.
type ConversationLogRepo struct {
	db *DB
}

// NewConversationLogRepo creates the conversation_log table if it does not
// already exist and returns a repo wrapper.
func NewConversationLogRepo(db *DB) (*ConversationLogRepo, error) {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS conversation_log (
			id          INTEGER PRIMARY KEY AUTOINCREMENT,
			tenant_id   TEXT    NOT NULL DEFAULT 'local',
			project_id  TEXT    NOT NULL DEFAULT 'default',
			session_id  TEXT    NOT NULL,
			role        TEXT    NOT NULL,
			content     TEXT    NOT NULL,
			msg_index   INTEGER NOT NULL,
			timestamp   TEXT    NOT NULL,
			metadata    TEXT,
			distilled   INTEGER DEFAULT 0,
			UNIQUE(tenant_id, project_id, session_id, msg_index)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_conv_scope_session ON conversation_log(tenant_id, project_id, session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_conv_session ON conversation_log(session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_conv_distilled ON conversation_log(distilled)`,
		`CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversation_log(timestamp)`,
	}
	for _, s := range stmts {
		if _, err := db.Exec(s); err != nil {
			return nil, fmt.Errorf("create conversation_log: %w", err)
		}
	}
	_, _ = db.Exec(`ALTER TABLE conversation_log ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`)
	_, _ = db.Exec(`ALTER TABLE conversation_log ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`)
	repo := &ConversationLogRepo{db: db}
	if err := repo.migrateScopeKey(); err != nil {
		return nil, err
	}
	return repo, nil
}

func (r *ConversationLogRepo) migrateScopeKey() error {
	var tableSQL string
	if err := r.db.QueryRow(`SELECT sql FROM sqlite_master WHERE type='table' AND name='conversation_log'`).Scan(&tableSQL); err != nil {
		return nil
	}
	if strings.Contains(tableSQL, "tenant_id, project_id, session_id, msg_index") {
		return nil
	}
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS conversation_log_scoped (
			id          INTEGER PRIMARY KEY AUTOINCREMENT,
			tenant_id   TEXT    NOT NULL DEFAULT 'local',
			project_id  TEXT    NOT NULL DEFAULT 'default',
			session_id  TEXT    NOT NULL,
			role        TEXT    NOT NULL,
			content     TEXT    NOT NULL,
			msg_index   INTEGER NOT NULL,
			timestamp   TEXT    NOT NULL,
			metadata    TEXT,
			distilled   INTEGER DEFAULT 0,
			UNIQUE(tenant_id, project_id, session_id, msg_index)
		)`,
		`INSERT OR IGNORE INTO conversation_log_scoped
			(id, tenant_id, project_id, session_id, role, content, msg_index, timestamp, metadata, distilled)
			SELECT id, COALESCE(tenant_id, 'local'), COALESCE(project_id, 'default'),
			       session_id, role, content, msg_index, timestamp, metadata, distilled
			FROM conversation_log`,
		`DROP TABLE conversation_log`,
		`ALTER TABLE conversation_log_scoped RENAME TO conversation_log`,
		`CREATE INDEX IF NOT EXISTS idx_conv_scope_session ON conversation_log(tenant_id, project_id, session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_conv_session ON conversation_log(session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_conv_distilled ON conversation_log(distilled)`,
		`CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversation_log(timestamp)`,
	}
	for _, stmt := range stmts {
		if _, err := r.db.Exec(stmt); err != nil {
			return fmt.Errorf("migrate conversation scope key: %w", err)
		}
	}
	return nil
}

// Record inserts a single entry. Idempotent on (session_id, msg_index) —
// re-ingesting the same transcript is a no-op for already-stored messages.
func (r *ConversationLogRepo) Record(ctx context.Context, e ConversationEntry) error {
	sc := rlmscope.FromContext(ctx)
	if e.SessionID == "" || e.Role == "" {
		return fmt.Errorf("session_id and role are required")
	}
	e.TenantID = sc.TenantID
	e.ProjectID = sc.ProjectID
	ts := e.Timestamp
	if ts.IsZero() {
		ts = time.Now().UTC()
	}
	_, err := r.db.Exec(
		`INSERT OR IGNORE INTO conversation_log
			(tenant_id, project_id, session_id, role, content, msg_index, timestamp, metadata, distilled)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		e.TenantID, e.ProjectID, e.SessionID, e.Role, e.Content, e.MsgIndex,
		ts.UTC().Format(time.RFC3339Nano), e.Metadata, boolToInt(e.Distilled),
	)
	if err != nil {
		return fmt.Errorf("record conversation: %w", err)
	}
	return nil
}

// RecordBatch inserts many entries in a single transaction. Returns the count
// actually inserted (duplicates skipped via INSERT OR IGNORE).
func (r *ConversationLogRepo) RecordBatch(ctx context.Context, entries []ConversationEntry) (int, error) {
	if len(entries) == 0 {
		return 0, nil
	}
	sc := rlmscope.FromContext(ctx)
	tx, err := r.db.SqlDB().Begin()
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	stmt, err := tx.Prepare(
		`INSERT OR IGNORE INTO conversation_log
			(tenant_id, project_id, session_id, role, content, msg_index, timestamp, metadata, distilled)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
	)
	if err != nil {
		return 0, fmt.Errorf("prepare: %w", err)
	}
	defer stmt.Close()

	inserted := 0
	for _, e := range entries {
		if e.SessionID == "" || e.Role == "" {
			continue
		}
		ts := e.Timestamp
		if ts.IsZero() {
			ts = time.Now().UTC()
		}
		res, err := stmt.Exec(
			sc.TenantID, sc.ProjectID, e.SessionID, e.Role, e.Content, e.MsgIndex,
			ts.UTC().Format(time.RFC3339Nano), e.Metadata, boolToInt(e.Distilled),
		)
		if err != nil {
			return inserted, fmt.Errorf("insert msg=%d: %w", e.MsgIndex, err)
		}
		n, _ := res.RowsAffected()
		inserted += int(n)
	}
	if err := tx.Commit(); err != nil {
		return inserted, fmt.Errorf("commit: %w", err)
	}
	return inserted, nil
}

// GetSession returns all messages for a session, ordered by msg_index.
func (r *ConversationLogRepo) GetSession(ctx context.Context, sessionID string) ([]ConversationEntry, error) {
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(
		`SELECT id, tenant_id, project_id, session_id, role, content, msg_index, timestamp, COALESCE(metadata, ''), distilled
			FROM conversation_log
			WHERE tenant_id = ? AND project_id = ? AND session_id = ?
			ORDER BY msg_index ASC`, sc.TenantID, sc.ProjectID, sessionID)
	if err != nil {
		return nil, fmt.Errorf("get session: %w", err)
	}
	defer rows.Close()
	return scanConversations(rows)
}

// GetUndistilled returns the oldest undistilled messages across all sessions,
// up to limit. Used by the distillation pipeline.
func (r *ConversationLogRepo) GetUndistilled(ctx context.Context, limit int) ([]ConversationEntry, error) {
	if limit <= 0 {
		limit = 200
	}
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(
		`SELECT id, tenant_id, project_id, session_id, role, content, msg_index, timestamp, COALESCE(metadata, ''), distilled
			FROM conversation_log
			WHERE tenant_id = ? AND project_id = ? AND distilled = 0
			ORDER BY id ASC LIMIT ?`, sc.TenantID, sc.ProjectID, limit)
	if err != nil {
		return nil, fmt.Errorf("get undistilled: %w", err)
	}
	defer rows.Close()
	return scanConversations(rows)
}

// MarkDistilled flags entries as consumed by the distillation pipeline.
func (r *ConversationLogRepo) MarkDistilled(ctx context.Context, ids []int64) error {
	if len(ids) == 0 {
		return nil
	}
	sc := rlmscope.FromContext(ctx)
	tx, err := r.db.SqlDB().Begin()
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	stmt, err := tx.Prepare(`UPDATE conversation_log SET distilled = 1
		WHERE id = ? AND tenant_id = ? AND project_id = ?`)
	if err != nil {
		return err
	}
	defer stmt.Close()
	for _, id := range ids {
		if _, err := stmt.Exec(id, sc.TenantID, sc.ProjectID); err != nil {
			return fmt.Errorf("mark id=%d: %w", id, err)
		}
	}
	return tx.Commit()
}

// Prune deletes distilled entries older than the given duration. Undistilled
// entries are never pruned — the distillation pipeline owns the decision.
func (r *ConversationLogRepo) Prune(ctx context.Context, olderThan time.Duration) (int64, error) {
	sc := rlmscope.FromContext(ctx)
	cutoff := time.Now().UTC().Add(-olderThan).Format(time.RFC3339Nano)
	res, err := r.db.Exec(
		`DELETE FROM conversation_log
		 WHERE tenant_id = ? AND project_id = ? AND distilled = 1 AND timestamp <= ?`,
		sc.TenantID, sc.ProjectID, cutoff)
	if err != nil {
		return 0, fmt.Errorf("prune: %w", err)
	}
	return res.RowsAffected()
}

// Stats reports aggregate counts.
type ConversationStats struct {
	TotalMessages   int `json:"total_messages"`
	TotalSessions   int `json:"total_sessions"`
	UndistilledRows int `json:"undistilled"`
}

// Stats returns conversation log statistics.
func (r *ConversationLogRepo) Stats(ctx context.Context) (ConversationStats, error) {
	sc := rlmscope.FromContext(ctx)
	var s ConversationStats
	err := r.db.QueryRow(`SELECT COUNT(*), COUNT(DISTINCT session_id),
		COALESCE(SUM(CASE WHEN distilled = 0 THEN 1 ELSE 0 END), 0)
		FROM conversation_log WHERE tenant_id = ? AND project_id = ?`,
		sc.TenantID, sc.ProjectID).Scan(&s.TotalMessages, &s.TotalSessions, &s.UndistilledRows)
	if err != nil {
		return s, fmt.Errorf("stats: %w", err)
	}
	return s, nil
}

// --- helpers ---

func scanConversations(rows interface {
	Next() bool
	Scan(...interface{}) error
	Err() error
}) ([]ConversationEntry, error) {
	var out []ConversationEntry
	for rows.Next() {
		var e ConversationEntry
		var ts string
		var distilled int
		if err := rows.Scan(&e.ID, &e.TenantID, &e.ProjectID, &e.SessionID, &e.Role, &e.Content,
			&e.MsgIndex, &ts, &e.Metadata, &distilled); err != nil {
			return nil, fmt.Errorf("scan conversation: %w", err)
		}
		e.Timestamp, _ = time.Parse(time.RFC3339Nano, ts)
		e.Distilled = distilled != 0
		out = append(out, e)
	}
	return out, rows.Err()
}
