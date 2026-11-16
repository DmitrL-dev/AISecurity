package httpserver

import (
	"os"
	"testing"
)

// Pre-launch audit 18.06: external sensor ingest fails CLOSED without
// SOC_SENSOR_KEYS. The HTTP integration tests in this package ingest via the
// external path without keys (they test the SOC pipeline / dashboard surface, not
// sensor auth), so enable the dev opt-in for the test binary. The fail-closed
// default is proven in the soc package (TestIngestEvent_FailsClosedWithoutSensorKeys).
func TestMain(m *testing.M) {
	os.Setenv("SOC_ALLOW_UNAUTH_INGEST", "1")
	os.Exit(m.Run())
}
