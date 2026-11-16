package soc

import (
	"testing"
	"time"
)

// === GenAI Monitor Tests ===

func TestIsGenAIProcess(t *testing.T) {
	tests := []struct {
		name     string
		process  string
		expected bool
	}{
		{"claude detected", "claude", true},
		{"cursor detected", "cursor", true},
		{"Cursor Helper detected", "Cursor Helper", true},
		{"copilot detected", "copilot", true},
		{"windsurf detected", "windsurf", true},
		{"gemini detected", "gemini", true},
		{"aider detected", "aider", true},
		{"codex detected", "codex", true},
		{"normal process ignored", "python3", false},
		{"vim ignored", "vim", false},
		{"empty string ignored", "", false},
		{"partial match rejected", "claud", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := IsGenAIProcess(tt.process)
			if got != tt.expected {
				t.Errorf("IsGenAIProcess(%q) = %v, want %v", tt.process, got, tt.expected)
			}
		})
	}
}

func TestIsCredentialFile(t *testing.T) {
	tests := []struct {
		name     string
		path     string
		expected bool
	}{
		{"credentials.db", "/home/user/.config/google-chrome/Default/credentials.db", true},
		{"Cookies", "/home/user/.config/chromium/Default/Cookies", true},
		{"Login Data", "/home/user/.config/google-chrome/Default/Login Data", true},
		{"logins.json", "/home/user/.mozilla/firefox/profile/logins.json", true},
		{"ssh key", "/home/user/.ssh/id_rsa", true},
		{"aws credentials", "/home/user/.aws/credentials", true},
		{"env file", "/app/.env", true},
		{"normal file ignored", "/home/user/document.txt", false},
		{"code file ignored", "/home/user/project/main.go", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := IsCredentialFile(tt.path)
			if got != tt.expected {
				t.Errorf("IsCredentialFile(%q) = %v, want %v", tt.path, got, tt.expected)
			}
		})
	}
}

func TestIsLLMEndpoint(t *testing.T) {
	tests := []struct {
		name     string
		domain   string
		expected bool
	}{
		{"anthropic", "api.anthropic.com", true},
		{"openai", "api.openai.com", true},
		{"gemini", "gemini.googleapis.com", true},
		{"deepseek", "api.deepseek.com", true},
		{"normal domain", "google.com", false},
		{"github", "api.github.com", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := IsLLMEndpoint(tt.domain)
			if got != tt.expected {
				t.Errorf("IsLLMEndpoint(%q) = %v, want %v", tt.domain, got, tt.expected)
			}
		})
	}
}

func TestProcessAncestryHasGenAIAncestor(t *testing.T) {
	tests := []struct {
		name     string
		ancestry ProcessAncestry
		expected bool
	}{
		{
			"claude parent",
			ProcessAncestry{ParentName: "claude", Ancestry: []string{"zsh", "login"}},
			true,
		},
		{
			"claude in ancestry chain",
			ProcessAncestry{ParentName: "python3", Ancestry: []string{"claude", "zsh", "login"}},
			true,
		},
		{
			"no genai ancestor",
			ProcessAncestry{ParentName: "bash", Ancestry: []string{"sshd", "login"}},
			false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := tt.ancestry.HasGenAIAncestor()
			if got != tt.expected {
				t.Errorf("HasGenAIAncestor() = %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestGenAIAncestorName(t *testing.T) {
	p := ProcessAncestry{ParentName: "python3", Ancestry: []string{"cursor", "zsh"}}
	if name := p.GenAIAncestorName(); name != "cursor" {
		t.Errorf("GenAIAncestorName() = %q, want %q", name, "cursor")
	}
}

// === GenAI Rules Tests ===

func TestGenAICorrelationRulesCount(t *testing.T) {
	rules := GenAICorrelationRules()
	if len(rules) != 6 {
		t.Errorf("GenAICorrelationRules() returned %d rules, want 6", len(rules))
	}
}

func TestAllSOCCorrelationRulesCount(t *testing.T) {
	rules := AllSOCCorrelationRules()
	// 15 default + 2 Shadow AI + 6 GenAI = 23
	if len(rules) != 23 {
		t.Errorf("AllSOCCorrelationRules() returned %d rules, want 23", len(rules))
	}
}

func TestGenAIChildProcessRule(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{
			Source:    SourceImmune,
			Category: CategoryGenAIChildProcess,
			Severity: SeverityInfo,
			Timestamp: now.Add(-30 * time.Second),
			Metadata: map[string]string{
				"parent_process": "claude",
				"child_process":  "python3",
			},
		},
	}
	rules := GenAICorrelationRules()
	matches := CorrelateSOCEvents(events, rules[:1]) // R1 only
	if len(matches) != 1 {
		t.Fatalf("expected 1 match for GenAI child process, got %d", len(matches))
	}
	if matches[0].Rule.ID != "SOC-CR-016" {
		t.Errorf("expected SOC-CR-016, got %s", matches[0].Rule.ID)
	}
}

func TestGenAISuspiciousDescendantRule(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{
			Source:    SourceImmune,
			Category: CategoryGenAIChildProcess,
			Severity: SeverityInfo,
			Timestamp: now.Add(-3 * time.Minute),
		},
		{
			Source:    SourceImmune,
			Category: "tool_abuse",
			Severity: SeverityMedium,
			Timestamp: now.Add(-1 * time.Minute),
		},
	}
	rules := GenAICorrelationRules()
	matches := CorrelateSOCEvents(events, rules[1:2]) // R2 only
	if len(matches) != 1 {
		t.Fatalf("expected 1 match for GenAI suspicious descendant, got %d", len(matches))
	}
	if matches[0].Rule.ID != "SOC-CR-017" {
		t.Errorf("expected SOC-CR-017, got %s", matches[0].Rule.ID)
	}
}

func TestGenAICredentialAccessRule(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{
			Source:    SourceImmune,
			Category: CategoryGenAIChildProcess,
			Severity: SeverityInfo,
			Timestamp: now.Add(-1 * time.Minute),
		},
		{
			Source:    SourceImmune,
			Category: CategoryGenAICredentialAccess,
			Severity: SeverityCritical,
			Timestamp: now.Add(-30 * time.Second),
			Metadata: map[string]string{
				"file_path": "/home/user/.config/google-chrome/Default/Login Data",
			},
		},
	}
	rules := GenAICorrelationRules()
	matches := CorrelateSOCEvents(events, rules[3:4]) // R4 only
	if len(matches) != 1 {
		t.Fatalf("expected 1 match for GenAI credential access, got %d", len(matches))
	}
	if matches[0].Rule.Severity != SeverityCritical {
		t.Errorf("expected CRITICAL severity, got %s", matches[0].Rule.Severity)
	}
}

func TestGenAICredentialAccessAutoKill(t *testing.T) {
	match := CorrelationMatch{
		Rule: SOCCorrelationRule{ID: "SOC-CR-019"},
	}
	action := EvaluateGenAIAutoResponse(match)
	if action == nil {
		t.Fatal("expected auto-response for SOC-CR-019, got nil")
	}
	if action.Type != "kill_process" {
		t.Errorf("expected kill_process, got %s", action.Type)
	}
}

func TestGenAIPersistenceRule(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{
			Source:    SourceImmune,
			Category: CategoryGenAIChildProcess,
			Severity: SeverityInfo,
			Timestamp: now.Add(-8 * time.Minute),
		},
		{
			Source:    SourceImmune,
			Category: CategoryGenAIPersistence,
			Severity: SeverityHigh,
			Timestamp: now.Add(-2 * time.Minute),
		},
	}
	rules := GenAICorrelationRules()
	matches := CorrelateSOCEvents(events, rules[4:5]) // R5 only
	if len(matches) != 1 {
		t.Fatalf("expected 1 match for GenAI persistence, got %d", len(matches))
	}
	if matches[0].Rule.ID != "SOC-CR-020" {
		t.Errorf("expected SOC-CR-020, got %s", matches[0].Rule.ID)
	}
}

func TestGenAIConfigModificationRule(t *testing.T) {
	now := time.Now()
	events := []SOCEvent{
		{
			Source:    SourceImmune,
			Category: CategoryGenAIConfigModification,
			Severity: SeverityMedium,
			Timestamp: now.Add(-2 * time.Minute),
		},
	}
	rules := GenAICorrelationRules()
	matches := CorrelateSOCEvents(events, rules[5:6]) // R6 only
	if len(matches) != 1 {
		t.Fatalf("expected 1 match for GenAI config modification, got %d", len(matches))
	}
}

func TestGenAINonGenAIProcessIgnored(t *testing.T) {
	now := time.Now()
	// Normal process events should not trigger GenAI rules
	events := []SOCEvent{
		{
			Source:    SourceSentinelCore,
			Category: "prompt_injection",
			Severity: SeverityHigh,
			Timestamp: now.Add(-1 * time.Minute),
		},
	}
	rules := GenAICorrelationRules()
	matches := CorrelateSOCEvents(events, rules)
	// None of the 6 GenAI rules should fire on a regular prompt_injection event
	for _, m := range matches {
		if m.Rule.ID >= "SOC-CR-016" && m.Rule.ID <= "SOC-CR-021" {
			t.Errorf("GenAI rule %s should not fire on non-GenAI event", m.Rule.ID)
		}
	}
}

func TestGenAINoAutoResponseForNonCredentialRules(t *testing.T) {
	// Rules other than SOC-CR-019 should NOT have auto-response
	nonAutoRuleIDs := []string{"SOC-CR-016", "SOC-CR-017", "SOC-CR-018", "SOC-CR-020", "SOC-CR-021"}
	for _, ruleID := range nonAutoRuleIDs {
		match := CorrelationMatch{
			Rule: SOCCorrelationRule{ID: ruleID},
		}
		action := EvaluateGenAIAutoResponse(match)
		if action != nil {
			t.Errorf("rule %s should NOT have auto-response, got %+v", ruleID, action)
		}
	}
}
