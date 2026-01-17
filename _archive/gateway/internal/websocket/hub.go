package websocket

import (
	"encoding/json"
	"log"
	"sync"
	"time"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
)

// Event represents a real-time event
type Event struct {
	Type      string      `json:"type"`
	Timestamp time.Time   `json:"timestamp"`
	Data      interface{} `json:"data"`
}

// Hub manages WebSocket connections
type Hub struct {
	clients    map[*websocket.Conn]bool
	broadcast  chan Event
	register   chan *websocket.Conn
	unregister chan *websocket.Conn
	mu         sync.RWMutex
}

// NewHub creates a new WebSocket hub
func NewHub() *Hub {
	return &Hub{
		clients:    make(map[*websocket.Conn]bool),
		broadcast:  make(chan Event, 100),
		register:   make(chan *websocket.Conn),
		unregister: make(chan *websocket.Conn),
	}
}

// Run starts the hub
func (h *Hub) Run() {
	for {
		select {
		case conn := <-h.register:
			h.mu.Lock()
			h.clients[conn] = true
			h.mu.Unlock()
			log.Printf("WebSocket client connected. Total: %d", len(h.clients))

		case conn := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[conn]; ok {
				delete(h.clients, conn)
				conn.Close()
			}
			h.mu.Unlock()
			log.Printf("WebSocket client disconnected. Total: %d", len(h.clients))

		case event := <-h.broadcast:
			h.mu.RLock()
			data, _ := json.Marshal(event)
			for conn := range h.clients {
				if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
					h.mu.RUnlock()
					h.unregister <- conn
					h.mu.RLock()
				}
			}
			h.mu.RUnlock()
		}
	}
}

// Broadcast sends an event to all connected clients
func (h *Hub) Broadcast(eventType string, data interface{}) {
	event := Event{
		Type:      eventType,
		Timestamp: time.Now(),
		Data:      data,
	}
	select {
	case h.broadcast <- event:
	default:
		log.Println("WebSocket broadcast channel full, dropping event")
	}
}

// Handler returns the WebSocket handler
func (h *Hub) Handler() fiber.Handler {
	return websocket.New(func(c *websocket.Conn) {
		h.register <- c
		defer func() {
			h.unregister <- c
		}()

		// Send welcome message
		welcome := Event{
			Type:      "connected",
			Timestamp: time.Now(),
			Data:      map[string]string{"message": "Connected to Sentinel real-time feed"},
		}
		data, _ := json.Marshal(welcome)
		c.WriteMessage(websocket.TextMessage, data)

		// Keep connection alive
		for {
			_, _, err := c.ReadMessage()
			if err != nil {
				break
			}
		}
	})
}

// Event types
const (
	EventThreatDetected = "threat_detected"
	EventRequestBlocked = "request_blocked"
	EventEngineHealth   = "engine_health"
	EventMetrics        = "metrics"
)
