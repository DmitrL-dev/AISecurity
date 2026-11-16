package httpserver

import (
	"strings"
	"testing"
)

// Regression for the mega-review 17.06 LOW (defense-in-depth): the ingest
// secret-scanner INVARIANT only covers Payload, so the gateway->SOC seam must
// itself guard the indicators it packs into Metadata. If an engine ever regresses
// to echo a raw secret into an indicator, it must NOT be persisted into the SOC.
func TestBuildScanSOCEvent_RedactsSecretInIndicators(t *testing.T) {
	secret := "sk-" + strings.Repeat("A", 40) // matches the OpenAI-key pattern in oracle.ScanForSecrets
	evt := buildScanSOCEvent("tnt-1", "injection", 0.95, "prompt", []string{"core/jb", "leaked=" + secret})

	got := evt.Metadata["indicators"]
	if strings.Contains(got, secret) {
		t.Fatalf("secret leaked into indicators metadata: %q", got)
	}
	if !strings.Contains(got, "redacted") {
		t.Fatalf("expected the indicators to be redacted, got %q", got)
	}
}
