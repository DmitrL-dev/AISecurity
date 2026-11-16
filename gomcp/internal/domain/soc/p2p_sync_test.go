package soc

import (
	"testing"
)

func TestP2PSync_Disabled(t *testing.T) {
	p := NewP2PSyncService()
	err := p.EnqueueOutbound(SyncEvent, map[string]string{"id": "evt-1"})
	if err != nil {
		t.Fatalf("disabled enqueue should return nil, got %v", err)
	}
	msgs := p.DrainOutbox()
	if len(msgs) != 0 {
		t.Fatal("disabled should produce no outbox messages")
	}
}

func TestP2PSync_AddAndListPeers(t *testing.T) {
	p := NewP2PSyncService()
	p.AddPeer("soc-2", "Site-B", "http://soc-b:9100", "full")
	p.AddPeer("soc-3", "Site-C", "http://soc-c:9100", "readonly")

	peers := p.ListPeers()
	if len(peers) != 2 {
		t.Fatalf("expected 2 peers, got %d", len(peers))
	}

	p.RemovePeer("soc-3")
	peers = p.ListPeers()
	if len(peers) != 1 {
		t.Fatalf("expected 1 peer after remove, got %d", len(peers))
	}
}

func TestP2PSync_EnqueueAndDrain(t *testing.T) {
	p := NewP2PSyncService()
	p.Enable()

	p.EnqueueOutbound(SyncEvent, map[string]string{"event_id": "evt-1"})
	p.EnqueueOutbound(SyncIncident, map[string]string{"incident_id": "inc-1"})
	p.EnqueueOutbound(SyncIOC, map[string]string{"ioc": "1.2.3.4"})

	msgs := p.DrainOutbox()
	if len(msgs) != 3 {
		t.Fatalf("expected 3 outbox messages, got %d", len(msgs))
	}

	// After drain, outbox should be empty
	msgs2 := p.DrainOutbox()
	if len(msgs2) != 0 {
		t.Fatalf("outbox should be empty after drain, got %d", len(msgs2))
	}
}

func TestP2PSync_ReceiveInbound(t *testing.T) {
	p := NewP2PSyncService()
	p.Enable()
	p.AddPeer("soc-2", "Site-B", "http://soc-b:9100", "full")

	msg := SyncMessage{
		ID:   "sync-1",
		Type: SyncEvent,
	}

	err := p.ReceiveInbound("soc-2", msg)
	if err != nil {
		t.Fatalf("receive should succeed: %v", err)
	}

	peers := p.ListPeers()
	for _, peer := range peers {
		if peer.ID == "soc-2" {
			if peer.EventsRecv != 1 {
				t.Fatalf("expected 1 received, got %d", peer.EventsRecv)
			}
			if peer.Status != "connected" {
				t.Fatalf("expected connected, got %s", peer.Status)
			}
		}
	}
}

func TestP2PSync_ReadonlyPeer(t *testing.T) {
	p := NewP2PSyncService()
	p.Enable()
	p.AddPeer("soc-ro", "ReadOnly-SOC", "http://ro:9100", "readonly")

	// Heartbeat should be allowed
	err := p.ReceiveInbound("soc-ro", SyncMessage{Type: SyncHeartbeat})
	if err != nil {
		t.Fatalf("heartbeat should be allowed from readonly: %v", err)
	}

	// Event should be denied
	err = p.ReceiveInbound("soc-ro", SyncMessage{Type: SyncEvent})
	if err == nil {
		t.Fatal("event from readonly peer should be denied")
	}
}

func TestP2PSync_UnknownPeer(t *testing.T) {
	p := NewP2PSyncService()
	p.Enable()

	err := p.ReceiveInbound("unknown", SyncMessage{Type: SyncEvent})
	if err == nil {
		t.Fatal("should reject unknown peer")
	}
}

func TestP2PSync_Stats(t *testing.T) {
	p := NewP2PSyncService()
	p.Enable()
	p.AddPeer("soc-2", "B", "http://b:9100", "full")

	stats := p.Stats()
	if stats["enabled"] != true {
		t.Fatal("should be enabled")
	}
	if stats["total_peers"].(int) != 1 {
		t.Fatal("should have 1 peer")
	}
}
