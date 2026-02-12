package tunnel

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"strings"
	"time"
)

// HTTPProxyServer is an HTTP CONNECT proxy that forwards
// connections through the upstream Dialer.
// Works with Windows system proxy settings.
type HTTPProxyServer struct {
	ListenAddr string
	Upstream   Dialer
	Logger     *log.Logger
}

// NewHTTPProxyServer creates an HTTP CONNECT proxy.
func NewHTTPProxyServer(
	listenAddr string,
	upstream Dialer,
) *HTTPProxyServer {
	return &HTTPProxyServer{
		ListenAddr: listenAddr,
		Upstream:   upstream,
		Logger:     log.Default(),
	}
}

// ListenAndServe starts the HTTP proxy.
func (s *HTTPProxyServer) ListenAndServe(
	ctx context.Context,
) error {
	ln, err := net.Listen("tcp", s.ListenAddr)
	if err != nil {
		return fmt.Errorf("listen %s: %w", s.ListenAddr, err)
	}
	defer ln.Close()

	s.Logger.Printf("HTTP proxy listening on %s", s.ListenAddr)

	go func() {
		<-ctx.Done()
		ln.Close()
	}()

	for {
		conn, err := ln.Accept()
		if err != nil {
			select {
			case <-ctx.Done():
				return ctx.Err()
			default:
				s.Logger.Printf("accept error: %v", err)
				continue
			}
		}
		go s.handleConn(ctx, conn)
	}
}

// handleConn processes a single HTTP proxy connection.
func (s *HTTPProxyServer) handleConn(
	ctx context.Context,
	conn net.Conn,
) {
	defer conn.Close()

	br := bufio.NewReader(conn)
	req, err := http.ReadRequest(br)
	if err != nil {
		s.Logger.Printf("read request: %v", err)
		return
	}

	if req.Method == http.MethodConnect {
		s.handleConnect(ctx, conn, req)
	} else {
		s.handleHTTP(ctx, conn, req, br)
	}
}

// handleConnect handles HTTPS tunneling via CONNECT method.
func (s *HTTPProxyServer) handleConnect(
	ctx context.Context,
	conn net.Conn,
	req *http.Request,
) {
	targetAddr := req.Host
	if !strings.Contains(targetAddr, ":") {
		targetAddr += ":443"
	}

	// Dial upstream
	upConn, err := s.Upstream.DialContext(
		ctx, "tcp", targetAddr,
	)
	if err != nil {
		s.Logger.Printf("dial %s: %v", targetAddr, err)
		fmt.Fprintf(conn,
			"HTTP/1.1 502 Bad Gateway\r\n\r\n",
		)
		return
	}
	defer upConn.Close()

	// Send 200 Connection Established
	fmt.Fprintf(conn,
		"HTTP/1.1 200 Connection Established\r\n\r\n",
	)

	s.Logger.Printf("tunnel: %s → %s",
		conn.RemoteAddr(), targetAddr)

	// Bidirectional copy
	relay(conn, upConn)
}

// handleHTTP handles plain HTTP requests (non-CONNECT).
func (s *HTTPProxyServer) handleHTTP(
	ctx context.Context,
	clientConn net.Conn,
	req *http.Request,
	br *bufio.Reader,
) {
	targetAddr := req.Host
	if !strings.Contains(targetAddr, ":") {
		targetAddr += ":80"
	}

	// Dial upstream
	upConn, err := s.Upstream.DialContext(
		ctx, "tcp", targetAddr,
	)
	if err != nil {
		s.Logger.Printf("dial %s: %v", targetAddr, err)
		fmt.Fprintf(clientConn,
			"HTTP/1.1 502 Bad Gateway\r\n\r\n",
		)
		return
	}
	defer upConn.Close()

	// Rewrite request URL to relative path
	req.RequestURI = req.URL.Path
	if req.URL.RawQuery != "" {
		req.RequestURI += "?" + req.URL.RawQuery
	}

	// Forward request
	if err := req.Write(upConn); err != nil {
		s.Logger.Printf("write request: %v", err)
		return
	}

	s.Logger.Printf("http: %s → %s%s",
		clientConn.RemoteAddr(), targetAddr, req.URL.Path)

	// Set deadline and copy response
	upConn.SetDeadline(
		time.Now().Add(30 * time.Second),
	)
	io.Copy(clientConn, upConn)
}
