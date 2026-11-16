package sqlite

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/session"
)

// StateRepo implements session.StateStore using SQLite.
// Compatible with memory_bridge.db schema (states + audit_log).
// NOTE: The Python version uses AES-256-GCM encryption on the data blob.
// This Go implementation stores plaintext JSON for now — encryption
// can be layered on top via a decorator if needed.
type StateRepo struct {
	db *DB
}

// NewStateRepo creates a StateRepo and ensures the schema exists.
func NewStateRepo(db *DB) (*StateRepo, error) {
	repo := &StateRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("state repo migrate: %w", err)
	}
	return repo, nil
}

func (r *StateRepo) migrate() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS states (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			session_id TEXT NOT NULL,
			version INTEGER NOT NULL,
			timestamp TEXT NOT NULL,
			checksum TEXT NOT NULL,
			data BLOB NOT NULL,
			nonce BLOB,
			created_at TEXT DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(tenant_id, project_id, session_id, version)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_state_scope_session ON states(tenant_id, project_id, session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_session_id ON states(session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_timestamp ON states(timestamp)`,
		`CREATE TABLE IF NOT EXISTS audit_log (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			session_id TEXT NOT NULL,
			action TEXT NOT NULL,
			version INTEGER,
			timestamp TEXT NOT NULL,
			details TEXT,
			created_at TEXT DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_audit_scope_session ON audit_log(tenant_id, project_id, session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)`,
	}
	for _, s := range stmts {
		if _, err := r.db.Exec(s); err != nil {
			return fmt.Errorf("exec migration: %w", err)
		}
	}
	// Scope migration for databases created before tenant/project isolation.
	_, _ = r.db.Exec(`ALTER TABLE states ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`)
	_, _ = r.db.Exec(`ALTER TABLE states ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`)
	_, _ = r.db.Exec(`ALTER TABLE audit_log ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`)
	_, _ = r.db.Exec(`ALTER TABLE audit_log ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`)
	if err := r.migrateStatesScopeKey(); err != nil {
		return err
	}
	return nil
}

func (r *StateRepo) migrateStatesScopeKey() error {
	var tableSQL string
	if err := r.db.QueryRow(`SELECT sql FROM sqlite_master WHERE type='table' AND name='states'`).Scan(&tableSQL); err != nil {
		return nil
	}
	if strings.Contains(tableSQL, "tenant_id, project_id, session_id, version") {
		return nil
	}
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS states_scoped (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			session_id TEXT NOT NULL,
			version INTEGER NOT NULL,
			timestamp TEXT NOT NULL,
			checksum TEXT NOT NULL,
			data BLOB NOT NULL,
			nonce BLOB,
			created_at TEXT DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(tenant_id, project_id, session_id, version)
		)`,
		`INSERT OR IGNORE INTO states_scoped
			(id, tenant_id, project_id, session_id, version, timestamp, checksum, data, nonce, created_at)
			SELECT id, COALESCE(tenant_id, 'local'), COALESCE(project_id, 'default'),
			       session_id, version, timestamp, checksum, data, nonce, created_at
			FROM states`,
		`DROP TABLE states`,
		`ALTER TABLE states_scoped RENAME TO states`,
		`CREATE INDEX IF NOT EXISTS idx_session_id ON states(session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_timestamp ON states(timestamp)`,
		`CREATE INDEX IF NOT EXISTS idx_state_scope_session ON states(tenant_id, project_id, session_id)`,
	}
	for _, stmt := range stmts {
		if _, err := r.db.Exec(stmt); err != nil {
			return fmt.Errorf("migrate states scope key: %w", err)
		}
	}
	return nil
}

// Save persists a cognitive state vector snapshot.
func (r *StateRepo) Save(ctx context.Context, state *session.CognitiveStateVector, checksum string) error {
	sc := rlmscope.FromContext(ctx)
	data, err := json.Marshal(state)
	if err != nil {
		return fmt.Errorf("marshal state: %w", err)
	}

	// Verify checksum if provided, or compute one.
	if checksum == "" {
		h := sha256.Sum256(data)
		checksum = hex.EncodeToString(h[:])
	}

	now := time.Now().Format(timeFormat)

	// Determine action for audit log.
	var action string
	var existingCount int
	row := r.db.QueryRow(`SELECT COUNT(*) FROM states
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		sc.TenantID, sc.ProjectID, state.SessionID)
	if err := row.Scan(&existingCount); err != nil {
		return fmt.Errorf("count existing: %w", err)
	}
	if existingCount == 0 {
		action = "create"
	} else {
		action = "update"
	}

	_, err = r.db.Exec(`INSERT INTO states (tenant_id, project_id, session_id, version, timestamp, checksum, data)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		sc.TenantID, sc.ProjectID, state.SessionID, state.Version, now, checksum, data,
	)
	if err != nil {
		return fmt.Errorf("insert state: %w", err)
	}

	// Write audit log entry.
	_, err = r.db.Exec(`INSERT INTO audit_log (tenant_id, project_id, session_id, action, version, timestamp, details)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		sc.TenantID, sc.ProjectID, state.SessionID, action, state.Version, now,
		fmt.Sprintf("%s session %s v%d", action, state.SessionID, state.Version),
	)
	if err != nil {
		return fmt.Errorf("insert audit: %w", err)
	}

	return nil
}

// Load retrieves a cognitive state vector. If version is nil, loads the latest.
func (r *StateRepo) Load(ctx context.Context, sessionID string, version *int) (*session.CognitiveStateVector, string, error) {
	sc := rlmscope.FromContext(ctx)
	var row *sql.Row
	if version != nil {
		row = r.db.QueryRow(`SELECT data, checksum FROM states
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND version = ?`,
			sc.TenantID, sc.ProjectID, sessionID, *version)
	} else {
		row = r.db.QueryRow(`SELECT data, checksum FROM states
			WHERE tenant_id = ? AND project_id = ? AND session_id = ?
			ORDER BY version DESC LIMIT 1`,
			sc.TenantID, sc.ProjectID, sessionID)
	}

	var data []byte
	var checksum string
	if err := row.Scan(&data, &checksum); err != nil {
		if err == sql.ErrNoRows {
			return nil, "", fmt.Errorf("session %s not found", sessionID)
		}
		return nil, "", fmt.Errorf("scan state: %w", err)
	}

	var state session.CognitiveStateVector
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, "", fmt.Errorf("unmarshal state: %w", err)
	}

	return &state, checksum, nil
}

// ListSessions returns metadata about all persisted sessions.
func (r *StateRepo) ListSessions(ctx context.Context) ([]session.SessionInfo, error) {
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(`SELECT session_id, MAX(version) as version, MAX(timestamp) as updated_at
		FROM states WHERE tenant_id = ? AND project_id = ?
		GROUP BY session_id ORDER BY updated_at DESC`, sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("list sessions: %w", err)
	}
	defer rows.Close()

	var sessions []session.SessionInfo
	for rows.Next() {
		var info session.SessionInfo
		var updatedAt string
		if err := rows.Scan(&info.SessionID, &info.Version, &updatedAt); err != nil {
			return nil, fmt.Errorf("scan session info: %w", err)
		}
		info.UpdatedAt, _ = time.Parse(timeFormat, updatedAt)
		sessions = append(sessions, info)
	}
	return sessions, rows.Err()
}

// DeleteSession removes all versions of a session. Returns the number of deleted rows.
func (r *StateRepo) DeleteSession(ctx context.Context, sessionID string) (int, error) {
	sc := rlmscope.FromContext(ctx)
	now := time.Now().Format(timeFormat)

	result, err := r.db.Exec(`DELETE FROM states
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?`,
		sc.TenantID, sc.ProjectID, sessionID)
	if err != nil {
		return 0, fmt.Errorf("delete session: %w", err)
	}
	n, _ := result.RowsAffected()

	// Audit log.
	_, _ = r.db.Exec(`INSERT INTO audit_log (tenant_id, project_id, session_id, action, timestamp, details)
		VALUES (?, ?, ?, 'delete', ?, ?)`,
		sc.TenantID, sc.ProjectID, sessionID, now, fmt.Sprintf("deleted %d versions of session %s", n, sessionID),
	)

	return int(n), nil
}

// GetAuditLog returns the audit log for a session.
func (r *StateRepo) GetAuditLog(ctx context.Context, sessionID string, limit int) ([]session.AuditEntry, error) {
	if limit <= 0 {
		limit = 50
	}
	sc := rlmscope.FromContext(ctx)
	rows, err := r.db.Query(`SELECT session_id, action, version, timestamp, details
		FROM audit_log
		WHERE tenant_id = ? AND project_id = ? AND session_id = ?
		ORDER BY id DESC LIMIT ?`,
		sc.TenantID, sc.ProjectID, sessionID, limit)
	if err != nil {
		return nil, fmt.Errorf("get audit log: %w", err)
	}
	defer rows.Close()

	var entries []session.AuditEntry
	for rows.Next() {
		var e session.AuditEntry
		var version sql.NullInt64
		if err := rows.Scan(&e.SessionID, &e.Action, &version, &e.Timestamp, &e.Details); err != nil {
			return nil, fmt.Errorf("scan audit entry: %w", err)
		}
		if version.Valid {
			e.Version = int(version.Int64)
		}
		entries = append(entries, e)
	}
	return entries, rows.Err()
}

// Ensure StateRepo implements session.StateStore.
var _ session.StateStore = (*StateRepo)(nil)
