package shadow_ai

import (
	"context"
	"fmt"
	"log/slog"
	"time"
)

// FallbackManager provides priority-based enforcement with graceful degradation.
// Tries enforcement points in priority order; falls back to detect_only if all are offline.
type FallbackManager struct {
	registry *PluginRegistry
	priority []PluginType // e.g., ["proxy", "firewall", "edr"]
	strategy string       // "detect_only" | "alert_only"
	logger   *slog.Logger

	// Event logging for detect-only fallback.
	eventLogFn func(event ShadowAIEvent)
}

// NewFallbackManager creates a new fallback manager with the given enforcement priority.
func NewFallbackManager(registry *PluginRegistry, strategy string) *FallbackManager {
	if strategy == "" {
		strategy = "detect_only"
	}
	return &FallbackManager{
		registry: registry,
		priority: []PluginType{PluginTypeProxy, PluginTypeFirewall, PluginTypeEDR},
		strategy: strategy,
		logger:   slog.Default().With("component", "shadow-ai-fallback"),
	}
}

// SetEventLogger sets the callback for logging detection-only events.
func (fm *FallbackManager) SetEventLogger(fn func(ShadowAIEvent)) {
	fm.eventLogFn = fn
}

// BlockDomain attempts to block a domain using the highest-priority healthy plugin.
// Returns the vendor that enforced, or falls back to detect_only mode.
func (fm *FallbackManager) BlockDomain(ctx context.Context, domain, reason string) (enforcedBy string, err error) {
	for _, pType := range fm.priority {
		plugins := fm.registry.GetByType(pType)
		for _, plugin := range plugins {
			ne, ok := plugin.(NetworkEnforcer)
			if !ok {
				// Try WebGateway for URL-based blocking.
				if wg, ok := plugin.(WebGateway); ok {
					vendor := wg.Vendor()
					if !fm.registry.IsHealthy(vendor) {
						continue
					}
					if err := wg.BlockURL(ctx, domain, reason); err != nil {
						fm.logger.Warn("block failed on gateway", "vendor", vendor, "error", err)
						continue
					}
					return vendor, nil
				}
				continue
			}

			vendor := ne.Vendor()
			if !fm.registry.IsHealthy(vendor) {
				continue
			}
			if err := ne.BlockDomain(ctx, domain, reason); err != nil {
				fm.logger.Warn("block failed on enforcer", "vendor", vendor, "error", err)
				continue
			}
			return vendor, nil
		}
	}

	// All enforcement points unavailable — fallback.
	fm.logger.Warn("all enforcement points unavailable, falling to detect_only",
		"domain", domain,
		"strategy", fm.strategy,
	)
	fm.logDetectOnly(domain, reason)
	return "", nil
}

// BlockIP attempts to block an IP using the highest-priority healthy firewall.
func (fm *FallbackManager) BlockIP(ctx context.Context, ip string, duration time.Duration, reason string) (enforcedBy string, err error) {
	enforcers := fm.registry.GetNetworkEnforcers()
	for _, ne := range enforcers {
		vendor := ne.Vendor()
		if !fm.registry.IsHealthy(vendor) {
			continue
		}
		if err := ne.BlockIP(ctx, ip, duration, reason); err != nil {
			fm.logger.Warn("block IP failed", "vendor", vendor, "error", err)
			continue
		}
		return vendor, nil
	}

	fm.logger.Warn("no healthy enforcer for IP block, falling to detect_only",
		"ip", ip,
		"strategy", fm.strategy,
	)
	fm.logDetectOnly(ip, reason)
	return "", nil
}

// IsolateHost attempts to isolate a host using the highest-priority healthy EDR.
func (fm *FallbackManager) IsolateHost(ctx context.Context, hostname string) (enforcedBy string, err error) {
	controllers := fm.registry.GetEndpointControllers()
	for _, ec := range controllers {
		vendor := ec.Vendor()
		if !fm.registry.IsHealthy(vendor) {
			continue
		}
		if err := ec.IsolateHost(ctx, hostname); err != nil {
			fm.logger.Warn("isolate failed", "vendor", vendor, "error", err)
			continue
		}
		return vendor, nil
	}

	fm.logger.Warn("no healthy EDR for host isolation, falling to detect_only",
		"hostname", hostname,
		"strategy", fm.strategy,
	)
	return "", fmt.Errorf("no healthy EDR available for host isolation")
}

// logDetectOnly records a detection-only event when no enforcement is possible.
func (fm *FallbackManager) logDetectOnly(target, reason string) {
	if fm.eventLogFn != nil {
		fm.eventLogFn(ShadowAIEvent{
			Destination:     target,
			DetectionMethod: DetectNetwork,
			Action:          "detect_only",
			Metadata: map[string]string{
				"reason":           reason,
				"fallback_strategy": fm.strategy,
			},
			Timestamp: time.Now(),
		})
	}
}

// Strategy returns the configured fallback strategy.
func (fm *FallbackManager) Strategy() string {
	return fm.strategy
}
