package soc

import (
	"errors"
	"testing"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func newHBService(t *testing.T) *Service {
	t.Helper()
	db, err := sqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	repo, err := sqlite.NewSOCRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}
	return NewService(repo, nil)
}

func seedSensor(t *testing.T, svc *Service, sensorID string) {
	t.Helper()
	e := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, "jailbreak", "seed")
	e.SensorID = sensorID
	e.TenantID = "tnt-x"
	if _, _, err := svc.IngestInternalEvent(e); err != nil { // trusted → bypasses auth
		t.Fatalf("seed sensor %s: %v", sensorID, err)
	}
}

// Review 14.06 round-4: heartbeat lost its only authentication when requireSOC
// was removed and had no PSK backstop. It must now enforce the SAME per-sensor
// PSK as event ingest when SOC_SENSOR_KEYS is configured.
func TestRecordHeartbeat_RequiresPSKWhenConfigured(t *testing.T) {
	svc := newHBService(t)
	svc.SetSensorKeys(map[string]string{"sensorA": "secret1"})
	seedSensor(t, svc, "sensorA")

	// Wrong key → auth failure, checked BEFORE the sensor-existence lookup (so
	// no 404-vs-403 existence oracle).
	if _, err := svc.RecordHeartbeat("sensorA", "wrong"); !errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("wrong key must fail auth, got %v", err)
	}
	// Missing sensor_id with keys on → auth failure.
	if _, err := svc.RecordHeartbeat("", "x"); !errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("missing sensor_id must fail auth, got %v", err)
	}
	// Unknown sensor id with keys on → still auth failure (not a not-found oracle).
	if _, err := svc.RecordHeartbeat("ghost", "secret1"); !errors.Is(err, domsoc.ErrAuthFailed) {
		t.Fatalf("unknown sensor must fail auth (no existence oracle), got %v", err)
	}
	// Correct key → heartbeat recorded.
	ok, err := svc.RecordHeartbeat("sensorA", "secret1")
	if err != nil || !ok {
		t.Fatalf("correct key must record heartbeat, got ok=%v err=%v", ok, err)
	}
}

// With no keys configured (the documented opt-in default) heartbeat stays open,
// in parity with event ingest — so we don't break keyless deployments.
func TestRecordHeartbeat_OpenWhenNoKeys(t *testing.T) {
	svc := newHBService(t) // no SetSensorKeys
	seedSensor(t, svc, "sensorA")

	if ok, err := svc.RecordHeartbeat("sensorA", ""); err != nil || !ok {
		t.Fatalf("no-keys heartbeat should succeed, got ok=%v err=%v", ok, err)
	}
}
