package transport

import (
	"fmt"
	"sort"
	"strings"
)

// ============================================================================
// CHROME HEADER ORDER — Cloudflare Enterprise Detection Evasion
// ============================================================================
// Go's net/http sorts headers alphabetically by key. Chrome sends headers
// in a FIXED, NON-ALPHABETICAL order. Cloudflare Enterprise and Akamai
// check this order to detect non-browser clients.
//
// This module provides Chrome's exact header order and a builder
// that outputs raw HTTP headers in the correct sequence.
// ============================================================================

// ChromeHeaderOrder returns Chrome 131-133's HTTP header order.
// Extracted from real Chrome traffic captures (GET request).
func ChromeHeaderOrder() []string {
	return []string{
		"Host",
		"Connection",
		"sec-ch-ua",
		"sec-ch-ua-mobile",
		"sec-ch-ua-platform",
		"Upgrade-Insecure-Requests",
		"User-Agent",
		"Accept",
		"Sec-Fetch-Site",
		"Sec-Fetch-Mode",
		"Sec-Fetch-User",
		"Sec-Fetch-Dest",
		"Accept-Encoding",
		"Accept-Language",
		"Cookie",
		"Priority",
	}
}

// headerOrderIndex maps Chrome's header order to numeric indices.
func headerOrderIndex() map[string]int {
	order := ChromeHeaderOrder()
	idx := make(map[string]int, len(order))
	for i, h := range order {
		idx[strings.ToLower(h)] = i
	}
	return idx
}

// BuildOrderedHeaders builds raw HTTP header lines in Chrome's order.
// Known Chrome headers are emitted first in Chrome's order,
// unknown headers are appended at the end alphabetically.
func BuildOrderedHeaders(headers map[string]string) string {
	idx := headerOrderIndex()

	type kv struct {
		key   string
		value string
		order int
	}

	pairs := make([]kv, 0, len(headers))
	for k, v := range headers {
		o, known := idx[strings.ToLower(k)]
		if !known {
			o = 1000 // Unknown headers go after Chrome headers
		}
		pairs = append(pairs, kv{key: k, value: v, order: o})
	}

	// Sort: Chrome order first, then alphabetically for unknowns
	sort.Slice(pairs, func(i, j int) bool {
		if pairs[i].order != pairs[j].order {
			return pairs[i].order < pairs[j].order
		}
		return pairs[i].key < pairs[j].key
	})

	var b strings.Builder
	for _, p := range pairs {
		fmt.Fprintf(&b, "%s: %s\r\n", p.key, p.value)
	}
	return b.String()
}
