package postgres

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/soc"
)

// SOCRepo provides PostgreSQL persistence for SOC events, incidents, and sensors.
// Implements domain/soc.SOCRepository.
type SOCRepo struct {
	db *DB
}

// NewSOCRepo creates a PostgreSQL-backed SOC repository.
// Unlike SQLite, tables are created via goose migrations (not inline DDL).
func NewSOCRepo(db *DB) *SOCRepo {
	return &SOCRepo{db: db}
}

// === Events ===

// InsertEvent persists a SOC event.
func (r *SOCRepo) InsertEvent(e soc.SOCEvent) error {
	metaJSON, err := json.Marshal(e.Metadata)
	if err != nil {
		return fmt.Errorf("encode event metadata: %w", err)
	}
	if e.Metadata == nil {
		metaJSON = []byte("{}")
	}
	_, err = r.db.Pool().Exec(
		`INSERT INTO soc_events (id, tenant_id, source, sensor_id, severity, category, subcategory,
		 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)`,
		e.ID, e.TenantID, e.Source, e.SensorID, e.Severity, e.Category, e.Subcategory,
		e.Confidence, e.Description, e.SessionID, e.ContentHash, e.DecisionHash, e.Verdict,
		e.Timestamp, string(metaJSON),
	)
	return err
}

// EventExistsByHash checks if an event with the given content hash already exists (§5.2 dedup).
func (r *SOCRepo) EventExistsByHash(tenantID, contentHash string) (bool, error) {
	if contentHash == "" {
		return false, nil
	}
	var count int
	err := r.db.Pool().QueryRow(
		"SELECT COUNT(*) FROM soc_events WHERE tenant_id = $1 AND content_hash = $2", tenantID, contentHash,
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
		rows, err = r.db.Pool().Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events WHERE tenant_id = $1 ORDER BY timestamp DESC LIMIT $2`, tenantID, limit)
	} else {
		rows, err = r.db.Pool().Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events ORDER BY timestamp DESC LIMIT $1`, limit)
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
		rows, err = r.db.Pool().Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events WHERE tenant_id = $1 AND category = $2 ORDER BY timestamp DESC LIMIT $3`,
			tenantID, category, limit)
	} else {
		rows, err = r.db.Pool().Query(
			`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
			 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
			 FROM soc_events WHERE category = $1 ORDER BY timestamp DESC LIMIT $2`,
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
		err = r.db.Pool().QueryRow("SELECT COUNT(*) FROM soc_events WHERE tenant_id = $1", tenantID).Scan(&count)
	} else {
		err = r.db.Pool().QueryRow("SELECT COUNT(*) FROM soc_events").Scan(&count)
	}
	return count, err
}

// GetEvent retrieves a single event by ID.
func (r *SOCRepo) GetEvent(id string) (*soc.SOCEvent, error) {
	var e soc.SOCEvent
	var metaJSON string
	// Review 13.06 (audit): select/scan tenant_id so callers that scope a
	// single event by tenant (IDOR guard) see the real owner instead of "".
	// Mirrors the GetIncident fix in this file.
	err := r.db.Pool().QueryRow(
		`SELECT id, tenant_id, source, sensor_id, severity, category, subcategory,
		 confidence, description, session_id, content_hash, decision_hash, verdict, timestamp, metadata
		 FROM soc_events WHERE id = $1`, id,
	).Scan(&e.ID, &e.TenantID, &e.Source, &e.SensorID, &e.Severity,
		&e.Category, &e.Subcategory, &e.Confidence, &e.Description,
		&e.SessionID, &e.ContentHash, &e.DecisionHash, &e.Verdict, &e.Timestamp, &metaJSON)
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal([]byte(metaJSON), &e.Metadata); err != nil {
		return nil, fmt.Errorf("decode event metadata: %w", err)
	}
	return &e, nil
}

// CountEventsSince returns events in the given time window.
func (r *SOCRepo) CountEventsSince(tenantID string, since time.Time) (int, error) {
	var count int
	var err error
	if tenantID != "" {
		err = r.db.Pool().QueryRow(
			"SELECT COUNT(*) FROM soc_events WHERE tenant_id = $1 AND timestamp >= $2", tenantID, since,
		).Scan(&count)
	} else {
		err = r.db.Pool().QueryRow(
			"SELECT COUNT(*) FROM soc_events WHERE timestamp >= $1", since,
		).Scan(&count)
	}
	return count, err
}

func scanEvents(rows *sql.Rows) ([]soc.SOCEvent, error) {
	var events []soc.SOCEvent
	for rows.Next() {
		var e soc.SOCEvent
		var metaJSON string
		err := rows.Scan(&e.ID, &e.TenantID, &e.Source, &e.SensorID, &e.Severity,
			&e.Category, &e.Subcategory, &e.Confidence, &e.Description,
			&e.SessionID, &e.ContentHash, &e.DecisionHash, &e.Verdict, &e.Timestamp, &metaJSON)
		if err != nil {
			return nil, err
		}
		if err := json.Unmarshal([]byte(metaJSON), &e.Metadata); err != nil {
			return nil, fmt.Errorf("decode event metadata: %w", err)
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
	var firstEventAt *time.Time
	if !inc.FirstEventAt.IsZero() {
		t := inc.FirstEventAt
		firstEventAt = &t
	}
	_, err = r.db.Pool().Exec(`INSERT INTO soc_incidents (id, tenant_id, status, severity, title, description,
 event_count, decision_chain_anchor, chain_length, correlation_rule,
 kill_chain_phase, first_event_at, created_at, updated_at,
 event_ids, mitre_mapping, playbook_applied, assigned_to, notes_json, timeline_json, resolved_at)
 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)`,
		inc.ID, inc.TenantID, inc.Status, inc.Severity, inc.Title, inc.Description,
		inc.EventCount, inc.DecisionChainAnchor, inc.ChainLength, inc.CorrelationRule,
		inc.KillChainPhase, firstEventAt, inc.CreatedAt, inc.UpdatedAt,
		events, mitre, inc.PlaybookApplied, inc.AssignedTo, notes, timeline, inc.ResolvedAt)
	return err
}

// GetIncident retrieves an incident by ID.
func (r *SOCRepo) GetIncident(id string) (*soc.Incident, error) {
	return scanIncident(r.db.Pool().QueryRow(`SELECT id, tenant_id, status, severity, title, description, event_count, decision_chain_anchor, chain_length, correlation_rule, kill_chain_phase, playbook_applied, created_at, updated_at, resolved_at, first_event_at, event_ids, mitre_mapping, assigned_to, notes_json, timeline_json FROM soc_incidents WHERE id = $1`, id))
}

type incidentScanner interface{ Scan(...any) error }

func scanIncident(row incidentScanner) (*soc.Incident, error) {
	var inc soc.Incident
	var events, mitre, notes, timeline string
	var resolvedAt, firstEventAt sql.NullTime
	err := row.Scan(&inc.ID, &inc.TenantID, &inc.Status, &inc.Severity, &inc.Title, &inc.Description,
		&inc.EventCount, &inc.DecisionChainAnchor, &inc.ChainLength, &inc.CorrelationRule,
		&inc.KillChainPhase, &inc.PlaybookApplied, &inc.CreatedAt, &inc.UpdatedAt, &resolvedAt, &firstEventAt,
		&events, &mitre, &inc.AssignedTo, &notes, &timeline)
	if err != nil {
		return nil, err
	}
	if resolvedAt.Valid {
		inc.ResolvedAt = &resolvedAt.Time
	}
	if firstEventAt.Valid {
		inc.FirstEventAt = firstEventAt.Time
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
		query += fmt.Sprintf(" AND tenant_id = $%d", len(args))
	}
	if status != "" {
		args = append(args, status)
		query += fmt.Sprintf(" AND status = $%d", len(args))
	}
	args = append(args, limit)
	query += fmt.Sprintf(" ORDER BY created_at DESC LIMIT $%d", len(args))
	rows, err := r.db.Pool().Query(query, args...)
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
	now := time.Now()
	if status == soc.StatusResolved || status == soc.StatusFalsePositive {
		_, err := r.db.Pool().Exec(
			`UPDATE soc_incidents SET status = $1, updated_at = $2, resolved_at = $3 WHERE id = $4`,
			status, now, now, id)
		return err
	}
	_, err := r.db.Pool().Exec(
		`UPDATE soc_incidents SET status = $1, updated_at = $2 WHERE id = $3`,
		status, now, id)
	return err
}

// CountOpenIncidents returns count of non-resolved incidents.
func (r *SOCRepo) CountOpenIncidents(tenantID string) (int, error) {
	var count int
	var err error
	if tenantID != "" {
		err = r.db.Pool().QueryRow(
			"SELECT COUNT(*) FROM soc_incidents WHERE tenant_id = $1 AND status IN ('OPEN', 'INVESTIGATING')",
			tenantID,
		).Scan(&count)
	} else {
		err = r.db.Pool().QueryRow(
			"SELECT COUNT(*) FROM soc_incidents WHERE status IN ('OPEN', 'INVESTIGATING')",
		).Scan(&count)
	}
	return count, err
}

// UpdateIncident persists full incident state (case management).
func (r *SOCRepo) UpdateIncident(inc *soc.Incident) error {
	eventsJSON, mitreJSON, notesJSON, timelineJSON, err := incidentJSON(*inc)
	if err != nil {
		return err
	}
	var firstEventAt *time.Time
	if !inc.FirstEventAt.IsZero() {
		value := inc.FirstEventAt
		firstEventAt = &value
	}
	result, err := r.db.Pool().Exec(`UPDATE soc_incidents SET status = $1, severity = $2, title = $3, description = $4, event_count = $5, assigned_to = $6, notes_json = $7, timeline_json = $8, playbook_applied = $9, kill_chain_phase = $10, updated_at = $11, resolved_at = $12, event_ids = $13, mitre_mapping = $14, decision_chain_anchor = $15, chain_length = $16, correlation_rule = $17, first_event_at = $18 WHERE id = $19 AND tenant_id = $20`,
		inc.Status, inc.Severity, inc.Title, inc.Description, inc.EventCount, inc.AssignedTo,
		notesJSON, timelineJSON, inc.PlaybookApplied, inc.KillChainPhase, inc.UpdatedAt, inc.ResolvedAt,
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

// === Sensors ===

// UpsertSensor creates or updates a sensor entry.
func (r *SOCRepo) UpsertSensor(s soc.Sensor) error {
	result, err := r.db.Pool().Exec(
		`INSERT INTO soc_sensors (sensor_id, tenant_id, sensor_type, status, first_seen, last_seen,
		 event_count, missed_heartbeats, hostname, version)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		 ON CONFLICT(sensor_id) DO UPDATE SET
		   status = EXCLUDED.status,
		   last_seen = EXCLUDED.last_seen,
		   event_count = EXCLUDED.event_count,
		   missed_heartbeats = EXCLUDED.missed_heartbeats
 WHERE soc_sensors.tenant_id = EXCLUDED.tenant_id`,
		s.SensorID, s.TenantID, s.SensorType, s.Status,
		s.FirstSeen, s.LastSeen,
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
	err := r.db.Pool().QueryRow(
		`SELECT sensor_id, tenant_id, sensor_type, status, first_seen, last_seen,
		 event_count, missed_heartbeats, hostname, version
		 FROM soc_sensors WHERE sensor_id = $1`, id,
	).Scan(&s.SensorID, &s.TenantID, &s.SensorType, &s.Status, &s.FirstSeen, &s.LastSeen,
		&s.EventCount, &s.MissedHeartbeats, &s.Hostname, &s.Version)
	if err != nil {
		return nil, err
	}
	return &s, nil
}

// ListSensors returns all registered sensors.
func (r *SOCRepo) ListSensors(tenantID string) ([]soc.Sensor, error) {
	var rows *sql.Rows
	var err error
	if tenantID != "" {
		rows, err = r.db.Pool().Query(
			`SELECT sensor_id, tenant_id, sensor_type, status, first_seen, last_seen,
			 event_count, missed_heartbeats, hostname, version
			 FROM soc_sensors WHERE tenant_id = $1 ORDER BY last_seen DESC`, tenantID)
	} else {
		rows, err = r.db.Pool().Query(
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
		err := rows.Scan(&s.SensorID, &s.TenantID, &s.SensorType, &s.Status,
			&s.FirstSeen, &s.LastSeen, &s.EventCount, &s.MissedHeartbeats,
			&s.Hostname, &s.Version)
		if err != nil {
			return nil, err
		}
		sensors = append(sensors, s)
	}
	return sensors, rows.Err()
}

// CountSensorsByStatus returns sensor count grouped by status.
func (r *SOCRepo) CountSensorsByStatus(tenantID string) (map[soc.SensorStatus]int, error) {
	var rows *sql.Rows
	var err error
	if tenantID != "" {
		rows, err = r.db.Pool().Query("SELECT status, COUNT(*) FROM soc_sensors WHERE tenant_id = $1 GROUP BY status", tenantID)
	} else {
		rows, err = r.db.Pool().Query("SELECT status, COUNT(*) FROM soc_sensors GROUP BY status")
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
func (r *SOCRepo) PurgeExpiredEvents(retentionDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -retentionDays)
	result, err := r.db.Pool().Exec("DELETE FROM soc_events WHERE timestamp < $1", cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge events: %w", err)
	}
	return result.RowsAffected()
}

// PurgeExpiredIncidents deletes resolved incidents older than the retention period.
func (r *SOCRepo) PurgeExpiredIncidents(retentionDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -retentionDays)
	result, err := r.db.Pool().Exec(
		"DELETE FROM soc_incidents WHERE status = $1 AND created_at < $2",
		soc.StatusResolved, cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge incidents: %w", err)
	}
	return result.RowsAffected()
}

// PurgeStaleIncidents deletes incidents older than maxAgeDays regardless of
// status (Review 14.06 round-5: never-resolved incidents grew unbounded).
func (r *SOCRepo) PurgeStaleIncidents(maxAgeDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -maxAgeDays)
	result, err := r.db.Pool().Exec("DELETE FROM soc_incidents WHERE created_at < $1", cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge stale incidents: %w", err)
	}
	return result.RowsAffected()
}

// PurgeStaleSensors deletes sensors not seen within staleDays (Review 14.06
// round-5: sensor rows were never purged → unbounded + GDPR residual).
func (r *SOCRepo) PurgeStaleSensors(staleDays int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -staleDays)
	result, err := r.db.Pool().Exec("DELETE FROM soc_sensors WHERE last_seen < $1", cutoff)
	if err != nil {
		return 0, fmt.Errorf("purge stale sensors: %w", err)
	}
	return result.RowsAffected()
}

// DeleteByTenant transactionally erases ALL of a tenant's SOC data for a GDPR
// Art.17 right-to-erasure request (Review 14.06 round-5). Idempotent. An empty
// tenantID is refused so erasure can never run store-wide.
func (r *SOCRepo) DeleteByTenant(tenantID string) (int64, error) {
	if tenantID == "" {
		return 0, fmt.Errorf("delete by tenant: empty tenant_id refused")
	}
	tx, err := r.db.Pool().Begin()
	if err != nil {
		return 0, fmt.Errorf("delete by tenant: begin: %w", err)
	}
	var total int64
	for _, table := range []string{"soc_events", "soc_incidents", "soc_sensors"} {
		res, err := tx.Exec("DELETE FROM "+table+" WHERE tenant_id = $1", tenantID)
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
	_, err := r.db.Pool().Exec(
		`INSERT INTO soc_waitlist (id, email, company, use_case, created_at)
		 VALUES ($1, $2, $3, $4, $5)`,
		e.ID, e.Email, e.Company, e.UseCase, e.CreatedAt,
	)
	return err
}

// ListWaitlist returns entries newest-first (limit ≤ 0 ⇒ default 1000).
func (r *SOCRepo) ListWaitlist(limit int) ([]soc.WaitlistEntry, error) {
	if limit <= 0 {
		limit = 1000
	}
	rows, err := r.db.Pool().Query(
		`SELECT id, email, company, use_case, created_at
		 FROM soc_waitlist ORDER BY created_at DESC LIMIT $1`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []soc.WaitlistEntry
	for rows.Next() {
		var e soc.WaitlistEntry
		if err := rows.Scan(&e.ID, &e.Email, &e.Company, &e.UseCase, &e.CreatedAt); err != nil {
			return nil, err
		}
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
	res, err := r.db.Pool().Exec("DELETE FROM soc_waitlist WHERE email = $1", email)
	if err != nil {
		return 0, fmt.Errorf("delete waitlist by email: %w", err)
	}
	return res.RowsAffected()
}

// Compile-time interface compliance check.
var _ soc.SOCRepository = (*SOCRepo)(nil)
