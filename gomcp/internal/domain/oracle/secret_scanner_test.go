package oracle

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestScanForSecrets_CleanCode(t *testing.T) {
	code := `package main

import "fmt"

func main() {
	fmt.Println("hello world")
	x := 42
	y := x + 1
}
`
	result := ScanForSecrets(code)
	assert.False(t, result.HasSecrets, "clean code should not trigger")
	assert.Empty(t, result.Detections)
}

func TestScanForSecrets_APIKey(t *testing.T) {
	code := `config := map[string]string{
	"api_key": "sk-1234567890abcdefghijklmnopqrstuv",
}`
	result := ScanForSecrets(code)
	assert.True(t, result.HasSecrets, "API key should be detected")
	assert.NotEmpty(t, result.Detections)

	found := false
	for _, d := range result.Detections {
		if strings.Contains(d, "PATTERN") {
			found = true
		}
	}
	assert.True(t, found, "should have PATTERN detection")
}

func TestScanForSecrets_GitHubPAT(t *testing.T) {
	code := `TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
`
	result := ScanForSecrets(code)
	assert.True(t, result.HasSecrets)
}

func TestScanForSecrets_OpenAIKey(t *testing.T) {
	code := `OPENAI_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456789"`
	result := ScanForSecrets(code)
	assert.True(t, result.HasSecrets)
}

func TestScanForSecrets_PrivateKey(t *testing.T) {
	code := `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...etc
-----END RSA PRIVATE KEY-----`
	result := ScanForSecrets(code)
	assert.True(t, result.HasSecrets)
}

func TestScanForSecrets_HighEntropyLine(t *testing.T) {
	// Random-looking base64 string (high entropy).
	code := `data = "aJ7kL9mX2pQwR5tY8vB3nZ0cF6gH1iE4dA-s_uO+M/W*xU@!%^&"`
	result := ScanForSecrets(code)
	assert.True(t, result.HasSecrets, "high entropy line should trigger")
	assert.Greater(t, result.MaxEntropy, 4.0)
}

func TestScanForSecrets_CommentsIgnored(t *testing.T) {
	code := `// api_key = "sk-1234567890abcdefghijklmnopqrstuv"
# secret = "very-long-secret-value-that-should-be-ignored"
`
	result := ScanForSecrets(code)
	// Pattern matching still catches it in the raw content,
	// but entropy check skips comments.
	// The pattern matcher scans raw content, so this WILL trigger.
	assert.True(t, result.HasSecrets)
}

func TestScanForSecrets_DBConnectionString(t *testing.T) {
	code := `dsn := "postgres://user:password@localhost:5432/mydb?sslmode=disable"`
	result := ScanForSecrets(code)
	assert.True(t, result.HasSecrets)
}

func TestScanForSecrets_ScannerRuleCount(t *testing.T) {
	result := ScanForSecrets("")
	assert.Equal(t, 8, result.ScannerRules, "should have 8 pattern rules")
}
