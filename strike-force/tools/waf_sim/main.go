package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"strings"
)

// Simple WAF Simulator
// Blocks "UNION" and "SELECT" unless encoded or obfuscated
func main() {
	silent := flag.Bool("silent", false, "Suppress logging for benchmarking")
	flag.Parse()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		query := r.URL.Query().Get("q")
		if query == "" {
			// Check body
			// simplified
		}

		decoded := query // Assume middleware handles decoding, but WAF often sees raw or semi-decoded

		if !*silent {
			fmt.Printf("[WAF] Received: %s\n", query)
		}

		// 1. Signature Check (Basic) - what Artemis should learn to avoid
		if strings.Contains(strings.ToUpper(decoded), "UNION") || strings.Contains(strings.ToUpper(decoded), "SELECT") {
			// 2. Evasion Check (Advanced) - what Artemis/Evasion should achieve
			// If it contains "/**/" (Comments) OR "%00" (Nulls), we let it pass (Simulated WAF Bypass)
			if strings.Contains(decoded, "/**/") || strings.Contains(decoded, "%00") {
				w.WriteHeader(200)
				w.Write([]byte("WAF_BYPASS_SUCCESS: You tricked me!"))
				log.Printf("[WAF] BYPASSED by %s\n", query)
				return
			}

			w.WriteHeader(403)
			w.Write([]byte("WAF_BLOCK: Malicious SQL Query Detected"))
			log.Printf("[WAF] BLOCKED %s\n", query)
			return
		}

		w.WriteHeader(200)
		w.Write([]byte("OK"))
	})

	fmt.Println("[*] WAF Simulator listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
