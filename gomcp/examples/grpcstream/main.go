// Example: gRPC Streaming
//
// This example demonstrates bidirectional streaming with
// hub-based broadcast and individual stream handling.
package main

import (
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/sentinel-community/gomcp/pkg/grpcstream"
)

func main() {
	// Create hub to manage all streams
	hub := grpcstream.NewHub()

	// Set up callbacks
	hub.OnConnect(func(s *grpcstream.Stream) {
		log.Printf("[CONNECT] Stream %s connected", s.ID)
	})

	hub.OnDisconnect(func(s *grpcstream.Stream) {
		log.Printf("[DISCONNECT] Stream %s disconnected", s.ID)
	})

	// Create some client streams
	var wg sync.WaitGroup

	for i := 1; i <= 3; i++ {
		stream := grpcstream.NewStream(fmt.Sprintf("client-%d", i), 10)
		hub.Register(stream)

		// Start receiver for each stream
		wg.Add(1)
		go func(s *grpcstream.Stream) {
			defer wg.Done()
			receiveMessages(s)
		}(stream)
	}

	// Give streams time to start
	time.Sleep(50 * time.Millisecond)

	fmt.Printf("Active streams: %d\n", hub.Count())
	fmt.Printf("Stream IDs: %v\n\n", hub.List())

	// Broadcast to all
	fmt.Println("=== Broadcasting to all ===")
	count := hub.Broadcast(grpcstream.NewNotification("server/ready", map[string]any{
		"version": "1.0.0",
	}))
	fmt.Printf("Sent to %d streams\n", count)

	// Send to specific streams
	fmt.Println("\n=== Targeted broadcast ===")
	count = hub.BroadcastTo(
		grpcstream.NewEvent("admin/alert", map[string]any{"level": "info"}),
		"client-1", "client-3",
	)
	fmt.Printf("Sent to %d streams\n", count)

	// Send different message types
	fmt.Println("\n=== Message types ===")
	if s, ok := hub.Get("client-2"); ok {
		s.Send(grpcstream.NewRequest("tools/call", map[string]any{"name": "calculator"}))
		s.Send(grpcstream.NewNotification("progress", map[string]any{"percent": 50}))
		s.Send(grpcstream.NewResponse("req-123", "success"))
	}

	// Give time for messages to be processed
	time.Sleep(100 * time.Millisecond)

	// Close all streams
	fmt.Println("\n=== Closing ===")
	hub.Close()

	wg.Wait()
	fmt.Println("All streams closed")
}

func receiveMessages(s *grpcstream.Stream) {
	for {
		msg, err := s.ReceiveWithTimeout(200 * time.Millisecond)
		if err != nil {
			return
		}
		fmt.Printf("[%s] Received: type=%s method=%s\n",
			s.ID, msg.Type, msg.Method)
	}
}
