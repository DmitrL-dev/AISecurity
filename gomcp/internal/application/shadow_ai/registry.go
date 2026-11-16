package shadow_ai

import (
	"fmt"
	"log/slog"
	"sync"
)

// PluginFactory creates a new plugin instance.
type PluginFactory func() interface{}

// PluginRegistry manages vendor plugin registration, loading, and lifecycle.
// Thread-safe via sync.RWMutex.
type PluginRegistry struct {
	mu        sync.RWMutex
	plugins   map[string]interface{}     // vendor → plugin instance
	factories map[string]PluginFactory   // "type_vendor" → factory
	configs   map[string]*PluginConfig   // vendor → config
	health    map[string]*PluginHealth   // vendor → health status
	logger    *slog.Logger
}

// NewPluginRegistry creates a new plugin registry.
func NewPluginRegistry() *PluginRegistry {
	return &PluginRegistry{
		plugins:   make(map[string]interface{}),
		factories: make(map[string]PluginFactory),
		configs:   make(map[string]*PluginConfig),
		health:    make(map[string]*PluginHealth),
		logger:    slog.Default().With("component", "shadow-ai-registry"),
	}
}

// RegisterFactory registers a plugin factory for a given type+vendor combination.
// Example: RegisterFactory("firewall", "checkpoint", func() interface{} { return &CheckPointEnforcer{} })
func (r *PluginRegistry) RegisterFactory(pluginType PluginType, vendor string, factory PluginFactory) {
	r.mu.Lock()
	defer r.mu.Unlock()

	key := fmt.Sprintf("%s_%s", pluginType, vendor)
	r.factories[key] = factory
	r.logger.Info("factory registered", "type", pluginType, "vendor", vendor)
}

// LoadPlugins creates and initializes plugins from configuration.
// Plugins that fail to initialize are logged but do not block other plugins.
func (r *PluginRegistry) LoadPlugins(config *IntegrationConfig) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	loaded := 0
	for i := range config.Plugins {
		pluginCfg := &config.Plugins[i]
		if !pluginCfg.Enabled {
			r.logger.Debug("plugin disabled, skipping", "vendor", pluginCfg.Vendor)
			continue
		}

		key := fmt.Sprintf("%s_%s", pluginCfg.Type, pluginCfg.Vendor)
		factory, exists := r.factories[key]
		if !exists {
			r.logger.Warn("no factory for plugin", "key", key, "vendor", pluginCfg.Vendor)
			continue
		}

		plugin := factory()

		// Initialize if plugin supports it.
		if init, ok := plugin.(Initializer); ok {
			if err := init.Initialize(pluginCfg.Config); err != nil {
				r.logger.Error("plugin init failed", "vendor", pluginCfg.Vendor, "error", err)
				continue
			}
		}

		r.plugins[pluginCfg.Vendor] = plugin
		r.configs[pluginCfg.Vendor] = pluginCfg
		r.health[pluginCfg.Vendor] = &PluginHealth{
			Vendor: pluginCfg.Vendor,
			Type:   pluginCfg.Type,
			Status: PluginStatusHealthy,
		}
		loaded++
		r.logger.Info("plugin loaded", "vendor", pluginCfg.Vendor, "type", pluginCfg.Type)
	}

	r.logger.Info("plugin loading complete", "loaded", loaded, "total", len(config.Plugins))
	return nil
}

// Get returns a plugin by vendor name.
func (r *PluginRegistry) Get(vendor string) (interface{}, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	p, ok := r.plugins[vendor]
	return p, ok
}

// GetByType returns all plugins of a given type.
func (r *PluginRegistry) GetByType(pluginType PluginType) []interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var result []interface{}
	for vendor, cfg := range r.configs {
		if cfg.Type == pluginType {
			if plugin, ok := r.plugins[vendor]; ok {
				result = append(result, plugin)
			}
		}
	}
	return result
}

// GetNetworkEnforcers returns all loaded NetworkEnforcer plugins.
func (r *PluginRegistry) GetNetworkEnforcers() []NetworkEnforcer {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var result []NetworkEnforcer
	for _, plugin := range r.plugins {
		if ne, ok := plugin.(NetworkEnforcer); ok {
			result = append(result, ne)
		}
	}
	return result
}

// GetEndpointControllers returns all loaded EndpointController plugins.
func (r *PluginRegistry) GetEndpointControllers() []EndpointController {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var result []EndpointController
	for _, plugin := range r.plugins {
		if ec, ok := plugin.(EndpointController); ok {
			result = append(result, ec)
		}
	}
	return result
}

// GetWebGateways returns all loaded WebGateway plugins.
func (r *PluginRegistry) GetWebGateways() []WebGateway {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var result []WebGateway
	for _, plugin := range r.plugins {
		if wg, ok := plugin.(WebGateway); ok {
			result = append(result, wg)
		}
	}
	return result
}

// IsHealthy returns true if a plugin is currently healthy.
func (r *PluginRegistry) IsHealthy(vendor string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	h, ok := r.health[vendor]
	return ok && h.Status == PluginStatusHealthy
}

// SetHealth updates the health status for a plugin.
func (r *PluginRegistry) SetHealth(vendor string, health *PluginHealth) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.health[vendor] = health
}

// GetHealth returns the health status snapshot for a plugin.
func (r *PluginRegistry) GetHealth(vendor string) (*PluginHealth, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	h, ok := r.health[vendor]
	if !ok {
		return nil, false
	}
	cp := *h
	return &cp, true
}

// AllHealth returns health snapshots for all plugins.
func (r *PluginRegistry) AllHealth() []PluginHealth {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make([]PluginHealth, 0, len(r.health))
	for _, h := range r.health {
		result = append(result, *h)
	}
	return result
}

// PluginCount returns the number of loaded plugins.
func (r *PluginRegistry) PluginCount() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.plugins)
}

// Vendors returns all loaded vendor names.
func (r *PluginRegistry) Vendors() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	result := make([]string, 0, len(r.plugins))
	for v := range r.plugins {
		result = append(result, v)
	}
	return result
}
