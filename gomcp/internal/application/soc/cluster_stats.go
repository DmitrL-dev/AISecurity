package soc

import (
	"errors"
	"math"
	"strings"
)

// ErrClusterTenantRequired prevents an absent tenant from becoming a global read.
var ErrClusterTenantRequired = errors.New("tenant scope required for cluster statistics")

// TenantClusterStats describes retained in-memory clusters, not lifetime ingest.
// Global engine mode and lifetime counters deliberately have no fields here.
type TenantClusterStats struct {
	Enabled         bool    `json:"enabled"`
	Scope           string  `json:"scope"`
	StatisticsBasis string  `json:"statistics_basis"`
	TotalClusters   int     `json:"total_clusters"`
	TotalEvents     int     `json:"total_events"`
	AvgClusterSize  float64 `json:"avg_cluster_size"`
	MaxClusterSize  int     `json:"max_cluster_size"`
}

// ClusterStatsForTenant aggregates one immutable snapshot for an exact tenant.
// TotalEvents counts retained event references; it is not events_processed.
func (s *Service) ClusterStatsForTenant(tenantID string) (TenantClusterStats, error) {
	stats := TenantClusterStats{Scope: "tenant", StatisticsBasis: "retained_clusters"}
	if strings.TrimSpace(tenantID) == "" {
		return stats, ErrClusterTenantRequired
	}
	if s.clusterEngine == nil {
		return stats, nil
	}
	stats.Enabled = true
	for _, cluster := range s.clusterEngine.Clusters() {
		if cluster.TenantID != tenantID {
			continue
		}
		size := len(cluster.Events)
		stats.TotalClusters++
		stats.TotalEvents += size
		if size > stats.MaxClusterSize {
			stats.MaxClusterSize = size
		}
	}
	if stats.TotalClusters != 0 {
		stats.AvgClusterSize = math.Round(float64(stats.TotalEvents)/float64(stats.TotalClusters)*100) / 100
	}
	return stats, nil
}
