package tools

import (
	"context"
	"fmt"
	"runtime"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// Version info set at build time via ldflags.
var (
	Version   = "2.0.0-dev"
	GitCommit = "unknown"
	BuildDate = "unknown"
)

// SystemService implements MCP tool logic for system operations.
type SystemService struct {
	factStore memory.FactStore
	startTime time.Time
}

// NewSystemService creates a new SystemService.
func NewSystemService(factStore memory.FactStore) *SystemService {
	return &SystemService{
		factStore: factStore,
		startTime: time.Now(),
	}
}

// HealthStatus holds the health check result.
type HealthStatus struct {
	Status    string `json:"status"`
	Version   string `json:"version"`
	GoVersion string `json:"go_version"`
	Uptime    string `json:"uptime"`
	OS        string `json:"os"`
	Arch      string `json:"arch"`
}

// Health returns server health status.
func (s *SystemService) Health(_ context.Context) *HealthStatus {
	return &HealthStatus{
		Status:    "healthy",
		Version:   Version,
		GoVersion: runtime.Version(),
		Uptime:    time.Since(s.startTime).Round(time.Second).String(),
		OS:        runtime.GOOS,
		Arch:      runtime.GOARCH,
	}
}

// VersionInfo holds version information.
type VersionInfo struct {
	Version   string `json:"version"`
	GitCommit string `json:"git_commit"`
	BuildDate string `json:"build_date"`
	GoVersion string `json:"go_version"`
}

// GetVersion returns version information.
func (s *SystemService) GetVersion() *VersionInfo {
	return &VersionInfo{
		Version:   Version,
		GitCommit: GitCommit,
		BuildDate: BuildDate,
		GoVersion: runtime.Version(),
	}
}

// DashboardData holds summary data for the system dashboard.
type DashboardData struct {
	Health    *HealthStatus          `json:"health"`
	FactStats *memory.FactStoreStats `json:"fact_stats,omitempty"`
}

// Dashboard returns a summary of all system metrics.
func (s *SystemService) Dashboard(ctx context.Context) (*DashboardData, error) {
	data := &DashboardData{
		Health: s.Health(ctx),
	}

	if s.factStore != nil {
		stats, err := s.factStore.Stats(ctx)
		if err != nil {
			return nil, fmt.Errorf("get fact stats: %w", err)
		}
		data.FactStats = stats
	}

	return data, nil
}
