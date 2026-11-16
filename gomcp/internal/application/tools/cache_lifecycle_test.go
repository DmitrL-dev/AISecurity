package tools

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/cache"
)

type faultingL0Cache struct{ memory.HotCache }

func (c faultingL0Cache) InvalidateFact(context.Context, string) error {
	return errors.New("synthetic invalidation error")
}

func TestL0ReadsSurviveInvalidationFailureWithoutMisreportingWrite(t *testing.T) {
	base := newTestFactService(t)
	ctx := context.Background()
	hot, err := cache.NewBoltCache(filepath.Join(t.TempDir(), "cache.db"))
	require.NoError(t, err)
	t.Cleanup(func() { _ = hot.Close() })
	a, err := base.AddFact(ctx, AddFactParams{Content: "lifecycle active A", Level: 0})
	require.NoError(t, err)
	require.NoError(t, hot.WarmUp(ctx, []*memory.Fact{a}))
	svc := NewFactService(base.Store(), faultingL0Cache{hot})
	b, err := svc.AddFact(ctx, AddFactParams{Content: "lifecycle active B", Level: 0})
	require.ErrorContains(t, err, "stored but cache invalidation failed")
	require.NotNil(t, b)
	facts, err := svc.GetL0Facts(ctx)
	require.NoError(t, err)
	require.Len(t, facts, 2)
}

func TestL0ReadsIgnoreLateStaleWarmUp(t *testing.T) {
	base := newTestFactService(t)
	ctx := context.Background()
	hot, err := cache.NewBoltCache(filepath.Join(t.TempDir(), "cache.db"))
	require.NoError(t, err)
	t.Cleanup(func() { _ = hot.Close() })
	svc := NewFactService(base.Store(), hot)
	a, err := svc.AddFact(ctx, AddFactParams{Content: "late warmup A", Level: 0})
	require.NoError(t, err)
	ready := make(chan struct{})
	release := make(chan struct{})
	finished := make(chan error, 1)
	go func() { close(ready); <-release; finished <- hot.WarmUp(ctx, []*memory.Fact{a}) }()
	<-ready
	_, err = svc.AddFact(ctx, AddFactParams{Content: "late warmup B", Level: 0})
	require.NoError(t, err)
	close(release)
	require.NoError(t, <-finished)
	facts, err := svc.GetL0Facts(ctx)
	require.NoError(t, err)
	require.Len(t, facts, 2)
}

func TestL0DirectReadsAllPersistedLifecycleStatesWithinScope(t *testing.T) {
	base := newTestFactService(t)
	hot, err := cache.NewBoltCache(filepath.Join(t.TempDir(), "cache.db"))
	require.NoError(t, err)
	t.Cleanup(func() { _ = hot.Close() })
	svc := NewFactService(base.Store(), hot)
	a := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-a"))
	otherProject := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-b"))
	otherTenant := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-b", "project-a"))
	active := memory.NewFact("active", memory.LevelProject, "lifecycle", "")
	require.NoError(t, base.Store().Add(a, active))
	require.NoError(t, hot.WarmUp(a, []*memory.Fact{active}))
	stale := memory.NewFact("stale", memory.LevelProject, "lifecycle", "")
	stale.IsStale = true
	require.NoError(t, base.Store().Add(a, stale))
	archived := memory.NewFact("archived", memory.LevelProject, "lifecycle", "")
	archived.IsArchived = true
	require.NoError(t, base.Store().Add(a, archived))
	for _, policy := range []string{memory.OnExpireMarkStale, memory.OnExpireArchive, memory.OnExpireDelete} {
		f := memory.NewFact("unprocessed "+policy, memory.LevelProject, "lifecycle", "")
		f.CreatedAt = time.Now().Add(-time.Hour)
		f.ValidFrom = f.CreatedAt
		f.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: policy}
		require.NoError(t, base.Store().Add(a, f))
	}
	for _, ctx := range []context.Context{otherProject, otherTenant} {
		require.NoError(t, base.Store().Add(ctx, memory.NewFact("other scope", memory.LevelProject, "lifecycle", "")))
	}
	sessionStore, ok := base.Store().(memory.SessionFactStore)
	require.True(t, ok)
	require.NoError(t, sessionStore.AddForSession(a, "session-a", memory.NewFact("private session", memory.LevelProject, "lifecycle", "")))
	facts, err := svc.GetL0Facts(a)
	require.NoError(t, err)
	got := map[string]bool{}
	for _, f := range facts {
		got[f.Content] = true
		require.Equal(t, "tenant-a", f.TenantID)
		require.Equal(t, "project-a", f.ProjectID)
		require.Empty(t, f.SessionID)
	}
	require.Equal(t, map[string]bool{"active": true, "stale": true, "archived": true, "unprocessed mark_stale": true, "unprocessed archive": true, "unprocessed delete": true}, got)
}
