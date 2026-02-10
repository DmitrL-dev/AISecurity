package tunnel

import (
	"context"
	"fmt"
	"io"
	"log"
	"net"
	"time"
)

// SOCKS5 protocol constants.
const (
	socks5Version = 0x05
	authNone      = 0x00
	cmdConnect    = 0x01
	atypIPv4      = 0x01
	atypDomain    = 0x03
	atypIPv6      = 0x04
	repSuccess    = 0x00
	repFailed     = 0x01
)

// Dialer is an interface for creating outbound connections.
// Implements support for uTLS stealth dialing.
type Dialer interface {
	DialContext(ctx context.Context, network, addr string) (net.Conn, error)
}

// SOCKS5Server is a local SOCKS5 proxy that forwards
// connections through a stealth dialer.
type SOCKS5Server struct {
	// ListenAddr is the local address to listen on.
	ListenAddr string

	// Upstream is the dialer used for outbound connections.
	// Can be a direct dialer or WSS tunnel client.
	Upstream Dialer

	// Logger for connection events.
	Logger *log.Logger
}

// NewSOCKS5Server creates a SOCKS5 server.
func NewSOCKS5Server(
	listenAddr string,
	upstream Dialer,
) *SOCKS5Server {
	return &SOCKS5Server{
		ListenAddr: listenAddr,
		Upstream:   upstream,
		Logger:     log.Default(),
	}
}

// ListenAndServe starts the SOCKS5 proxy.
func (s *SOCKS5Server) ListenAndServe(
	ctx context.Context,
) error {
	ln, err := net.Listen("tcp", s.ListenAddr)
	if err != nil {
		return fmt.Errorf("listen %s: %w", s.ListenAddr, err)
	}
	defer ln.Close()

	s.Logger.Printf("SOCKS5 listening on %s", s.ListenAddr)

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

// handleConn processes a single SOCKS5 connection.
func (s *SOCKS5Server) handleConn(
	ctx context.Context,
	conn net.Conn,
) {
	defer conn.Close()

	// 1. Greeting
	if err := s.readGreeting(conn); err != nil {
		s.Logger.Printf("greeting: %v", err)
		return
	}

	// 2. Send "no auth required"
	if _, err := conn.Write([]byte{
		socks5Version, authNone,
	}); err != nil {
		return
	}

	// 3. Read connect request
	targetAddr, err := s.readRequest(conn)
	if err != nil {
		s.Logger.Printf("request: %v", err)
		return
	}

	// 4. Dial upstream
	upConn, err := s.Upstream.DialContext(
		ctx, "tcp", targetAddr,
	)
	if err != nil {
		s.Logger.Printf("dial %s: %v", targetAddr, err)
		s.sendReply(conn, repFailed)
		return
	}
	defer upConn.Close()

	// 5. Send success reply
	s.sendReply(conn, repSuccess)

	s.Logger.Printf("tunnel: %s → %s",
		conn.RemoteAddr(), targetAddr)

	// 6. Bidirectional copy
	relay(conn, upConn)
}

// readGreeting reads the SOCKS5 greeting.
func (s *SOCKS5Server) readGreeting(
	conn net.Conn,
) error {
	buf := make([]byte, 2)
	if _, err := io.ReadFull(conn, buf); err != nil {
		return err
	}
	if buf[0] != socks5Version {
		return fmt.Errorf("unsupported version: %d", buf[0])
	}

	// Read and discard auth methods
	methods := make([]byte, buf[1])
	_, err := io.ReadFull(conn, methods)
	return err
}

// readRequest reads the SOCKS5 connect request.
func (s *SOCKS5Server) readRequest(
	conn net.Conn,
) (string, error) {
	// VER CMD RSV ATYP
	buf := make([]byte, 4)
	if _, err := io.ReadFull(conn, buf); err != nil {
		return "", err
	}

	if buf[1] != cmdConnect {
		return "", fmt.Errorf(
			"unsupported command: %d", buf[1],
		)
	}

	var host string
	switch buf[3] {
	case atypIPv4:
		ip := make([]byte, 4)
		if _, err := io.ReadFull(conn, ip); err != nil {
			return "", err
		}
		host = net.IP(ip).String()

	case atypDomain:
		lenBuf := make([]byte, 1)
		if _, err := io.ReadFull(conn, lenBuf); err != nil {
			return "", err
		}
		domain := make([]byte, lenBuf[0])
		if _, err := io.ReadFull(conn, domain); err != nil {
			return "", err
		}
		host = string(domain)

	case atypIPv6:
		ip := make([]byte, 16)
		if _, err := io.ReadFull(conn, ip); err != nil {
			return "", err
		}
		host = net.IP(ip).String()

	default:
		return "", fmt.Errorf(
			"unsupported atype: %d", buf[3],
		)
	}

	// Read port (2 bytes big-endian)
	portBuf := make([]byte, 2)
	if _, err := io.ReadFull(conn, portBuf); err != nil {
		return "", err
	}
	port := int(portBuf[0])<<8 | int(portBuf[1])

	return fmt.Sprintf("%s:%d", host, port), nil
}

// sendReply sends a SOCKS5 reply.
func (s *SOCKS5Server) sendReply(
	conn net.Conn,
	rep byte,
) {
	// VER REP RSV ATYP ADDR PORT
	reply := []byte{
		socks5Version, rep, 0x00,
		atypIPv4, 0, 0, 0, 0, 0, 0,
	}
	conn.Write(reply)
}

// relay copies data bidirectionally between two connections.
func relay(a, b net.Conn) {
	done := make(chan struct{}, 2)
	cp := func(dst, src net.Conn) {
		defer func() { done <- struct{}{} }()
		io.Copy(dst, src)
		// Signal EOF
		if tc, ok := dst.(*net.TCPConn); ok {
			tc.CloseWrite()
		}
	}
	go cp(a, b)
	go cp(b, a)
	<-done

	// Set short deadline on remaining direction
	a.SetDeadline(time.Now().Add(5 * time.Second))
	b.SetDeadline(time.Now().Add(5 * time.Second))
	<-done
}
