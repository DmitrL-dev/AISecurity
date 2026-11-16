package sqlite

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// InteractionEntry represents a single tool call record in the interaction log.
type InteractionEntry struct {
	ID        int64     `json:"id"`
	TenantID  string    `json:"tenant_id,omitempty"`
	ProjectID string    `json:"project_id,omitempty"`
	ToolName  string    `json:"tool_name"`
	ArgsJSON  string    `json:"args_json,omitempty"`
	Timestamp time.Time `json:"timestamp"`
	Processed bool      `json:"processed"`
}

// InteractionLogRepo provides crash-safe tool call recording in SQLite.
// Every tool call is INSERT-ed immediately; WAL mode ensures durability
// even on kill -9 / terminal close.
type InteractionLogRepo struct {
	db *DB
}

// NewInteractionLogRepo creates the interaction_log table if needed and returns the repo.
func NewInteractionLogRepo(db *DB) (*InteractionLogRepo, error) {
	createSQL := `
		CREATE TABLE IF NOT EXISTS interaction_log (
			id        INTEGER PRIMARY KEY AUTOINCREMENT,
			tenant_id TEXT    NOT NULL DEFAULT 'local',
			project_id TEXT   NOT NULL DEFAULT 'default',
			tool_name TEXT    NOT NULL,
			args_json TEXT,
			timestamp TEXT    NOT NULL,
			processed INTEGER DEFAULT 0
		)`
	if _, err := db.Exec(createSQL); err != nil {
		return nil, fmt.Errorf("create interaction_log table: %w", err)
	}
	_, _ = db.Exec(`ALTER TABLE interaction_log ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`)
	_, _ = db.Exec(`ALTER TABLE interaction_log ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`)
	_, _ = db.Exec(`CREATE INDEX IF NOT EXISTS idx_interaction_scope_processed
		ON interaction_log(tenant_id, project_id, processed)`)
	if err := quarantineExactProtocolInteractions(db); err != nil {
		return nil, err
	}
	return &InteractionLogRepo{db: db}, nil
}

// quarantineExactProtocolInteractions closes the upgrade window left by older
// middleware builds that logged exact-memory tool arguments. Those rows must
// never be summarized into project-wide session-history facts. Keeping the
// processed rows provides a durable audit trail without making their arguments
// reachable to the processor.
func quarantineExactProtocolInteractions(db *DB) error {
	tx, err := db.SqlDB().Begin()
	if err != nil {
		return fmt.Errorf("begin exact interaction quarantine: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	toolNames := memory.ExactProtocolToolNames()
	placeholders := make([]string, len(toolNames))
	args := make([]any, len(toolNames))
	for i, name := range toolNames {
		placeholders[i] = "?"
		args[i] = name
	}
	if _, err := tx.Exec(`UPDATE interaction_log SET processed = 1
		WHERE processed = 0 AND tool_name IN (`+strings.Join(placeholders, ",")+`)`, args...); err != nil {
		return fmt.Errorf("quarantine exact interaction rows: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit exact interaction quarantine: %w", err)
	}
	return nil
}

// Record inserts a tool call entry. This is designed to be fire-and-forget
// from the middleware — errors are logged but don't break the tool call.
func (r *InteractionLogRepo) Record(ctx context.Context, toolName string, args map[string]interface{}) error {
	if memory.IsExactProtocolTool(toolName) {
		return fmt.Errorf("exact protocol tool %q must not be recorded", toolName)
	}
	sc := rlmscope.FromContext(ctx)
	argsJSON := ""
	if len(args) > 0 {
		// Only keep string arguments to reduce noise
		filtered := make(map[string]string)
		for k, v := range args {
			if s, ok := v.(string); ok && s != "" {
				// Truncate very long values
				if len(s) > 200 {
					s = s[:200] + "..."
				}
				filtered[k] = s
			}
		}
		if len(filtered) > 0 {
			data, _ := json.Marshal(filtered)
			argsJSON = string(data)
		}
	}

	now := time.Now().UTC().Format(time.RFC3339)
	_, err := r.db.Exec(
		`INSERT INTO interaction_log (tenant_id, project_id, tool_name, args_json, timestamp)
		 VALUES (?, ?, ?, ?, ?)`,
		sc.TenantID, sc.ProjectID, toolName, argsJSON, now,
	)
	return err
}

// GetUnprocessed returns all entries not yet processed, ordered oldest first.
func (r *InteractionLogRepo) GetUnprocessed(ctx context.Context) ([]InteractionEntry, error) {
	sc := rlmscope.FromContext(ctx)
	toolNames := memory.ExactProtocolToolNames()
	placeholders := make([]string, len(toolNames))
	args := []any{sc.TenantID, sc.ProjectID}
	for i, name := range toolNames {
		placeholders[i] = "?"
		args = append(args, name)
	}
	rows, err := r.db.Query(
		`SELECT id, tenant_id, project_id, tool_name, args_json, timestamp, processed
		 FROM interaction_log
		 WHERE tenant_id = ? AND project_id = ? AND processed = 0
		   AND tool_name NOT IN (`+strings.Join(placeholders, ",")+`)
		 ORDER BY id ASC`, args...,
	)
	if err != nil {
		return nil, fmt.Errorf("query unprocessed: %w", err)
	}
	defer rows.Close()

	var entries []InteractionEntry
	for rows.Next() {
		var e InteractionEntry
		var ts string
		var proc int
		if err := rows.Scan(&e.ID, &e.TenantID, &e.ProjectID, &e.ToolName, &e.ArgsJSON, &ts, &proc); err != nil {
			return nil, fmt.Errorf("scan entry: %w", err)
		}
		e.Timestamp, _ = time.Parse(time.RFC3339, ts)
		e.Processed = proc != 0
		entries = append(entries, e)
	}
	return entries, rows.Err()
}

// MarkProcessed marks entries as processed by their IDs.
func (r *InteractionLogRepo) MarkProcessed(ctx context.Context, ids []int64) error {
	if len(ids) == 0 {
		return nil
	}
	sc := rlmscope.FromContext(ctx)
	for _, id := range ids {
		if _, err := r.db.Exec(`UPDATE interaction_log SET processed = 1
			WHERE id = ? AND tenant_id = ? AND project_id = ?`,
			id, sc.TenantID, sc.ProjectID); err != nil {
			return fmt.Errorf("mark processed id=%d: %w", id, err)
		}
	}
	return nil
}

// Count returns the total number of entries and unprocessed count.
func (r *InteractionLogRepo) Count(ctx context.Context) (total int, unprocessed int, err error) {
	sc := rlmscope.FromContext(ctx)
	row := r.db.QueryRow(`SELECT COUNT(*), COALESCE(SUM(CASE WHEN processed=0 THEN 1 ELSE 0 END), 0)
		FROM interaction_log WHERE tenant_id = ? AND project_id = ?`,
		sc.TenantID, sc.ProjectID)
	err = row.Scan(&total, &unprocessed)
	return
}

// Prune deletes processed entries older than the given duration.
func (r *InteractionLogRepo) Prune(ctx context.Context, olderThan time.Duration) (int64, error) {
	sc := rlmscope.FromContext(ctx)
	cutoff := time.Now().UTC().Add(-olderThan).Format(time.RFC3339)
	result, err := r.db.Exec(
		`DELETE FROM interaction_log
		 WHERE tenant_id = ? AND project_id = ? AND processed = 1 AND timestamp <= ?`,
		sc.TenantID, sc.ProjectID, cutoff,
	)
	if err != nil {
		return 0, err
	}
	return result.RowsAffected()
}
