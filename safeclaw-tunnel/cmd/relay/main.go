package main

import (
	"flag"
	"fmt"
	"log"
	"os"

	"github.com/AISecurity/safeclaw-tunnel/internal/tunnel"
)

func main() {
	listen := flag.String(
		"listen", ":443",
		"Relay listen address",
	)
	cert := flag.String(
		"cert", "",
		"TLS certificate file",
	)
	key := flag.String(
		"key", "",
		"TLS private key file",
	)
	ver := flag.Bool(
		"version", false,
		"Show version",
	)

	flag.Parse()

	if *ver {
		fmt.Println("safeclaw-relay v0.1.0")
		os.Exit(0)
	}

	logger := log.New(
		os.Stdout, "[relay] ",
		log.LstdFlags|log.Lshortfile,
	)

	relay := tunnel.NewWSSRelay(
		*listen, *cert, *key,
	)

	logger.Printf("SafeClaw Relay on %s", *listen)
	if *cert != "" {
		logger.Printf("TLS: %s", *cert)
	} else {
		logger.Println("WARNING: No TLS — use reverse proxy")
	}

	if err := relay.ListenAndServe(); err != nil {
		logger.Fatalf("Fatal: %v", err)
	}
}
