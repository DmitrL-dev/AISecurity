package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

// ============================================================================
// CENTRIFUGE PROBE — Deep Protocol Reconnaissance
// ============================================================================
// Centrifuge is a real-time messaging server by Centrifugal.
// Wire format: line-delimited JSON over WebSocket.
// Commands: connect, subscribe, publish, presence, history, ping
// ============================================================================

// CentrifugeCommand represents a Centrifuge protocol command.
type CentrifugeCommand struct {
	ID        int               `json:"id"`
	Connect   *ConnectRequest   `json:"connect,omitempty"`
	Subscribe *SubscribeRequest `json:"subscribe,omitempty"`
	Presence  *PresenceRequest  `json:"presence,omitempty"`
	History   *HistoryRequest   `json:"history,omitempty"`
	Ping      *PingRequest      `json:"ping,omitempty"`
	RPC       *RPCRequest       `json:"rpc,omitempty"`
}

type ConnectRequest struct {
	Token   string            `json:"token,omitempty"`
	Data    json.RawMessage   `json:"data,omitempty"`
	Name    string            `json:"name,omitempty"`
	Version string            `json:"version,omitempty"`
	Subs    map[string]SubReq `json:"subs,omitempty"`
}

type SubReq struct {
	Recover bool   `json:"recover,omitempty"`
	Epoch   string `json:"epoch,omitempty"`
	Offset  uint64 `json:"offset,omitempty"`
}

type SubscribeRequest struct {
	Channel string          `json:"channel"`
	Token   string          `json:"token,omitempty"`
	Data    json.RawMessage `json:"data,omitempty"`
}

type PresenceRequest struct {
	Channel string `json:"channel"`
}

type HistoryRequest struct {
	Channel string `json:"channel"`
	Limit   int    `json:"limit,omitempty"`
}

type PingRequest struct{}

type RPCRequest struct {
	Method string          `json:"method,omitempty"`
	Data   json.RawMessage `json:"data,omitempty"`
}

// CentrifugeReply represents a server response.
type CentrifugeReply struct {
	ID      int              `json:"id,omitempty"`
	Connect *ConnectResult   `json:"connect,omitempty"`
	Sub     *SubscribeResult `json:"subscribe,omitempty"`
	Error   *ErrorResult     `json:"error,omitempty"`
	Push    *PushResult      `json:"push,omitempty"`
}

type ConnectResult struct {
	Client  string               `json:"client"`
	Version string               `json:"version"`
	Expires bool                 `json:"expires,omitempty"`
	TTL     int                  `json:"ttl,omitempty"`
	Data    json.RawMessage      `json:"data,omitempty"`
	Subs    map[string]SubResult `json:"subs,omitempty"`
	Ping    int                  `json:"ping,omitempty"`
	Pong    bool                 `json:"pong,omitempty"`
	Node    string               `json:"node,omitempty"`
}

type SubResult struct {
	Recoverable bool   `json:"recoverable,omitempty"`
	Epoch       string `json:"epoch,omitempty"`
}

type SubscribeResult struct {
	Recoverable bool            `json:"recoverable,omitempty"`
	Epoch       string          `json:"epoch,omitempty"`
	Data        json.RawMessage `json:"data,omitempty"`
}

type ErrorResult struct {
	Code      int    `json:"code"`
	Message   string `json:"message"`
	Temporary bool   `json:"temporary,omitempty"`
}

type PushResult struct {
	Channel string          `json:"channel,omitempty"`
	Pub     json.RawMessage `json:"pub,omitempty"`
	Message json.RawMessage `json:"message,omitempty"`
}

// CentrifugeProbeResult holds all findings from the deep probe.
type CentrifugeProbeResult struct {
	Connected      bool                 `json:"connected"`
	ClientID       string               `json:"client_id"`
	ServerVersion  string               `json:"server_version"`
	ServerNode     string               `json:"server_node"`
	PingInterval   int                  `json:"ping_interval"`
	TTL            int                  `json:"ttl,omitempty"`
	Expires        bool                 `json:"expires,omitempty"`
	ServerSubs     []string             `json:"server_subs,omitempty"`
	ChannelResults []ChannelProbeResult `json:"channel_results"`
	Error          string               `json:"error,omitempty"`
	ConnectLatency string               `json:"connect_latency"`
}

type ChannelProbeResult struct {
	Channel    string `json:"channel"`
	Accessible bool   `json:"accessible"`
	Error      string `json:"error,omitempty"`
	ErrorCode  int    `json:"error_code,omitempty"`
}

// CentrifugeProbe manages a Centrifuge protocol probe session.
type CentrifugeProbe struct {
	target  string
	headers http.Header
}

// NewCentrifugeProbe creates a probe targeting a Centrifuge WebSocket endpoint.
func NewCentrifugeProbe(target string, headers http.Header) *CentrifugeProbe {
	return &CentrifugeProbe{target: target, headers: headers}
}

// Execute runs the full Centrifuge deep probe with multi-strategy connect.
// Strategy A: Anonymous connect with subprotocol
// Strategy B: Connect with CSRF token
// Strategy C: Read-first (detect server-initiated close)
func (cp *CentrifugeProbe) Execute(ctx context.Context) (*CentrifugeProbeResult, error) {
	result := &CentrifugeProbeResult{}

	// ── Strategy A: Try read-first to detect server-initiated close ──
	fmt.Println("    [A] Passive listen (detect server-initiated messages)...")
	dialerA := websocket.Dialer{HandshakeTimeout: 10 * time.Second}
	connA, _, errA := dialerA.DialContext(ctx, cp.target, cp.headers)
	if errA != nil {
		fmt.Printf("    [A] Dial failed: %v\n", errA)
	} else {
		connA.SetReadDeadline(time.Now().Add(3 * time.Second))
		msgType, msg, readErr := connA.ReadMessage()
		if readErr != nil {
			fmt.Printf("    [A] Server sent close/error before connect: %v\n", readErr)
		} else {
			fmt.Printf("    [A] Server sent message (type=%d): %s\n", msgType, string(msg))
		}
		connA.Close()
	}

	// ── Strategy B: Connect with centrifuge-json subprotocol ──
	fmt.Println("    [B] Connect with centrifuge-json subprotocol...")
	dialerB := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
		Subprotocols:     []string{"centrifuge-json"},
	}
	connB, respB, errB := dialerB.DialContext(ctx, cp.target, cp.headers)
	if errB != nil {
		fmt.Printf("    [B] Dial failed: %v\n", errB)
	} else {
		negotiated := ""
		if respB != nil {
			negotiated = respB.Header.Get("Sec-WebSocket-Protocol")
		}
		fmt.Printf("    [B] Connected! Negotiated subprotocol: '%s'\n", negotiated)

		connectCmd := CentrifugeCommand{
			ID: 1,
			Connect: &ConnectRequest{
				Name:    "centrifuge-js",
				Version: "5.2.2",
			},
		}
		if sendErr := cp.sendCommand(connB, connectCmd); sendErr != nil {
			fmt.Printf("    [B] Send error: %v\n", sendErr)
		} else {
			fmt.Println("    [B] Connect command sent, reading reply...")
			connB.SetReadDeadline(time.Now().Add(10 * time.Second))
			msgType, msg, readErr := connB.ReadMessage()
			if readErr != nil {
				fmt.Printf("    [B] Read error: %v\n", readErr)
			} else {
				fmt.Printf("    [B] Reply (type=%d): %s\n", msgType, string(msg))
				reply, parseErr := cp.parseReply(msg)
				if parseErr == nil && reply.Connect != nil {
					result.Connected = true
					result.ClientID = reply.Connect.Client
					result.ServerVersion = reply.Connect.Version
					result.ServerNode = reply.Connect.Node
					result.PingInterval = reply.Connect.Ping
					result.TTL = reply.Connect.TTL
					result.Expires = reply.Connect.Expires
					for ch := range reply.Connect.Subs {
						result.ServerSubs = append(result.ServerSubs, ch)
					}
				}
			}
		}
		connB.Close()
	}

	// If Strategy B failed, try C with CSRF token
	if !result.Connected {
		csrfToken := cp.headers.Get("X-Csrf-Token")
		if csrfToken != "" {
			fmt.Println("    [C] Connect with CSRF token as Centrifuge token...")
			dialerC := websocket.Dialer{
				HandshakeTimeout: 10 * time.Second,
				Subprotocols:     []string{"centrifuge-json"},
			}
			connC, _, errC := dialerC.DialContext(ctx, cp.target, cp.headers)
			if errC != nil {
				fmt.Printf("    [C] Dial failed: %v\n", errC)
			} else {
				connectCmd := CentrifugeCommand{
					ID: 1,
					Connect: &ConnectRequest{
						Token:   csrfToken,
						Name:    "centrifuge-js",
						Version: "5.2.2",
					},
				}
				if sendErr := cp.sendCommand(connC, connectCmd); sendErr != nil {
					fmt.Printf("    [C] Send error: %v\n", sendErr)
				} else {
					connC.SetReadDeadline(time.Now().Add(10 * time.Second))
					msgType, msg, readErr := connC.ReadMessage()
					if readErr != nil {
						fmt.Printf("    [C] Read error: %v\n", readErr)
					} else {
						fmt.Printf("    [C] Reply (type=%d): %s\n", msgType, string(msg))
						reply, parseErr := cp.parseReply(msg)
						if parseErr == nil && reply.Connect != nil {
							result.Connected = true
							result.ClientID = reply.Connect.Client
							result.ServerVersion = reply.Connect.Version
							result.ServerNode = reply.Connect.Node
							result.PingInterval = reply.Connect.Ping
							result.TTL = reply.Connect.TTL
							result.Expires = reply.Connect.Expires
							for ch := range reply.Connect.Subs {
								result.ServerSubs = append(result.ServerSubs, ch)
							}
						}
					}
				}
				connC.Close()
			}
		}
	}

	// If connected, try channel enumeration
	if result.Connected {
		fmt.Println("    [D] Channel enumeration...")
		dialerD := websocket.Dialer{
			HandshakeTimeout: 10 * time.Second,
			Subprotocols:     []string{"centrifuge-json"},
		}
		connD, _, errD := dialerD.DialContext(ctx, cp.target, cp.headers)
		if errD == nil {
			// Re-connect for channel probing
			connectCmd := CentrifugeCommand{ID: 1, Connect: &ConnectRequest{Name: "centrifuge-js", Version: "5.2.2"}}
			cp.sendCommand(connD, connectCmd)
			cp.readReply(connD, 10*time.Second)

			channels := []string{"notifications", "events", "updates", "chat", "system", "admin", "public", "broadcast", "#notifications", "$notifications", "user", "global", "live", "feed", "activity"}
			cmdID := 2
			for _, ch := range channels {
				subCmd := CentrifugeCommand{ID: cmdID, Subscribe: &SubscribeRequest{Channel: ch}}
				if sendErr := cp.sendCommand(connD, subCmd); sendErr != nil {
					result.ChannelResults = append(result.ChannelResults, ChannelProbeResult{Channel: ch, Error: fmt.Sprintf("send: %v", sendErr)})
					break
				}
				subReply, readErr := cp.readReply(connD, 5*time.Second)
				cr := ChannelProbeResult{Channel: ch}
				if readErr != nil {
					cr.Error = fmt.Sprintf("read: %v", readErr)
					result.ChannelResults = append(result.ChannelResults, cr)
					break
				}
				if subReply != nil && subReply.Error != nil {
					cr.Error = subReply.Error.Message
					cr.ErrorCode = subReply.Error.Code
				} else {
					cr.Accessible = true
				}
				result.ChannelResults = append(result.ChannelResults, cr)
				cmdID++
			}
			connD.Close()
		}
	} else {
		result.Error = "all connect strategies failed"
	}

	return result, nil
}

func (cp *CentrifugeProbe) sendCommand(conn *websocket.Conn, cmd CentrifugeCommand) error {
	data, err := json.Marshal(cmd)
	if err != nil {
		return err
	}
	// Centrifuge uses newline-delimited JSON
	data = append(data, '\n')
	return conn.WriteMessage(websocket.TextMessage, data)
}

func (cp *CentrifugeProbe) parseReply(message []byte) (*CentrifugeReply, error) {
	lines := strings.Split(strings.TrimSpace(string(message)), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || line == "{}" {
			continue
		}
		var reply CentrifugeReply
		if err := json.Unmarshal([]byte(line), &reply); err != nil {
			return nil, fmt.Errorf("unmarshal reply: %w (raw: %s)", err, line)
		}
		return &reply, nil
	}
	return nil, fmt.Errorf("no valid reply in frame")
}

func (cp *CentrifugeProbe) readReply(conn *websocket.Conn, timeout time.Duration) (*CentrifugeReply, error) {
	conn.SetReadDeadline(time.Now().Add(timeout))
	_, message, err := conn.ReadMessage()
	if err != nil {
		return nil, err
	}
	return cp.parseReply(message)
}
