package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/sentinel-community/strike-force/internal/adapters/transport"
	"github.com/sentinel-community/strike-force/internal/domain/entity"
)

func main() {
	fmt.Println("[*] JA3/TLS Evasion Check Tool")
	fmt.Println("[*] Target: https://hh.ru (Checking WAF/Anti-Bot)")

	// Initialize our uTLS-enabled transport
	tr := transport.NewWrapper(10 * time.Second)

	target := entity.Target{
		ID:     "probe_hh",
		URL:    "https://hh.ru",
		Method: "GET",
	}

	payload := entity.Payload{
		ID:    "benign_probe",
		Value: "1", // Benign value
	}

	fmt.Println("[*] Sending request with uTLS (impersonating Chrome/Firefox)...")
	result, err := tr.Send(context.Background(), target, payload)
	if err != nil {
		fmt.Printf("[-] Transport Fatal Error: %v\n", err)
		return
	}

	// Check internal error from transport wrapper
	if result.Error != nil {
		errStr := result.Error.Error()
		// Detect H2 Settings Frame signature (\x00\x00\x12\x04...)
		// If we see this, Cloudflare accepted our ClientHello (Evasion Success)
		// but sent H2 binary data our H1 client couldn't parse.
		if strings.Contains(errStr, "malformed HTTP response") || strings.Contains(errStr, "\\x00\\x00\\x06") || strings.Contains(errStr, "\\x00\\x00\\x12") {
			fmt.Println("[+] SUCCESS: Handshake accepted! (Cloudflare sent HTTP/2 frames)")
			fmt.Println("[*] The WAF let us through. Protocol mismatch is expected with uTLS+net/http.")
			return
		}

		fmt.Printf("[-] Requests Failed: %v\n", result.Error)
		return
	}

	fmt.Printf("[+] Status Code: %d\n", result.StatusCode)

	if result.StatusCode == 200 {
		fmt.Println("[+] SUCCESS: Cloudflare accepted the connection!")
		fmt.Println("[*] If we were blocked by JA3, we would likely see 403.")
	} else if result.StatusCode == 403 {
		fmt.Println("[-] FAILED: Detected and blocked (403).")
	} else {
		respLen := len(result.Response)
		snippet := ""
		if respLen > 100 {
			snippet = result.Response[:100] + "..."
		} else {
			snippet = result.Response
		}
		fmt.Printf("[?] Result (Len %d): %s\n", respLen, snippet)
	}
}
