package shadow_ai

import (
	"context"
	"fmt"
	"log/slog"
	"time"
)

// PluginStatus represents a plugin's operational state.
type PluginStatus string

const (
	PluginStatusHealthy  PluginStatus = "healthy"
	PluginStatusDegraded PluginStatus = "degraded"
	PluginStatusOffline  PluginStatus = "offline"
)

// PluginHealth tracks the health state of a single plugin.
type PluginHealth struct {
	Vendor      string        `json:"vendor"`
	Type        PluginType    `json:"type"`
	Status      PluginStatus  `json:"status"`
	LastCheck   time.Time     `json:"last_check"`
	Consecutive int           `json:"consecutive_failures"`
	Latency     time.Duration `json:"latency"`
	LastError   string        `json:"last_error,omitempty"`
}

// MaxConsecutivePluginFailures before marking offline.
const MaxConsecutivePluginFailures = 3

// HealthChecker performs continuous health monitoring of all registered plugins.
type HealthChecker struct {
	registry *PluginRegistry
	interval time.Duration
	alertFn  func(vendor string, status PluginStatus, msg string)
	logger   *slog.Logger
}

// NewHealthChecker creates a health checker that monitors plugin health.
func NewHealthChecker(registry *PluginRegistry, interval time.Duration, alertFn func(string, PluginStatus, string)) *HealthChecker {
	if interval <= 0 {
		interval = 30 * time.Second
	}
	return &HealthChecker{
		registry: registry,
		interval: interval,
		alertFn:  alertFn,
		logger:   slog.Default().With("component", "shadow-ai-health"),
	}
}

// Start begins continuous health monitoring. Blocks until ctx is cancelled.
func (hc *HealthChecker) Start(ctx context.Context) {
	hc.logger.Info("health checker started", "interval", hc.interval)
	ticker := time.NewTicker(hc.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			hc.logger.Info("health checker stopped")
			return
		case <-ticker.C:
			hc.checkAllPlugins(ctx)
		}
	}
}

// checkAllPlugins runs health checks on all registered plugins.
func (hc *HealthChecker) checkAllPlugins(ctx context.Context) {
	vendors := hc.registry.Vendors()

	for _, vendor := range vendors {
		plugin, ok := hc.registry.Get(vendor)
		if !ok {
			continue
		}

		existing, _ := hc.registry.GetHealth(vendor)
		if existing == nil {
			continue
		}

		start := time.Now()
		err := hc.checkPlugin(ctx, plugin)
		latency := time.Since(start)

		health := &PluginHealth{
			Vendor:    vendor,
			Type:      existing.Type,
			LastCheck: time.Now(),
			Latency:   latency,
		}

		if err != nil {
			health.Consecutive = existing.Consecutive + 1
			health.LastError = err.Error()

			if health.Consecutive >= MaxConsecutivePluginFailures {
				health.Status = PluginStatusOffline
				if existing.Status != PluginStatusOffline {
					hc.logger.Error("plugin went OFFLINE",
						"vendor", vendor,
						"consecutive", health.Consecutive,
						"error", err,
					)
					if hc.alertFn != nil {
						hc.alertFn(vendor, PluginStatusOffline,
							fmt.Sprintf("Plugin %s offline after %d consecutive failures: %v",
								vendor, health.Consecutive, err))
					}
				}
			} else {
				health.Status = PluginStatusDegraded
				hc.logger.Warn("plugin health check failed",
					"vendor", vendor,
					"consecutive", health.Consecutive,
					"error", err,
				)
			}
		} else {
			health.Status = PluginStatusHealthy
			health.Consecutive = 0

			// Log recovery if previously degraded/offline.
			if existing.Status != PluginStatusHealthy {
				hc.logger.Info("plugin recovered", "vendor", vendor, "latency", latency)
				if hc.alertFn != nil {
					hc.alertFn(vendor, PluginStatusHealthy,
						fmt.Sprintf("Plugin %s recovered, latency %s", vendor, latency))
				}
			}
		}

		hc.registry.SetHealth(vendor, health)
	}
}

// checkPlugin runs the health check for a single plugin.
func (hc *HealthChecker) checkPlugin(ctx context.Context, plugin interface{}) error {
	checkCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	switch p := plugin.(type) {
	case NetworkEnforcer:
		return p.HealthCheck(checkCtx)
	case EndpointController:
		return p.HealthCheck(checkCtx)
	case WebGateway:
		return p.HealthCheck(checkCtx)
	default:
		return fmt.Errorf("plugin does not implement HealthCheck")
	}
}

// CheckNow runs an immediate health check on all plugins (non-blocking).
func (hc *HealthChecker) CheckNow(ctx context.Context) {
	hc.checkAllPlugins(ctx)
}
