package soc

import "time"

// SOCRepository defines the persistence contract for the SOC subsystem.
// Implementations: sqlite.SOCRepo (default), postgres.SOCRepo (production).
//
// All methods that list or count data accept a tenantID parameter for multi-tenant
// isolation. Pass "" (empty) for backward compatibility (returns all tenants).
type SOCRepository interface {
	// ── Events ──────────────────────────────────────────────
	InsertEvent(e SOCEvent) error
	GetEvent(id string) (*SOCEvent, error)
	ListEvents(tenantID string, limit int) ([]SOCEvent, error)
	ListEventsByCategory(tenantID string, category string, limit int) ([]SOCEvent, error)
	EventExistsByHash(tenantID, contentHash string) (bool, error) // §5.2 dedup
	CountEvents(tenantID string) (int, error)
	CountEventsSince(tenantID string, since time.Time) (int, error)

	// ── Incidents ───────────────────────────────────────────
	InsertIncident(inc Incident) error
	GetIncident(id string) (*Incident, error)
	ListIncidents(tenantID string, status string, limit int) ([]Incident, error)
	UpdateIncidentStatus(id string, status IncidentStatus) error
	UpdateIncident(inc *Incident) error
	CountOpenIncidents(tenantID string) (int, error)

	// ── Sensors ─────────────────────────────────────────────
	UpsertSensor(s Sensor) error
	ListSensors(tenantID string) ([]Sensor, error)
	CountSensorsByStatus(tenantID string) (map[SensorStatus]int, error)

	// ── Retention ───────────────────────────────────────────
	PurgeExpiredEvents(retentionDays int) (int64, error)
	PurgeExpiredIncidents(retentionDays int) (int64, error)
	// PurgeStaleIncidents deletes incidents older than maxAgeDays REGARDLESS of
	// status (Review 14.06 round-5): PurgeExpiredIncidents only removes RESOLVED
	// ones, so never-resolved incidents grew unbounded. maxAgeDays should exceed
	// the resolved-retention window.
	PurgeStaleIncidents(maxAgeDays int) (int64, error)
	// PurgeStaleSensors deletes sensors not seen within staleDays (Review 14.06
	// round-5): sensor rows (incl. per-tenant "gateway:<tenant>") were never
	// purged, growing unbounded and leaving GDPR residual.
	PurgeStaleSensors(staleDays int) (int64, error)

	// ── Waitlist (pre-signup interest) ──────────────────────
	// AddWaitlistEntry persists a registration-interest record. Cleartext PII lives
	// here (a DELETABLE table), never in the immutable audit chain.
	AddWaitlistEntry(e WaitlistEntry) error
	// ListWaitlist returns entries newest-first (limit ≤ 0 ⇒ a default cap).
	ListWaitlist(limit int) ([]WaitlistEntry, error)
	// DeleteWaitlistByEmail erases all entries for an email (GDPR Art.17 erasure
	// path for a waitlist subject). Returns rows deleted; refuses an empty email.
	DeleteWaitlistByEmail(email string) (int64, error)

	// ── GDPR erasure ────────────────────────────────────────
	// DeleteByTenant transactionally removes ALL of a tenant's persisted SOC data
	// (events + incidents + sensors) for a right-to-erasure request (GDPR Art.17).
	// Idempotent: returns the number of rows deleted (0 if the tenant had none).
	// An empty tenantID is rejected — erasure must never run store-wide.
	DeleteByTenant(tenantID string) (int64, error)
}
