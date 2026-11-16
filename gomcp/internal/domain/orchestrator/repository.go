package orchestrator

import "time"

// Repository persists orchestrator training samples. Both the SQLite and
// PostgreSQL infrastructure repos implement it. Every query is tenant-scoped
// (mirrors the SOC repo's per-tenant isolation) — callers pass the caller's
// tenant and a non-empty tenant filter is REQUIRED for export/label paths so a
// sample can never leak across tenants.
type Repository interface {
	// Insert persists one captured sample. Best-effort: callers fire this async
	// off the scan path and must not surface its error to the scan response.
	Insert(s Sample) error

	// AttachLabel writes the supervised label onto every UNLABELED sample for the
	// given tenant whose timestamp falls in [from, to]. Returns the number of
	// rows updated. The join is by tenant + time window (see the handler doc for
	// why this is the available granularity). An empty tenantID is refused so a
	// disposition can never relabel store-wide.
	AttachLabel(tenantID string, from, to time.Time, label Label, source string) (int64, error)

	// ExportLabeled returns LABELED samples for the tenant (newest first, bounded
	// by limit). An empty tenantID is refused. When onlyLabeled is false the
	// platform-admin export may include unlabeled rows (for corpus inspection);
	// the default path passes true.
	ExportLabeled(tenantID string, limit int, onlyLabeled bool) ([]Sample, error)

	// CountSamples returns (total, labeled) counts for the tenant, for the export
	// summary + tests.
	CountSamples(tenantID string) (total int64, labeled int64, err error)

	// PurgeExpired deletes samples older than retentionDays. Returns rows deleted.
	// Honors the same retention discipline as SOC events.
	PurgeExpired(retentionDays int) (int64, error)

	// DeleteByTenant erases all of a tenant's samples (GDPR Art.17). Refuses an
	// empty tenantID.
	DeleteByTenant(tenantID string) (int64, error)
}
