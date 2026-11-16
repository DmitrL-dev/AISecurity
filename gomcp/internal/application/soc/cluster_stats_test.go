package soc

import (
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

func clusterStatsFixture() *Service {
	cfg := domsoc.DefaultClusterConfig()
	cfg.MinEventsForEmbedding = 1000
	cfg.ColdStartTimeout = time.Hour
	cfg.MaxClusterSize = 100
	svc := &Service{clusterEngine: domsoc.NewClusterEngine(cfg)}
	for _, seed := range []struct {
		tenant, category string
		count            int
	}{{"tenant-a", "shared", 2}, {"tenant-a", "second", 1}, {"tenant-b", "shared", 4}, {"", "shared", 1}} {
		for i := 0; i < seed.count; i++ {
			event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, seed.category, "synthetic")
			event.TenantID = seed.tenant
			svc.clusterEngine.AddEvent(event)
		}
	}
	return svc
}

func TestTenantClusterStatsRetainedCounts(t *testing.T) {
	svc := clusterStatsFixture()
	a, err := svc.ClusterStatsForTenant("tenant-a")
	require.NoError(t, err)
	require.Equal(t, TenantClusterStats{true, "tenant", "retained_clusters", 2, 3, 1.5, 2}, a)
	b, err := svc.ClusterStatsForTenant("tenant-b")
	require.NoError(t, err)
	require.Equal(t, TenantClusterStats{true, "tenant", "retained_clusters", 1, 4, 4, 4}, b)
	empty, err := svc.ClusterStatsForTenant("tenant-empty")
	require.NoError(t, err)
	require.Equal(t, TenantClusterStats{Enabled: true, Scope: "tenant", StatisticsBasis: "retained_clusters"}, empty)

	// Mutating a copied cluster snapshot cannot change the engine's owned rows.
	for _, c := range svc.clusterEngine.Clusters() {
		c.TenantID = "tenant-a"
		c.Events = append(c.Events, "synthetic-copy-only")
	}
	unchanged, err := svc.ClusterStatsForTenant("tenant-a")
	require.NoError(t, err)
	require.Equal(t, a, unchanged)

	// Only this synthetic in-memory cluster map is changed; no erasure service runs.
	svc.clusterEngine.DeleteByTenant("tenant-a")
	after, err := svc.ClusterStatsForTenant("tenant-a")
	require.NoError(t, err)
	require.Equal(t, empty, after)
	other, err := svc.ClusterStatsForTenant("tenant-b")
	require.NoError(t, err)
	require.Equal(t, b, other)
	require.Equal(t, 8, svc.ClusterStats()["events_processed"])
	require.Equal(t, 5, svc.ClusterStats()["total_events"])
}

func TestTenantClusterStatsRequiresTenantScope(t *testing.T) {
	svc := clusterStatsFixture()
	for _, tenant := range []string{"", " \t\n"} {
		_, err := svc.ClusterStatsForTenant(tenant)
		require.ErrorIs(t, err, ErrClusterTenantRequired)
	}
}

func TestTenantClusterStatsDisabledEngine(t *testing.T) {
	svc := &Service{}
	stats, err := svc.ClusterStatsForTenant("tenant-a")
	require.NoError(t, err)
	require.Equal(t, TenantClusterStats{Scope: "tenant", StatisticsBasis: "retained_clusters"}, stats)
	_, err = svc.ClusterStatsForTenant("")
	require.ErrorIs(t, err, ErrClusterTenantRequired)
}

func TestTenantClusterStatsConcurrentSnapshots(t *testing.T) {
	cfg := domsoc.DefaultClusterConfig()
	cfg.MinEventsForEmbedding = 1000
	cfg.ColdStartTimeout = time.Hour
	cfg.MaxClusterSize = 100
	svc := &Service{clusterEngine: domsoc.NewClusterEngine(cfg)}
	add := func(tenant string) {
		event := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "shared", "synthetic")
		event.TenantID = tenant
		svc.clusterEngine.AddEvent(event)
	}
	add("tenant-a")
	advance := make(chan struct{})
	progress := make(chan struct{}, 1)
	finished := make(chan struct{})
	go func() {
		defer close(finished)
		for range advance {
			add("tenant-a")
			add("tenant-b")
			progress <- struct{}{}
		}
	}()
	defer func() { close(advance); <-finished }()
	for i := 0; i < 20; i++ {
		advance <- struct{}{}
		stats, err := svc.ClusterStatsForTenant("tenant-a")
		require.NoError(t, err)
		require.Equal(t, 1, stats.TotalClusters)
		require.GreaterOrEqual(t, stats.TotalEvents, i+1)
		require.LessOrEqual(t, stats.TotalEvents, i+2)
		require.Equal(t, stats.TotalEvents, stats.MaxClusterSize)
		require.Equal(t, float64(stats.TotalEvents), stats.AvgClusterSize)
		<-progress
	}
}
