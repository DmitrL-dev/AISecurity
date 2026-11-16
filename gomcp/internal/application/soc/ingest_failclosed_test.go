package soc

import (
	"errors"
	"os"
	"testing"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// Pre-launch audit 18.06: external sensor ingest now fails CLOSED when no
// SOC_SENSOR_KEYS are configured. The pipeline/integration tests in this package
// ingest via the external path without keys (they test correlation/SOAR, not
// sensor auth), so enable the dev opt-in for the whole test binary. Sensor-auth
// tests (e.g. TestIngestInternalEvent_BypassesSensorAuth) set keys explicitly and
// still enforce regardless of this env. The fail-closed default itself is proven
// by TestIngestEvent_FailsClosedWithoutSensorKeys below (which clears the opt-in).
func TestMain(m *testing.M) {
	os.Setenv("SOC_ALLOW_UNAUTH_INGEST", "1")
	os.Exit(m.Run())
}

func TestIngestEvent_FailsClosedWithoutSensorKeys(t *testing.T) {
	t.Setenv("SOC_ALLOW_UNAUTH_INGEST", "") // override the package opt-in → prod default

	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	svc := NewService(repo, nil) // no SetSensorKeys → no PSKs configured

	evt := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "test", "external probe")
	evt.SensorID = "rogue-sensor"
	if _, _, err := svc.IngestEvent(evt); !errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("external ingest without keys (opt-in off) must FAIL CLOSED, got %v", err)
	}

	// The internal (trusted) gateway feed must remain unaffected.
	intl := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "test", "gateway feed")
	intl.TenantID = "tnt-x"
	if _, _, err := svc.IngestInternalEvent(intl); errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("internal gateway feed must bypass sensor auth even fail-closed, got %v", err)
	}
}
