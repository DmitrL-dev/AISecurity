package shadow_ai

// --- Vendor Plugin Registration ---
//
// The concrete vendor clients live in their own files:
//
//	plugin_checkpoint.go  — Check Point Management API   (NetworkEnforcer)
//	plugin_crowdstrike.go — CrowdStrike Falcon           (EndpointController)
//	plugin_zscaler.go     — Zscaler Internet Access (ZIA)(WebGateway)
//
// Each is a REAL HTTP client (proper auth, endpoints, SSRF-hardened transport).
// They are only loaded when explicitly enabled with valid creds in the plugin
// config; with no creds the controller runs in honest detect_only mode and never
// fabricates enforcement.

// RegisterDefaultPlugins registers all built-in vendor plugin factories.
func RegisterDefaultPlugins(registry *PluginRegistry) {
	registry.RegisterFactory(PluginTypeFirewall, "checkpoint", func() interface{} {
		return NewCheckPointEnforcer()
	})
	registry.RegisterFactory(PluginTypeEDR, "crowdstrike", func() interface{} {
		return NewCrowdStrikeController()
	})
	registry.RegisterFactory(PluginTypeProxy, "zscaler", func() interface{} {
		return NewZscalerGateway()
	})
}
