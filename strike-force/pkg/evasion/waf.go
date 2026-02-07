package evasion

import (
	"fmt"
	"math/rand"
	"net/url"
	"strings"
	"unicode"
)

// WAFBypasser implements WAF evasion techniques
type WAFBypasser struct {
	aggression int
}

// NewWAFBypasser creates a new bypasser
func NewWAFBypasser(aggression int) *WAFBypasser {
	return &WAFBypasser{aggression: aggression}
}

// GenerateVariants generates multiple bypass payloads
func (w *WAFBypasser) GenerateVariants(payload string) []string {
	var variants []string

	// 1. URL Encoding
	variants = append(variants, w.urlEncode(payload))

	// 2. Double URL Encoding
	variants = append(variants, w.doubleUrlEncode(payload))

	// 3. Case Manipulation
	variants = append(variants, w.caseRandomize(payload))

	// 4. SQL Comment Injection
	variants = append(variants, w.sqlCommentInject(payload))

	// 5. Hex Encoding (0x...)
	variants = append(variants, w.hexEncode(payload))

	return variants
}

func (w *WAFBypasser) urlEncode(s string) string {
	return url.QueryEscape(s)
}

func (w *WAFBypasser) doubleUrlEncode(s string) string {
	return url.QueryEscape(url.QueryEscape(s))
}

func (w *WAFBypasser) caseRandomize(s string) string {
	var sb strings.Builder
	for _, r := range s {
		if unicode.IsLetter(r) {
			if rand.Float32() > 0.5 {
				sb.WriteRune(unicode.ToUpper(r))
			} else {
				sb.WriteRune(unicode.ToLower(r))
			}
		} else {
			sb.WriteRune(r)
		}
	}
	return sb.String()
}

func (w *WAFBypasser) sqlCommentInject(s string) string {
	keywords := []string{"SELECT", "UNION", "FROM", "WHERE", "AND", "OR"}
	res := s
	for _, kw := range keywords {
		// Simple injection: INSERT -> INS/**/ERT
		// Case insensitive check would be better, but this is a starter port
		if strings.Contains(strings.ToUpper(res), kw) {
			mid := len(kw) / 2
			replacement := kw[:mid] + "/**/" + kw[mid:]
			// Naive replacement for now
			res = strings.Replace(res, kw, replacement, -1)
		}
	}
	return res
}

func (w *WAFBypasser) hexEncode(s string) string {
	return "0x" + fmt.Sprintf("%x", s)
}
