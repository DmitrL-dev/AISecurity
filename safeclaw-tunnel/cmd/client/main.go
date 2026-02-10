package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/AISecurity/safeclaw-tunnel/internal/tunnel"
)

var (
	version = "0.1.0"
	banner  = `
╔═══════════════════════════════════════╗
║  SafeClaw Tunnel v%s               ║
║  Stealth proxy for AI infrastructure ║
║  github.com/AISecurity/safeclaw      ║
╚═══════════════════════════════════════╝
`
)

func main() {
	listen := flag.String(
		"listen", ":1080",
		"SOCKS5 listen address",
	)
	relayURL := flag.String(
		"relay", "",
		"WSS relay URL (e.g. wss://relay.example.com/tunnel)",
	)
	doh := flag.Bool(
		"doh", true,
		"Use DNS-over-HTTPS (Cloudflare)",
	)
	ver := flag.Bool(
		"version", false,
		"Show version",
	)

	flag.Parse()

	if *ver {
		fmt.Printf("safeclaw-tunnel v%s\n", version)
		os.Exit(0)
	}

	fmt.Printf(banner, version)

	logger := log.New(
		os.Stdout, "[safeclaw] ",
		log.LstdFlags|log.Lshortfile,
	)

	// Choose upstream dialer
	var upstream tunnel.Dialer
	if *relayURL != "" {
		logger.Printf("Mode: RELAY via %s", *relayURL)
		upstream = tunnel.NewWSSClient(*relayURL)
	} else {
		logger.Printf("Mode: DIRECT (no relay)")
		upstream = tunnel.NewDirectDialer()
	}

	_ = doh // TODO: integrate DoH resolver into dialer

	// Create SOCKS5 server
	srv := tunnel.NewSOCKS5Server(*listen, upstream)
	srv.Logger = logger

	// Graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigCh
		logger.Printf("Signal %v, shutting down...", sig)
		cancel()
	}()

	// Start
	logger.Printf("SOCKS5 proxy on %s", *listen)
	if *relayURL != "" {
		logger.Printf(
			"Configure Telegram: SOCKS5 → 127.0.0.1%s",
			*listen,
		)
	}

	if err := srv.ListenAndServe(ctx); err != nil {
		if ctx.Err() != nil {
			logger.Println("Shutdown complete")
		} else {
			logger.Fatalf("Fatal: %v", err)
		}
	}
}
