package soc

import (
	"testing"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// Review 14.06 round-4: SOC_SENSOR_KEYS gains an optional 3rd field
// "sensorID:key:tenant". Keys parse as before; tenants come from the 3rd field.
func TestParseSensorKeysAndTenants(t *testing.T) {
	env := "sensorA:keyA:tnt-1, sensorB:keyB , sensorC:keyC:tnt-3"

	keys := ParseSensorKeys(env)
	if keys["sensorA"] != "keyA" || keys["sensorB"] != "keyB" || keys["sensorC"] != "keyC" {
		t.Fatalf("keys parse wrong (3-field key must NOT include :tenant): %v", keys)
	}

	tenants := ParseSensorTenants(env)
	if tenants["sensorA"] != "tnt-1" || tenants["sensorC"] != "tnt-3" {
		t.Fatalf("tenant parse wrong: %v", tenants)
	}
	if _, ok := tenants["sensorB"]; ok {
		t.Fatalf("sensorB carries no tenant field, must be absent: %v", tenants)
	}

	// Backward-compat: a plain "id:key" still yields the key and no tenant.
	if k := ParseSensorKeys("s1:k1"); k["s1"] != "k1" {
		t.Fatalf("2-field key parse broken: %v", k)
	}
	if tn := ParseSensorTenants("s1:k1"); tn != nil {
		t.Fatalf("2-field input must yield no tenants, got: %v", tn)
	}
}

// The core cross-tenant fix: an authenticated event carrying NO TenantID is
// attributed to its sensor's bound tenant, so two tenants' sensors do NOT
// co-mingle (the empty-TenantID collision the round-3 clustering fix depended on
// not happening).
func TestIngest_DerivesTenantFromSensorBinding(t *testing.T) {
	svc := newHBService(t) // helper in heartbeat_auth_test.go (same package)
	svc.SetSensorKeys(map[string]string{"sensorA": "k1", "sensorB": "k2"})
	svc.SetSensorTenants(map[string]string{"sensorA": "tnt-1", "sensorB": "tnt-2"})

	mk := func(sensorID, key, cat string) {
		e := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityHigh, cat, cat+" desc")
		e.SensorID = sensorID
		e.SensorKey = key
		// Intentionally NO TenantID — it must be derived from the sensor binding.
		if _, _, err := svc.IngestEvent(e); err != nil {
			t.Fatalf("ingest %s: %v", sensorID, err)
		}
	}
	mk("sensorA", "k1", "jailbreak")
	mk("sensorB", "k2", "injection")

	cats := func(r *AnalyticsReport) map[string]bool {
		m := map[string]bool{}
		for _, c := range r.TopCategories {
			m[c.Category] = true
		}
		return m
	}
	ra, _ := svc.Analytics("tnt-1", 24)
	rb, _ := svc.Analytics("tnt-2", 24)

	if c := cats(ra); c["injection"] || !c["jailbreak"] {
		t.Fatalf("tnt-1 must see only sensorA's events (no cross-tenant): %v", c)
	}
	if c := cats(rb); c["jailbreak"] || !c["injection"] {
		t.Fatalf("tnt-2 must see only sensorB's events (no cross-tenant): %v", c)
	}
}
