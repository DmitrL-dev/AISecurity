package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"

	"github.com/AISecurity/safeclaw-tunnel/internal/tunnel"
)

var (
	version = "0.3.0"
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
	httpListen := flag.String(
		"http", ":8118",
		"HTTP CONNECT proxy address (for Windows system proxy)",
	)
	relayURL := flag.String(
		"relay", "",
		"WSS relay URL (e.g. wss://relay.example.com/tunnel)",
	)
	proxyList := flag.String(
		"proxies", "",
		"Upstream SOCKS5 proxies (user:pass@host:port#country), comma-separated",
	)
	proxyFile := flag.String(
		"proxy-file", "",
		"File with upstream proxies (one per line: user:pass@host:port#country)",
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

	switch {
	case *proxyList != "":
		raw := strings.ReplaceAll(*proxyList, ",", "\n")
		proxies := tunnel.ParseProxyList(raw)
		if len(proxies) == 0 {
			logger.Fatal("No valid proxies in -proxies")
		}
		upstream = tunnel.NewProxyRotator(proxies, logger)
		logger.Printf(
			"Mode: PROXY ROTATION (%d proxies)",
			len(proxies),
		)
		for i, p := range proxies {
			logger.Printf(
				"  [%d] %s (%s)", i+1, p.Addr, p.Country,
			)
		}

	case *proxyFile != "":
		data, err := os.ReadFile(*proxyFile)
		if err != nil {
			logger.Fatalf("Read proxy file: %v", err)
		}
		proxies := tunnel.ParseProxyList(string(data))
		if len(proxies) == 0 {
			logger.Fatal("No valid proxies in file")
		}
		upstream = tunnel.NewProxyRotator(proxies, logger)
		logger.Printf(
			"Mode: PROXY ROTATION (%d proxies from %s)",
			len(proxies), *proxyFile,
		)
		for i, p := range proxies {
			logger.Printf(
				"  [%d] %s (%s)", i+1, p.Addr, p.Country,
			)
		}

	case *relayURL != "":
		logger.Printf("Mode: RELAY via %s", *relayURL)
		upstream = tunnel.NewWSSClient(*relayURL)

	default:
		logger.Printf("Mode: DIRECT (no relay)")
		upstream = tunnel.NewDirectDialer()
	}

	_ = doh // TODO: integrate DoH resolver into dialer

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

	var wg sync.WaitGroup

	// Start SOCKS5 proxy
	socks := tunnel.NewSOCKS5Server(*listen, upstream)
	socks.Logger = logger
	logger.Printf("SOCKS5 proxy on %s", *listen)

	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := socks.ListenAndServe(ctx); err != nil {
			if ctx.Err() == nil {
				logger.Printf("SOCKS5 error: %v", err)
			}
		}
	}()

	// Start HTTP CONNECT proxy
	httpProxy := tunnel.NewHTTPProxyServer(
		*httpListen, upstream,
	)
	httpProxy.Logger = logger
	logger.Printf("HTTP  proxy on %s (for Windows/browser)", *httpListen)

	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := httpProxy.ListenAndServe(ctx); err != nil {
			if ctx.Err() == nil {
				logger.Printf("HTTP proxy error: %v", err)
			}
		}
	}()

	logger.Printf("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	logger.Printf("Windows proxy: 127.0.0.1%s", *httpListen)
	logger.Printf("SOCKS5 proxy:  127.0.0.1%s", *listen)
	logger.Printf("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

	wg.Wait()
	logger.Println("Shutdown complete")
}
