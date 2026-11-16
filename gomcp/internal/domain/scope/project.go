package scope

import "time"

const (
	ProjectStatusActive   = "active"
	ProjectStatusArchived = "archived"
)

// Project is the tenant-local registry record for one RLM project.
type Project struct {
	TenantID       string     `json:"tenant_id"`
	ProjectID      string     `json:"project_id"`
	Name           string     `json:"name"`
	Status         string     `json:"status"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
	ArchivedAt     *time.Time `json:"archived_at,omitempty"`
	LastAccessedAt *time.Time `json:"last_accessed_at,omitempty"`

	FactCount      int        `json:"fact_count,omitempty"`
	GeneCount      int        `json:"gene_count,omitempty"`
	StaleCount     int        `json:"stale_count,omitempty"`
	ArchivedCount  int        `json:"archived_count,omitempty"`
	DomainCount    int        `json:"domain_count,omitempty"`
	WithEmbeddings int        `json:"with_embeddings,omitempty"`
	LastFactAt     *time.Time `json:"last_fact_at,omitempty"`
}

// ProjectStats is a richer per-project operational snapshot.
type ProjectStats struct {
	Project        *Project   `json:"project"`
	TotalFacts     int        `json:"total_facts"`
	GeneCount      int        `json:"gene_count"`
	StaleCount     int        `json:"stale_count"`
	ArchivedCount  int        `json:"archived_count"`
	DomainCount    int        `json:"domain_count"`
	WithEmbeddings int        `json:"with_embeddings"`
	LastFactAt     *time.Time `json:"last_fact_at,omitempty"`
}
