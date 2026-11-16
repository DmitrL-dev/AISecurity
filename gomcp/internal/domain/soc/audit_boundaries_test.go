package soc

import (
	"net"
	"testing"
)

func TestAuditTenantSubscriptionFiltersBeforeQueueing(t *testing.T) {
	bus := NewEventBus(1)
	events := bus.SubscribeTenant("audit", "tenant-a")
	bus.Publish(SOCEvent{ID: "foreign", TenantID: "tenant-b"})
	bus.Publish(SOCEvent{ID: "own", TenantID: "tenant-a"})
	select {
	case event := <-events:
		if event.ID != "own" {
			t.Fatal("foreign event occupied tenant queue")
		}
	default:
		t.Fatal("tenant event dropped")
	}
}
func TestAuditWebhookBlocksSpecialPurposeAddressRanges(t *testing.T) {
	for _, raw := range []string{"100.64.0.1", "192.0.2.1", "198.18.0.1", "240.0.0.1", "64:ff9b::7f00:1", "64:ff9b:1::1", "2002:7f00:1::1", "::ffff:127.0.0.1"} {
		if !webhookIPDisallowed(net.ParseIP(raw)) {
			t.Errorf("special-purpose address allowed: %s", raw)
		}
	}
	if webhookIPDisallowed(net.ParseIP("8.8.8.8")) {
		t.Fatal("public fixture address denied")
	}
}

func TestAuditIncidentIdentityDoesNotRestartWithProcessCounter(t *testing.T) {
	first := NewIncident("synthetic fixture", SeverityHigh, "audit-rule")
	second := NewIncident("synthetic fixture", SeverityHigh, "audit-rule")
	if first.ID == second.ID || len(first.ID) < 30 {
		t.Fatal("incident IDs lack independent random identity")
	}
}
