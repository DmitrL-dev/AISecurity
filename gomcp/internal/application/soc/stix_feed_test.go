package soc

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- stixPatternToIOC ---

func TestSTIXPatternToIOC_IPv4(t *testing.T) {
	obj := STIXObject{
		Type:     "indicator",
		Pattern:  "[ipv4-addr:value = '192.168.1.1']",
		Modified: time.Now(),
	}
	ioc := stixPatternToIOC(obj)
	require.NotNil(t, ioc, "should parse IPv4 pattern")
	assert.Equal(t, IOCTypeIP, ioc.Type)
	assert.Equal(t, "192.168.1.1", ioc.Value)
	assert.Equal(t, "medium", ioc.Severity)
	assert.False(t, ioc.FirstSeen.IsZero(), "FirstSeen must be set")
}

func TestSTIXPatternToIOC_Hash(t *testing.T) {
	hash := "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
	obj := STIXObject{
		Type:     "indicator",
		Pattern:  "[file:hashes.'SHA-256' = '" + hash + "']",
		Modified: time.Now(),
		Labels:   []string{"malicious-activity"},
	}
	ioc := stixPatternToIOC(obj)
	require.NotNil(t, ioc, "should parse hash pattern")
	assert.Equal(t, IOCTypeHash, ioc.Type)
	assert.Equal(t, hash, ioc.Value)
	assert.Equal(t, "critical", ioc.Severity, "malicious-activity label → critical")
}

func TestSTIXPatternToIOC_Domain(t *testing.T) {
	obj := STIXObject{
		Type:     "indicator",
		Pattern:  "[domain-name:value = 'evil.example.com']",
		Modified: time.Now(),
		Labels:   []string{"attribution"},
	}
	ioc := stixPatternToIOC(obj)
	require.NotNil(t, ioc)
	assert.Equal(t, IOCTypeDomain, ioc.Type)
	assert.Equal(t, "evil.example.com", ioc.Value)
	assert.Equal(t, "high", ioc.Severity, "attribution label → high")
}

func TestSTIXPatternToIOC_Unsupported(t *testing.T) {
	obj := STIXObject{
		Type:     "indicator",
		Pattern:  "[email-addr:value = 'attacker@evil.com']",
		Modified: time.Now(),
	}
	ioc := stixPatternToIOC(obj)
	assert.Nil(t, ioc, "unsupported pattern type should return nil")
}

func TestSTIXPatternToIOC_FallbackToCreated(t *testing.T) {
	created := time.Date(2026, 1, 15, 0, 0, 0, 0, time.UTC)
	obj := STIXObject{
		Type:    "indicator",
		Pattern: "[ipv4-addr:value = '10.0.0.1']",
		Created: created,
		// Modified is zero → should fall back to Created
	}
	ioc := stixPatternToIOC(obj)
	require.NotNil(t, ioc)
	assert.Equal(t, created, ioc.FirstSeen, "should fall back to Created when Modified is zero")
}

// --- extractSTIXValue ---

func TestExtractSTIXValue(t *testing.T) {
	tests := []struct {
		name    string
		pattern string
		want    string
	}{
		{"ipv4", "[ipv4-addr:value = '1.2.3.4']", "1.2.3.4"},
		{"domain", "[domain-name:value = 'evil.com']", "evil.com"},
		{"hash", "[file:hashes.'SHA-256' = 'abc123']", "abc123"},
		{"empty_no_quotes", "[ipv4-addr:value = ]", ""},
		{"single_quote_only", "'", ""},
		{"empty_string", "", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractSTIXValue(tt.pattern)
			assert.Equal(t, tt.want, got)
		})
	}
}

// --- processBundle ---

func TestProcessBundle_FiltersNonIndicators(t *testing.T) {
	store := NewThreatIntelStore()
	fs := NewFeedSync(store, nil)

	bundle := STIXBundle{
		Type: "bundle",
		ID:   "bundle--test",
		Objects: []STIXObject{
			{Type: "indicator", Pattern: "[ipv4-addr:value = '10.0.0.1']", Modified: time.Now()},
			{Type: "malware", Name: "BadMalware"},   // should be skipped
			{Type: "indicator", Pattern: ""},          // empty pattern → skipped
			{Type: "attack-pattern", Name: "Phish"},   // should be skipped
			{Type: "indicator", Pattern: "[domain-name:value = 'bad.com']", Modified: time.Now()},
		},
	}

	imported := fs.processBundle("test-feed", bundle)
	assert.Equal(t, 2, imported, "should import only 2 valid indicators")
	assert.Equal(t, 2, store.TotalIOCs, "store should have 2 IOCs")
}

// --- DefaultOTXFeed ---

func TestDefaultOTXFeed(t *testing.T) {
	feed := DefaultOTXFeed("test-key-123")
	assert.Equal(t, "AlienVault OTX", feed.Name)
	assert.True(t, feed.Enabled, "should be enabled when key provided")
	assert.Contains(t, feed.URL, "otx.alienvault.com")
	assert.Equal(t, time.Hour, feed.Interval)
	assert.Equal(t, "test-key-123", feed.Headers["X-OTX-API-KEY"])

	disabled := DefaultOTXFeed("")
	assert.False(t, disabled.Enabled, "should be disabled when key is empty")
}
