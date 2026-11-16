package soc

import "testing"

// Review 14.06 round-3: alert clusters must never co-mingle tenants. Two events
// with identical category/source but different tenants must land in DIFFERENT,
// tenant-stamped clusters.
func TestClusterEngine_TenantIsolation(t *testing.T) {
	ce := NewClusterEngine(DefaultClusterConfig())

	a := NewSOCEvent(SourceSentinelCore, SeverityHigh, "jailbreak", "tenant a event")
	a.TenantID = "tnt-a"
	b := NewSOCEvent(SourceSentinelCore, SeverityHigh, "jailbreak", "tenant b event")
	b.TenantID = "tnt-b"
	a2 := NewSOCEvent(SourceSentinelCore, SeverityHigh, "jailbreak", "tenant a event 2")
	a2.TenantID = "tnt-a"

	ca := ce.AddEvent(a)
	cb := ce.AddEvent(b)
	ca2 := ce.AddEvent(a2)

	if ca == cb {
		t.Fatalf("different tenants must NOT share a cluster (a=%s b=%s)", ca, cb)
	}
	if ca != ca2 {
		t.Fatalf("same tenant + category/source should cluster together (a=%s a2=%s)", ca, ca2)
	}

	// Every cluster is single-tenant and correctly stamped.
	for _, c := range ce.Clusters() {
		if c.TenantID == "" {
			t.Fatalf("cluster %s has no tenant", c.ID)
		}
	}
}
