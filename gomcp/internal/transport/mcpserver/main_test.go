package mcpserver

import (
	"os"
	"testing"
)

// Pre-launch audit 18.06: external sensor ingest fails CLOSED without
// SOC_SENSOR_KEYS. The SOC pipeline/integration tests in this package ingest via
// the external path without keys (they test correlation/sync/lifecycle, not sensor
// auth), so enable the dev opt-in for the test binary. The fail-closed default
// itself is asserted by TestSOC_SensorAuth_NotConfigured_FailsClosed (which clears
// the opt-in), and tests that DO set sensor keys still enforce regardless.
func TestMain(m *testing.M) {
	os.Setenv("SOC_ALLOW_UNAUTH_INGEST", "1")
	os.Exit(m.Run())
}
