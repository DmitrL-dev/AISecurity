package soc

import (
	"strings"
	"testing"
)

// Review 14.06 round-5: SensorID is attacker-controlled and used as a map key +
// rate-limit key + persisted column, so Validate bounds its length and charset
// to stop a unique-SensorID flood (unbounded maps / SQLite rows).
func TestSOCEvent_Validate_SensorID(t *testing.T) {
	base := func() SOCEvent {
		return NewSOCEvent(SourceSentinelCore, SeverityHigh, "jailbreak", "desc")
	}

	// Empty SensorID is allowed (the ingest path falls back to Source).
	e := base()
	e.SensorID = ""
	if err := e.Validate(); err != nil {
		t.Fatalf("empty sensor_id should be valid: %v", err)
	}

	// Normal ids and the gateway "gateway:<tenant>" form are valid.
	for _, id := range []string{"host-01", "gateway:tnt-abc", "sensor_1.edge"} {
		e := base()
		e.SensorID = id
		if err := e.Validate(); err != nil {
			t.Fatalf("sensor_id %q should be valid: %v", id, err)
		}
	}

	// Over-long id is rejected.
	e = base()
	e.SensorID = strings.Repeat("a", MaxSensorIDLen+1)
	if err := e.Validate(); err == nil {
		t.Fatal("over-long sensor_id must be rejected")
	}

	// Bad charset (space, slash, tab, punctuation) is rejected.
	for _, id := range []string{"has space", "a/b", "x\ty", "drop;table"} {
		e := base()
		e.SensorID = id
		if err := e.Validate(); err == nil {
			t.Fatalf("sensor_id %q must be rejected (bad charset)", id)
		}
	}
}
