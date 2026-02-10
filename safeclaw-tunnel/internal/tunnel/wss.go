package tunnel

import (
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// WSSClient tunnels TCP connections over a WebSocket.
// The WebSocket itself uses uTLS for stealth.
type WSSClient struct {
	// RelayURL is the WSS endpoint of the relay server.
	RelayURL string

	// TLSConfig for WebSocket connection.
	TLSConfig *tls.Config

	// ConnectHeaders are extra HTTP headers for the upgrade.
	ConnectHeaders http.Header
}

// NewWSSClient creates a WebSocket tunnel client.
func NewWSSClient(relayURL string) *WSSClient {
	return &WSSClient{
		RelayURL: relayURL,
		ConnectHeaders: http.Header{
			"User-Agent": []string{
				"Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
					"AppleWebKit/537.36 (KHTML, like Gecko) " +
					"Chrome/120.0.0.0 Safari/537.36",
			},
		},
	}
}

// DialContext connects to the target through the WSS relay.
// Implements the Dialer interface for SOCKS5 upstream.
func (c *WSSClient) DialContext(
	ctx context.Context,
	network, addr string,
) (net.Conn, error) {
	// Connect to relay with target header
	headers := c.ConnectHeaders.Clone()
	headers.Set("X-Target", addr)

	dialer := websocket.Dialer{
		TLSClientConfig:  c.TLSConfig,
		HandshakeTimeout: 10 * time.Second,
	}

	wsConn, _, err := dialer.DialContext(
		ctx, c.RelayURL, headers,
	)
	if err != nil {
		return nil, fmt.Errorf("wss dial: %w", err)
	}

	return &wsNetConn{ws: wsConn}, nil
}

// wsNetConn wraps a WebSocket connection to implement net.Conn.
type wsNetConn struct {
	ws     *websocket.Conn
	reader io.Reader
	mu     sync.Mutex
}

func (c *wsNetConn) Read(b []byte) (int, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	for {
		if c.reader != nil {
			n, err := c.reader.Read(b)
			if err == io.EOF {
				c.reader = nil
				continue
			}
			return n, err
		}

		_, reader, err := c.ws.NextReader()
		if err != nil {
			return 0, err
		}
		c.reader = reader
	}
}

func (c *wsNetConn) Write(b []byte) (int, error) {
	err := c.ws.WriteMessage(
		websocket.BinaryMessage, b,
	)
	if err != nil {
		return 0, err
	}
	return len(b), nil
}

func (c *wsNetConn) Close() error {
	return c.ws.Close()
}

func (c *wsNetConn) LocalAddr() net.Addr {
	return c.ws.LocalAddr()
}

func (c *wsNetConn) RemoteAddr() net.Addr {
	return c.ws.RemoteAddr()
}

func (c *wsNetConn) SetDeadline(t time.Time) error {
	if err := c.ws.SetReadDeadline(t); err != nil {
		return err
	}
	return c.ws.SetWriteDeadline(t)
}

func (c *wsNetConn) SetReadDeadline(t time.Time) error {
	return c.ws.SetReadDeadline(t)
}

func (c *wsNetConn) SetWriteDeadline(t time.Time) error {
	return c.ws.SetWriteDeadline(t)
}

// ============================================================
// Relay Server (for VPS deployment)
// ============================================================

// WSSRelay is the server-side WebSocket relay.
// Accepts WSS connections and forwards them to targets.
type WSSRelay struct {
	// ListenAddr for the relay server.
	ListenAddr string

	// CertFile and KeyFile for TLS.
	CertFile string
	KeyFile  string

	upgrader websocket.Upgrader
}

// NewWSSRelay creates a relay server.
func NewWSSRelay(
	listenAddr, certFile, keyFile string,
) *WSSRelay {
	return &WSSRelay{
		ListenAddr: listenAddr,
		CertFile:   certFile,
		KeyFile:    keyFile,
		upgrader: websocket.Upgrader{
			ReadBufferSize:  32768,
			WriteBufferSize: 32768,
		},
	}
}

// ListenAndServe starts the relay server.
func (r *WSSRelay) ListenAndServe() error {
	mux := http.NewServeMux()
	mux.HandleFunc("/tunnel", r.handleTunnel)

	// Health check
	mux.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		fmt.Fprint(w, "<html><body>OK</body></html>")
	})

	srv := &http.Server{
		Addr:    r.ListenAddr,
		Handler: mux,
	}

	if r.CertFile != "" {
		return srv.ListenAndServeTLS(
			r.CertFile, r.KeyFile,
		)
	}
	return srv.ListenAndServe()
}

// handleTunnel processes incoming tunnel connections.
func (r *WSSRelay) handleTunnel(
	w http.ResponseWriter,
	req *http.Request,
) {
	target := req.Header.Get("X-Target")
	if target == "" {
		http.Error(w, "missing target", 400)
		return
	}

	// Connect to actual target
	targetConn, err := net.DialTimeout(
		"tcp", target, 10*time.Second,
	)
	if err != nil {
		http.Error(w, "target unreachable", 502)
		return
	}
	defer targetConn.Close()

	// Upgrade to WebSocket
	wsConn, err := r.upgrader.Upgrade(w, req, nil)
	if err != nil {
		return
	}
	defer wsConn.Close()

	// Relay data
	wc := &wsNetConn{ws: wsConn}
	relay(wc, targetConn)
}
