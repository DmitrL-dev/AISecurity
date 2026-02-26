package sqlite

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// InteractionEntry represents a single tool call record in the interaction log.
type InteractionEntry struct {
	ID        int64     `json:"id"`
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
			tool_name TEXT    NOT NULL,
			args_json TEXT,
			timestamp TEXT    NOT NULL,
			processed INTEGER DEFAULT 0
		)`
	if _, err := db.Exec(createSQL); err != nil {
		return nil, fmt.Errorf("create interaction_log table: %w", err)
	}
	return &InteractionLogRepo{db: db}, nil
}

// Record inserts a tool call entry. This is designed to be fire-and-forget
// from the middleware — errors are logged but don't break the tool call.
func (r *InteractionLogRepo) Record(ctx context.Context, toolName string, args map[string]interface{}) error {
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
		`INSERT INTO interaction_log (tool_name, args_json, timestamp) VALUES (?, ?, ?)`,
		toolName, argsJSON, now,
	)
	return err
}

// GetUnprocessed returns all entries not yet processed, ordered oldest first.
func (r *InteractionLogRepo) GetUnprocessed(ctx context.Context) ([]InteractionEntry, error) {
	rows, err := r.db.Query(
		`SELECT id, tool_name, args_json, timestamp, processed 
		 FROM interaction_log WHERE processed = 0 ORDER BY id ASC`,
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
		if err := rows.Scan(&e.ID, &e.ToolName, &e.ArgsJSON, &ts, &proc); err != nil {
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
	for _, id := range ids {
		if _, err := r.db.Exec(`UPDATE interaction_log SET processed = 1 WHERE id = ?`, id); err != nil {
			return fmt.Errorf("mark processed id=%d: %w", id, err)
		}
	}
	return nil
}

// Count returns the total number of entries and unprocessed count.
func (r *InteractionLogRepo) Count(ctx context.Context) (total int, unprocessed int, err error) {
	row := r.db.QueryRow(`SELECT COUNT(*), COALESCE(SUM(CASE WHEN processed=0 THEN 1 ELSE 0 END), 0) FROM interaction_log`)
	err = row.Scan(&total, &unprocessed)
	return
}

// Prune deletes processed entries older than the given duration.
func (r *InteractionLogRepo) Prune(ctx context.Context, olderThan time.Duration) (int64, error) {
	cutoff := time.Now().UTC().Add(-olderThan).Format(time.RFC3339)
	result, err := r.db.Exec(
		`DELETE FROM interaction_log WHERE processed = 1 AND timestamp <= ?`, cutoff,
	)
	if err != nil {
		return 0, err
	}
	return result.RowsAffected()
}
