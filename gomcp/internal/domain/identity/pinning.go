package identity

// Context-aware trimming with security event pinning (SDD-003 M5).
//
// Security events are pinned in context and exempt from trimming
// when the context window overflows. This prevents attackers from
// waiting for security events to be evicted.

// Message represents a context window message.
type Message struct {
	Role      string `json:"role"`       // "user", "assistant", "system", "security"
	Content   string `json:"content"`
	TokenCount int   `json:"token_count"`
	IsPinned  bool   `json:"is_pinned"`  // Security events are pinned
	EventType string `json:"event_type,omitempty"` // For security messages
}

// PinnedEventTypes are security events that MUST NOT be trimmed from context.
var PinnedEventTypes = map[string]bool{
	"permission_denied":        true,
	"injection_detected":       true,
	"circuit_breaker_open":     true,
	"credential_access_blocked": true,
	"exfiltration_attempt":     true,
	"ssrf_blocked":             true,
	"genai_credential_access":  true,
	"genai_persistence":        true,
}

// IsPinnedEvent returns true if the event type should be pinned (never trimmed).
func IsPinnedEvent(eventType string) bool {
	return PinnedEventTypes[eventType]
}

// TrimContext trims context messages to fit within maxTokens,
// preserving all pinned security events.
//
// Algorithm:
// 1. Separate pinned and unpinned messages
// 2. Calculate token budget remaining after pinned messages
// 3. Trim unpinned messages (oldest first) to fit budget
// 4. Merge: pinned messages in original positions + surviving unpinned
func TrimContext(messages []Message, maxTokens int) []Message {
	if len(messages) == 0 {
		return messages
	}

	// Calculate total tokens
	totalTokens := 0
	for _, m := range messages {
		totalTokens += m.TokenCount
	}

	// If within budget, return as-is
	if totalTokens <= maxTokens {
		return messages
	}

	// Separate pinned and unpinned, preserving original indices
	type indexedMsg struct {
		idx int
		msg Message
	}
	var pinned, unpinned []indexedMsg
	pinnedTokens := 0

	for i, m := range messages {
		if m.IsPinned || IsPinnedEvent(m.EventType) {
			pinned = append(pinned, indexedMsg{i, m})
			pinnedTokens += m.TokenCount
		} else {
			unpinned = append(unpinned, indexedMsg{i, m})
		}
	}

	// Budget for unpinned messages
	remainingBudget := maxTokens - pinnedTokens
	if remainingBudget < 0 {
		remainingBudget = 0
	}

	// Trim unpinned from the beginning (oldest first)
	var survivingUnpinned []indexedMsg
	usedTokens := 0
	// Keep messages from the END (newest) that fit
	for i := len(unpinned) - 1; i >= 0; i-- {
		if usedTokens + unpinned[i].msg.TokenCount <= remainingBudget {
			survivingUnpinned = append([]indexedMsg{unpinned[i]}, survivingUnpinned...)
			usedTokens += unpinned[i].msg.TokenCount
		}
	}

	// Merge by original index order
	all := append(pinned, survivingUnpinned...)
	// Sort by original index
	for i := 0; i < len(all); i++ {
		for j := i + 1; j < len(all); j++ {
			if all[j].idx < all[i].idx {
				all[i], all[j] = all[j], all[i]
			}
		}
	}

	result := make([]Message, len(all))
	for i, im := range all {
		result[i] = im.msg
	}
	return result
}
