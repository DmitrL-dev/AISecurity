package judge

import (
	"os"
	"strconv"
	"strings"
)

// defaultGetenv is the production environment reader (os.Getenv). Indirected via
// the package-level Getenv var so tests can stub configuration without touching
// the process environment.
func defaultGetenv(key string) string { return os.Getenv(key) }

func envStr(key, def string) string {
	if v := Getenv(key); v != "" {
		return v
	}
	return def
}

// envBool parses the common truthy spellings (1/true/yes/on, case-insensitive);
// anything else (including unset/empty) yields def.
func envBool(key string, def bool) bool {
	v := strings.ToLower(strings.TrimSpace(Getenv(key)))
	if v == "" {
		return def
	}
	switch v {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return def
	}
}

func envFloat(key string, def float64) float64 {
	v := strings.TrimSpace(Getenv(key))
	if v == "" {
		return def
	}
	if f, err := strconv.ParseFloat(v, 64); err == nil {
		return f
	}
	return def
}

func envInt(key string, def int) int {
	v := strings.TrimSpace(Getenv(key))
	if v == "" {
		return def
	}
	if n, err := strconv.Atoi(v); err == nil {
		return n
	}
	return def
}
