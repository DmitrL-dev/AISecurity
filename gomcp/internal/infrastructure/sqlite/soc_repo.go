package sqlite

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/soc"
)

// SOCRepo provides SQLite persistence for SOC events, incidents, and sensors.
type SOCRepo struct {
	db *DB
}

// NewSOCRepo creates and initializes SOC tables.
func NewSOCRepo(db *DB) (*SOCRepo, error) {
	repo := &SOCRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("soc_repo: migrate: %w", err)
	}
	return repo, nil
}

func (r *SOCRepo) migrate() error {
	tables := []string{
		`CREATE TABLE IF NOT EXISTS soc_events (
			id            TEXT PRIMARY KEY,
			tenant_id     TEXT NOT NULL DEFAULT '',
			source        TEXT NOT NULL,
			sensor_id     TEXT NOT NULL DEFAULT '',
			severity      TEXT NOT NULL,
			category      TEXT NOT NULL,
			subcategory   TEXT NOT NULL DEFAULT '',
			confidence    REAL NOT NULL DEFAULT 0.0,
			description   TEXT NOT NULL DEFAULT '',
			session_id    TEXT NOT NULL DEFAULT '',
			content_hash  TEXT NOT NULL DEFAULT '',
			decision_hash TEXT NOT NULL DEFAULT '',
			verdict       TEXT NOT NULL DEFAULT 'REVIEW',
			timestamp     TEXT NOT NULL,
			metadata      TEXT NOT NULL DEFAULT '{}'
		)`,
		`CREATE TABLE IF NOT EXISTS soc_incidents (
			id                    TEXT PRIMARY KEY,
			tenant_id             TEXT NOT NULL DEFAULT '',
			status                TEXT NOT NULL DEFAULT 'OPEN',
			severity              TEXT NOT NULL,
			title                 TEXT NOT NULL,
			description           TEXT NOT NULL DEFAULT '',
			event_ids             TEXT NOT NULL DEFAULT '[]',
			event_count           INTEGER NOT NULL DEFAULT 0,
			decision_chain_anchor TEXT NOT NULL DEFAULT '',
			chain_length          INTEGER NOT NULL DEFAULT 0,
			correlation_rule      TEXT NOT NULL DEFAULT '',
			kill_chain_phase      TEXT NOT NULL DEFAULT '',
			mitre_mapping         TEXT NOT NULL DEFAULT '[]',
			playbook_applied      TEXT NOT NULL DEFAULT '',
			assigned_to           TEXT NOT NULL DEFAULT '',
			notes_json            TEXT NOT NULL DEFAULT '[]',
			timeline_json         TEXT NOT NULL DEFAULT '[]',
			created_at            TEXT NOT NULL,
			updated_at            TEXT NOT NULL,
			resolved_at           TEXT
		)`,
		`CREATE TABLE IF NOT EXISTS soc_sensors (
			sensor_id         TEXT PRIMARY KEY,
			tenant_id         TEXT NOT NULL DEFAULT '',
			sensor_type       TEXT NOT NULL,
			status            TEXT DEFAULT 'UNKNOWN',
			first_seen        TEXT NOT NULL,
			last_seen         TEXT NOT NULL,
			event_count       INTEGER DEFAULT 0,
			missed_heartbeats INTEGER DEFAULT 0,
			hostname          TEXT NOT NULL DEFAULT '',
			version           TEXT NOT NULL DEFAULT ''
		)`,
		// Pre-signup waitlist (deletable PII store — GDPR Art.17). Cleartext lives
		// here, not in the immutable decision chain.
		`CREATE TABLE IF NOT EXISTS soc_waitlist (
			id         TEXT PRIMARY KEY,
			email      TEXT NOT NULL,
			company    TEXT NOT NULL DEFAULT '',
			use_case   TEXT NOT NULL DEFAULT '',
			created_at TEXT NOT NULL
		)`,
		// Indexes for non-tenant columns only — safe on any schema version.
		// tenant_id indexes are applied after ALTER TABLE migrations below.
		`CREATE INDEX IF NOT EXISTS idx_soc_events_timestamp ON soc_events(timestamp)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_events_severity ON soc_events(severity)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_events_category ON soc_events(category)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_events_sensor ON soc_events(sensor_id)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_events_content_hash ON soc_events(content_hash)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_incidents_status ON soc_incidents(status)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_sensors_status ON soc_sensors(status)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_waitlist_email ON soc_waitlist(email)`,
	}
	for _, ddl := range tables {
		if _, err := r.db.Exec(ddl); err != nil {
			return fmt.Errorf("exec %q: %w", ddl[:40], err)
		}
	}
	// Migration: add columns and tenant indexes after columns are guaranteed to exist.
	// All steps ignore errors — safe to re-run on any schema version.
	migrations := []string{
		`ALTER TABLE soc_incidents ADD COLUMN assigned_to TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE soc_incidents ADD COLUMN notes_json TEXT NOT NULL DEFAULT '[]'`,
		`ALTER TABLE soc_incidents ADD COLUMN timeline_json TEXT NOT NULL DEFAULT '[]'`,
		// first_event_at: earliest correlated-event time, the MTTD anchor (IMP6).
		// Nullable — pre-migration rows have no value, surfaced as zero/unknown so
		// MTTD aggregation skips them rather than reporting a false 0s detection.
		`ALTER TABLE soc_incidents ADD COLUMN first_event_at TEXT`,
		`ALTER TABLE soc_events ADD COLUMN tenant_id TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE soc_incidents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE soc_sensors ADD COLUMN tenant_id TEXT NOT NULL DEFAULT ''`,
		// tenant_id indexes — must come AFTER the ALTER TABLE statements above.
		`CREATE INDEX IF NOT EXISTS idx_soc_events_tenant ON soc_events(tenant_id)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_incidents_tenant ON soc_incidents(tenant_id)`,
		`CREATE INDEX IF NOT EXISTS idx_soc_sensors_tenant ON soc_sensors(tenant_id)`,
	}
	for _, m := range migrations {
		r.db.Exec(m) // Ignore errors (column/index already exists)
	}
	return nil
}

// === Events ===

// InsertEvent persists a SOC event.
func (r *SOCRepo) InsertEvent(e soc.SOCEvent) error {
	metaJSON := "{}"
	if len(e.Metadata) > 0 {
		if b, err := json.Marshal(e.Metadata); err == nil {
			metaJSON = string(b)
		}
	}
	_, err := r.db.Exec(
		`INSERT INTO soc_events (id, tenant_id, source, sensor_id, severity, category, subcategory,
		 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		e.ID, e.TenantID, e.Source, e.SensorID, e.Severity, e.Category, e.Subcategory,
		e.Confidence, e.Description, e.SessionID, e.ContentHash, e.DecisionHash, e.Verdict,
		e.Timestamp.Format(time.RFC3339Nano), metaJSON,
	)
	return err
}

// EventExistsByHash checks if an event with the given content hash already exists (§5.2 dedup).
func (r *SOCRepo) EventExistsByHash(tenantID, contentHash string) (bool, error) {
	if contentHash == "" {
		return false, nil
	}
	var count int
	err := r.db.QueryRow(
		"SELECT COUNT(*) FROM soc_events WHERE tenant_id = ? AND content_hash = ?", tenantID, contentHash,
	).Scan(&count)
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

// ListEvents returns events ordered by timestamp (newest first), with limit.
func (r *SOCRepo) ListEvents(tenantID string, limit int) ([]soc.SOCEvent, error) {
	if limit <= 0 {
		limit = 50
	}
	var rows *sql.Rows
	var err error
	if tenantID != "" {
		rows, err = r.db.Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events WHERE tenant_id = ? ORDER BY timestamp DESC LIMIT ?`, tenantID, limit)
	} else {
		rows, err = r.db.Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events ORDER BY timestamp DESC LIMIT ?`, limit)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanEvents(rows)
}

// ListEventsByCategory returns events filtered by category.
func (r *SOCRepo) ListEventsByCategory(tenantID string, category string, limit int) ([]soc.SOCEvent, error) {
	if limit <= 0 {
		limit = 50
	}
	var rows *sql.Rows
	var err error
	if tenantID != "" {
		rows, err = r.db.Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events WHERE tenant_id = ? AND category = ? ORDER BY timestamp DESC LIMIT ?`,
			tenantID, category, limit)
	} else {
		rows, err = r.db.Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events WHERE category = ? ORDER BY timestamp DESC LIMIT ?`,
			category, limit)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanEvents(rows)
}

// CountEvents returns total event count.
func (r *SOCRepo) CountEvents(tenantID string) (int, error) {
	var count int
	var err error
	if tenantID != "" {
		err = r.db.QueryRow("SELECT COUNT(*) FROM soc_events WHERE tenant_id = ?", tenantID).Scan(&count)
	} else {
		err = r.db.QueryRow("SELECT COUNT(*) FROM soc_events").Scan(&count)
	}
	return count, err
}

// GetEvent retrieves a single event by ID.
func (r *SOCRepo) GetEvent(id string) (*soc.SOCEvent, error) {
	var e soc.SOCEvent
	var ts string
	var metaJSON string
	// tenant_id MUST be selected/scanned so callers that scope by tenant
	// (IDOR prevention) see the real owner — consistent with scanEvents and
	// GetIncident. Previously omitted, leaving TenantID always "".
	err := r.db.QueryRow(
		`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
		 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
		 FROM soc_events WHERE id = ?`, id,
	).Scan(&e.ID, &e.TenantID, &e.Source, &e.SensorID, &e.Severity,
		&e.Category, &e.Subcategory, &e.Confidence, &e.Description,
		&e.SessionID, &e.ContentHash, &e.DecisionHash, &e.Verdict, &ts, &metaJSON)
	if err != nil {
		return nil, err
	}
	e.Timestamp, _ = time.Parse(time.RFC3339Nano, ts)
	if metaJSON != "" && metaJSON != "{}" {
		json.Unmarshal([]byte(metaJSON), &e.Metadata)
	}
	return &e, nil
}

// CountEventsSince returns events in the given time window.
func (r *SOCRepo) CountEventsSince(tenantID string, since time.Time) (int, error) {
	var count int
	var err error
	if tenantID != "" {
		err = r.db.QueryRow(
			"SELECT COUNT(*) FROM soc_events WHERE tenant_id = ? AND timestamp >= ?",
			tenantID, since.Format(time.RFC3339Nano),
		).Scan(&count)
	} else {
		err = r.db.QueryRow(
			"SELECT COUNT(*) FROM soc_events WHERE timestamp >= ?",
			since.Format(time.RFC3339Nano),
		).Scan(&count)
	}
	return count, err
}

func scanEvents(rows *sql.Rows) ([]soc.SOCEvent, error) {
	var events []soc.SOCEvent
	for rows.Next() {
		var e soc.SOCEvent
		var ts, metaJSON string
		err := rows.Scan(&e.ID, &e.TenantID, &e.Source, &e.SensorID, &e.Severity,
			&e.Category, &e.Subcategory, &e.Confidence, &e.Description,
			&e.SessionID, &e.ContentHash, &e.DecisionHash, &e.Verdict, &ts, &metaJSON)
		if err != nil {
			return nil, err
		}
		e.Timestamp, _ = time.Parse(time.RFC3339Nano, ts)
		if metaJSON != "" && metaJSON != "{}" {
			json.Unmarshal([]byte(metaJSON), &e.Metadata)
		}
		events = append(events, e)
	}
	return events, rows.Err()
}

// === Incidents ===

// incidentJSON encodes before writing: unsupported timeline metadata must not
// silently discard evidence or partially update an incident.
func incidentJSON(inc soc.Incident) (events, mitre, notes, timeline string, err error) {
	values := []any{inc.Events, inc.MITREMapping, inc.Notes, inc.Timeline}
	encoded := make([]string, len(values))
	for i, value := range values {
		b, encodeErr := json.Marshal(value)
		if encodeErr != nil {
			err = fmt.Errorf("encode incident evidence: %w", encodeErr)
			return
		}
		if string(b) == "null" {
			b = []byte("[]")
		}
		encoded[i] = string(b)
	}
	return encoded[0], encoded[1], encoded[2], encoded[3], nil
}

func decodeIncidentJSON(inc *soc.Incident, events, mitre, notes, timeline string) error {
	values := []any{&inc.Events, &inc.MITREMapping, &inc.Notes, &inc.Timeline}
	for i, text := range []string{events, mitre, notes, timeline} {
		if err := json.Unmarshal([]byte(text), values[i]); err != nil {
			return fmt.Errorf("decode incident evidence: %w", err)
		}
	}
	return nil
}

// InsertIncident persists a new incident.
func (r *SOCRepo) InsertIncident(inc soc.Incident) error {
	events, mitre, notes, timeline, err := incidentJSON(inc)
	if err != nil {
		return err
	}
	var firstEventAt, resolvedAt *string
	if !inc.FirstEventAt.IsZero() {
		t := inc.FirstEventAt.Format(time.RFC3339Nano)
		firstEventAt = &t
	}
	if inc.ResolvedAt != nil {
		t := inc.ResolvedAt.Format(time.RFC3339Nano)
		resolvedAt = &t
	}
	_, err = r.db.Exec(`INSERT INTO soc_incidents (id, tenant_id, status, severity, title, description,
 event_count, decision_chain_anchor, chain_length, correlation_rule,
 kill_chain_phase, first_event_at, created_at, updated_at,
 event_ids, mitre_mapping, playbook_applied, assigned_to, notes_json, timeline_json, resolved_at)
 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		inc.ID, inc.TenantID, inc.Status, inc.Severity, inc.Title, inc.Description,
		inc.EventCount, inc.DecisionChainAnchor, inc.ChainLength, inc.CorrelationRule,
		inc.KillChainPhase, firstEventAt, inc.CreatedAt.Format(time.RFC3339Nano), inc.UpdatedAt.Format(time.RFC3339Nano),
		events, mitre, inc.PlaybookApplied, inc.AssignedTo, notes, timeline, resolvedAt)
	return err
}

// GetIncident retrieves an incident by ID with full case management data.
func (r *SOCRepo) GetIncident(id string) (*soc.Incident, error) {
	return scanIncident(r.db.QueryRow(`SELECT id, tenant_id, status, severity, title, description, event_count, decision_chain_anchor, chain_length, correlation_rule, kill_chain_phase, playbook_applied, created_at, updated_at, resolved_at, first_event_at, event_ids, mitre_mapping, assigned_to, notes_json, timeline_json FROM soc_incidents WHERE id = ?`, id))
}

type incidentScanner interface{ Scan(...any) error }

func scanIncident(row incidentScanner) (*soc.Incident, error) {
	var inc soc.Incident
	var events, mitre, notes, timeline string
	var createdAt, updatedAt string
	var resolvedAt, firstEventAt sql.NullString
	err := row.Scan(&inc.ID, &inc.TenantID, &inc.Status, &inc.Severity, &inc.Title, &inc.Description,
		&inc.EventCount, &inc.DecisionChainAnchor, &inc.ChainLength, &inc.CorrelationRule,
		&inc.KillChainPhase, &inc.PlaybookApplied, &createdAt, &updatedAt, &resolvedAt, &firstEventAt,
		&events, &mitre, &inc.AssignedTo, &notes, &timeline)
	if err != nil {
		return nil, err
	}
	inc.CreatedAt, _ = time.Parse(time.RFC3339Nano, createdAt)
	inc.UpdatedAt, _ = time.Parse(time.RFC3339Nano, updatedAt)
	if resolvedAt.Valid && resolvedAt.String != "" {
		t, _ := time.Parse(time.RFC3339Nano, resolvedAt.String)
		inc.ResolvedAt = &t
	}
	if firstEventAt.Valid && firstEventAt.String != "" {
		inc.FirstEventAt, _ = time.Parse(time.RFC3339Nano, firstEventAt.String)
	}
	if err := decodeIncidentJSON(&inc, events, mitre, notes, timeline); err != nil {
		return nil, err
	}
	return &inc, nil
}

// ListIncidents returns full persisted incident evidence with tenant/status filters.
func (r *SOCRepo) ListIncidents(tenantID string, status string, limit int) ([]soc.Incident, error) {
	if limit <= 0 {
		limit = 50
	}
	query := `SELECT id, tenant_id, status, severity, title, description, event_count, decision_chain_anchor, chain_length, correlation_rule, kill_chain_phase, playbook_applied, created_at, updated_at, resolved_at, first_event_at, event_ids, mitre_mapping, assigned_to, notes_json, timeline_json FROM soc_incidents WHERE 1=1`
	args := []any{}
	if tenantID != "" {
		args = append(args, tenantID)
		query += " AND tenant_id = ?"
	}
	if status != "" {
		args = append(args, status)
		query += " AND status = ?"
	}
	args = append(args, limit)
	query += " ORDER BY created_at DESC LIMIT ?"
	rows, err := r.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var incidents []soc.Incident
	for rows.Next() {
		inc, err := scanIncident(rows)
		if err != nil {
			return nil, err
		}
		incidents = append(incidents, *inc)
	}
	return incidents, rows.Err()
}

// UpdateIncidentStatus updates status (and optionally resolved_at).
func (r *SOCRepo) UpdateIncidentStatus(id string, status soc.IncidentStatus) error {
	now := time.Now().Format(time.RFC3339Nano)
	if status == soc.StatusResolved || status == soc.StatusFalsePositive {
		_, err := r.db.Exec(
			`UPDATE soc_incidents SET status = ?, updated_at = ?, resolved_at = ? WHERE id = ?`,
			status, now, now, id)
		return err
	}
	_, err := r.db.Exec(
		`UPDATE soc_incidents SET status = ?, updated_at = ? WHERE id = ?`,
		status, now, id)
	return err
}

// UpdateIncident persists the full incident state including case management data.
func (r *SOCRepo) UpdateIncident(inc *soc.Incident) error {
	eventsJSON, mitreJSON, notesJSON, timelineJSON, err := incidentJSON(*inc)
	if err != nil {
		return err
	}
	var firstEventAt, resolvedAt *string
	if !inc.FirstEventAt.IsZero() {
		value := inc.FirstEventAt.Format(time.RFC3339Nano)
		firstEventAt = &value
	}
	if inc.ResolvedAt != nil {
		value := inc.ResolvedAt.Format(time.RFC3339Nano)
		resolvedAt = &value
	}
	result, err := r.db.Exec(`UPDATE soc_incidents SET status = ?, severity = ?, title = ?, description = ?, event_count = ?, assigned_to = ?, notes_json = ?, timeline_json = ?, playbook_applied = ?, kill_chain_phase = ?, updated_at = ?, resolved_at = ?, event_ids = ?, mitre_mapping = ?, decision_chain_anchor = ?, chain_length = ?, correlation_rule = ?, first_event_at = ? WHERE id = ? AND tenant_id = ?`,
		inc.Status, inc.Severity, inc.Title, inc.Description, inc.EventCount, inc.AssignedTo,
		notesJSON, timelineJSON, inc.PlaybookApplied, inc.KillChainPhase, inc.UpdatedAt.Format(time.RFC3339Nano), resolvedAt,
		eventsJSON, mitreJSON, inc.DecisionChainAnchor, inc.ChainLength, inc.CorrelationRule, firstEventAt, inc.ID, inc.TenantID)
	if err != nil {
		return err
	}
	n, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return fmt.Errorf("incident not found for owner")
	}
	return nil
}

// CountOpenIncidents returns count of non-resolved incidents.
func (r *SOCRepo) CountOpenIncidents(tenantID string) (int, error) {
	var count int
	var err error
	if tenantID != "" {
		err = r.db.QueryRow(
			"SELECT COUNT(*) FROM soc_incidents WHERE tenant_id = ? AND status IN ('OPEN', 'INVESTIGATING')",
			tenantID,
		).Scan(&count)
	} else {
		err = r.db.QueryRow(
			"SELECT COUNT(*) FROM soc_incidents WHERE status IN ('OPEN', 'INVESTIGATING')",
		).Scan(&count)
	}
	return count, err
}

// === Sensors ===

// UpsertSensor creates or updates a sensor entry.
func (r *SOCRepo) UpsertSensor(s soc.Sensor) error {
	result, err := r.db.Exec(
		`INSERT INTO soc_sensors (sensor_id, tenant_id, sensor_type, status, first_seen, last_seen,
		 event_count, missed_heartbeats, hostname, version)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		 ON CONFLICT(sensor_id) DO UPDATE SET
		   status = excluded.status,
		   last_seen = excluded.last_seen,
		   event_count = excluded.event_count,
		   missed_heartbeats = excluded.missed_heartbeats
 WHERE soc_sensors.tenant_id = excluded.tenant_id`,
		s.SensorID, s.TenantID, s.SensorType, s.Status,
		s.FirstSeen.Format(time.RFC3339Nano),
		s.LastSeen.Format(time.RFC3339Nano),
		s.EventCount, s.MissedHeartbeats, s.Hostname, s.Version,
	)
	if err != nil {
		return err
	}
	n, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return fmt.Errorf("sensor ownership conflict")
	}
	return nil
}

// GetSensor retrieves a sensor by ID.
func (r *SOCRepo) GetSensor(id string) (*soc.Sensor, error) {
	var s soc.Sensor
	var firstSeen, lastSeen string
	err := r.db.QueryRow(
		`SELECT sensor_id, tenant_id, sensor_type, status, first_seen, last_seen,
		 event_count, missed_heartbeats, hostname, version
		 FROM soc_sensors WHERE sensor_id = ?`, id,
	).Scan(&s.SensorID, &s.TenantID, &s.SensorType, &s.Status, &firstSeen, &lastSeen,
		&s.EventCount, &s.MissedHeartbeats, &s.Hostname, &s.Version)
	if err != nil {
		return nil, err
	}
	s.FirstSeen, _ = time.Parse(time.RFC3339Nano, firstSeen)
	s.LastSeen, _ = time.Parse(time.RFC3339Nano, lastSeen)
	return &s, nil
}

// ListSensors returns all registered sensors.
func (r *SOCRepo) ListSensors(tenantID string) ([]soc.Sensor, error) {
	var rows *sql.Rows
	var err error
	if tenantID != "" {
		rows, err = r.db.Query(
			`SELECT sensor_id, tenant_id, sensor_type, status, first_seen, last_seen,
			 event_count, missed_heartbeats, hostname, version
			 FROM soc_sensors WHERE tenant_id = ? ORDER BY last_seen DESC`, tenantID)
	} else {
		rows, err = r.db.Query(
			`SELECT sensor_id, tenant_id, sensor_type, status, first_seen, last_seen,
			 event_count, missed_heartbeats, hostname, version
			 FROM soc_sensors ORDER BY last_seen DESC`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var sensors []soc.Sensor
	for rows.Next() {
		var s soc.Sensor
		var firstSeen, lastSeen string
		err := rows.Scan(&s.SensorID, &s.TenantID, &s.SensorType, &s.Status,
			&firstSeen, &lastSeen, &s.EventCount, &s.MissedHeartbeats,
			&s.Hostname, &s.Version)
		if err != nil {
			return nil, err
		}
		s.FirstSeen, _ = time.Parse(time.RFC3339Nano, firstSeen)
		s.LastSeen, _ = time.Parse(time.RFC3339Nano, lastSeen)
		sensors = append(sensors, s)
	}
	return sensors, rows.Err()
}

// CountSensorsByStatus returns sensor count grouped by status.
func (r *SOCRepo) CountSensorsByStatus(tenantID string) (map[soc.SensorStatus]int, error) {
	var rows *sql.Rows
	var err error
	if tenantID != "" {
		rows, err = r.db.Query("SELECT status, COUNT(*) FROM soc_sensors WHERE tenant_id = ? GROUP BY status", tenantID)
	} else {
		rows, err = r.db.Query("SELECT status, COUNT(*) FROM soc_sensors GROUP BY status")
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make(map[soc.SensorStatus]int)
	for rows.Next() {
		var status soc.SensorStatus
		var count int
		if err := rows.Scan(&status, &count); err != nil {
			return nil, err
		}
		result[status] = count
	}
	return result, rows.Err()
}

// PurgeExpiredEvents deletes events older than the retention period.
// Returns the number of deleted events.
func (r *SOCRepo) PurgeExpiredEvents(retentionDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -retentionDays).Format(time.RFC3339)
	result, err := r.db.Exec("DELETE FROM soc_events WHERE timestamp < ?", cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge events: %w", err)
	}
	return result.RowsAffected()
}

// PurgeExpiredIncidents deletes resolved incidents older than the retention period.
// Only resolved incidents are purged; open/investigating incidents are preserved.
// Returns the number of deleted incidents.
func (r *SOCRepo) PurgeExpiredIncidents(retentionDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -retentionDays).Format(time.RFC3339)
	result, err := r.db.Exec(
		"DELETE FROM soc_incidents WHERE status = ? AND created_at < ?",
		soc.StatusResolved, cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge incidents: %w", err)
	}
	return result.RowsAffected()
}

// PurgeStaleIncidents deletes incidents older than maxAgeDays REGARDLESS of
// status (Review 14.06 round-5) — never-resolved incidents would otherwise grow
// unbounded since PurgeExpiredIncidents only removes RESOLVED ones.
func (r *SOCRepo) PurgeStaleIncidents(maxAgeDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -maxAgeDays).Format(time.RFC3339)
	result, err := r.db.Exec("DELETE FROM soc_incidents WHERE created_at < ?", cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge stale incidents: %w", err)
	}
	return result.RowsAffected()
}

// PurgeStaleSensors deletes sensors not seen within staleDays (Review 14.06
// round-5) — sensor rows (incl. per-tenant "gateway:<tenant>") were never purged.
func (r *SOCRepo) PurgeStaleSensors(staleDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -staleDays).Format(time.RFC3339)
	result, err := r.db.Exec("DELETE FROM soc_sensors WHERE last_seen < ?", cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge stale sensors: %w", err)
	}
	return result.RowsAffected()
}

// DeleteByTenant transactionally erases ALL of a tenant's SOC data for a GDPR
// Art.17 right-to-erasure request (Review 14.06 round-5). Idempotent. An empty
// tenantID is refused so erasure can never run store-wide. The table list is a
// fixed constant (no injection); tenantID is parameterized.
func (r *SOCRepo) DeleteByTenant(tenantID string) (int64, error) {
	if tenantID == "" {
		return 0, fmt.Errorf("delete by tenant: empty tenant_id refused")
	}
	tx, err := r.db.SqlDB().Begin()
	if err != nil {
		return 0, fmt.Errorf("delete by tenant: begin: %w", err)
	}
	var total int64
	for _, table := range []string{"soc_events", "soc_incidents", "soc_sensors"} {
		res, err := tx.Exec("DELETE FROM "+table+" WHERE tenant_id = ?", tenantID)
		if err != nil {
			_ = tx.Rollback()
			return 0, fmt.Errorf("delete by tenant %s: %w", table, err)
		}
		if n, raErr := res.RowsAffected(); raErr == nil {
			total += n
		}
	}
	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("delete by tenant: commit: %w", err)
	}
	return total, nil
}

// === Waitlist (pre-signup interest; deletable PII store) ===

// AddWaitlistEntry persists a registration-interest record.
func (r *SOCRepo) AddWaitlistEntry(e soc.WaitlistEntry) error {
	_, err := r.db.Exec(
		`INSERT INTO soc_waitlist (id, email, company, use_case, created_at)
		 VALUES (?, ?, ?, ?, ?)`,
		e.ID, e.Email, e.Company, e.UseCase, e.CreatedAt.Format(time.RFC3339Nano),
	)
	return err
}

// ListWaitlist returns entries newest-first (limit ≤ 0 ⇒ default 1000).
func (r *SOCRepo) ListWaitlist(limit int) ([]soc.WaitlistEntry, error) {
	if limit <= 0 {
		limit = 1000
	}
	rows, err := r.db.Query(
		`SELECT id, email, company, use_case, created_at
		 FROM soc_waitlist ORDER BY created_at DESC LIMIT ?`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []soc.WaitlistEntry
	for rows.Next() {
		var e soc.WaitlistEntry
		var createdAt string
		if err := rows.Scan(&e.ID, &e.Email, &e.Company, &e.UseCase, &createdAt); err != nil {
			return nil, err
		}
		e.CreatedAt, _ = time.Parse(time.RFC3339Nano, createdAt)
		out = append(out, e)
	}
	return out, rows.Err()
}

// DeleteWaitlistByEmail erases all entries for an email (GDPR Art.17 erasure path).
// Refuses an empty email so it can never wipe the whole table.
func (r *SOCRepo) DeleteWaitlistByEmail(email string) (int64, error) {
	if email == "" {
		return 0, fmt.Errorf("delete waitlist: empty email refused")
	}
	res, err := r.db.Exec("DELETE FROM soc_waitlist WHERE email = ?", email)
	if err != nil {
		return 0, fmt.Errorf("delete waitlist by email: %w", err)
	}
	return res.RowsAffected()
}
