package soc

// GenAI Process Monitoring & Detection
//
// Defines GenAI-specific process names, credential files, LLM DNS endpoints,
// and auto-response actions for GenAI EDR (SDD-001).

// GenAIProcessNames is the canonical list of GenAI IDE agent process names.
// Used by IMMUNE eBPF hooks and GoMCP SOC correlation rules.
var GenAIProcessNames = []string{
	"claude",
	"cursor",
	"Cursor Helper",
	"Cursor Helper (Plugin)",
	"copilot",
	"copilot-agent",
	"windsurf",
	"gemini",
	"aider",
	"continue",
	"cline",
	"codex",
	"codex-cli",
}

// CredentialFiles is the list of sensitive files monitored for GenAI access.
// Access by a GenAI process or its descendants triggers CRITICAL alert.
var CredentialFiles = []string{
	"credentials.db",
	"Cookies",
	"Login Data",
	"logins.json",
	"key3.db",
	"key4.db",
	"cert9.db",
	".ssh/id_rsa",
	".ssh/id_ed25519",
	".aws/credentials",
	".env",
	".netrc",
}

// LLMDNSEndpoints is the list of known LLM API endpoints for DNS monitoring.
// Shield DNS monitor emits events when these domains are resolved.
var LLMDNSEndpoints = []string{
	"api.anthropic.com",
	"api.openai.com",
	"chatgpt.com",
	"claude.ai",
	"generativelanguage.googleapis.com",
	"gemini.googleapis.com",
	"api.deepseek.com",
	"api.together.xyz",
	"api.groq.com",
	"api.mistral.ai",
	"api.cohere.com",
}

// GenAI event categories for the SOC event bus.
const (
	CategoryGenAIChildProcess      = "genai_child_process"
	CategoryGenAISensitiveFile     = "genai_sensitive_file_access"
	CategoryGenAIUnusualDomain     = "genai_unusual_domain"
	CategoryGenAICredentialAccess  = "genai_credential_access"
	CategoryGenAIPersistence       = "genai_persistence"
	CategoryGenAIConfigModification = "genai_config_modification"
)

// AutoAction defines an automated response for GenAI EDR rules.
type AutoAction struct {
	Type   string `json:"type"`   // "kill_process", "notify", "quarantine"
	Target string `json:"target"` // Process ID, file path, etc.
	Reason string `json:"reason"` // Human-readable justification
}

// IsGenAIProcess returns true if the process name matches a known GenAI agent.
func IsGenAIProcess(processName string) bool {
	for _, name := range GenAIProcessNames {
		if processName == name {
			return true
		}
	}
	return false
}

// IsCredentialFile returns true if the file path matches a known credential file.
func IsCredentialFile(filePath string) bool {
	for _, cred := range CredentialFiles {
		// Check if the file path ends with the credential file name
		if len(filePath) >= len(cred) && filePath[len(filePath)-len(cred):] == cred {
			return true
		}
	}
	return false
}

// IsLLMEndpoint returns true if the domain matches a known LLM API endpoint.
func IsLLMEndpoint(domain string) bool {
	for _, endpoint := range LLMDNSEndpoints {
		if domain == endpoint {
			return true
		}
	}
	return false
}

// ProcessAncestry represents the process tree for Entity ID Intersection.
type ProcessAncestry struct {
	PID        int      `json:"pid"`
	Name       string   `json:"name"`
	Executable string   `json:"executable"`
	Args       []string `json:"args,omitempty"`
	ParentPID  int      `json:"parent_pid"`
	ParentName string   `json:"parent_name"`
	Ancestry   []string `json:"ancestry"` // Full ancestry chain (oldest first)
	EntityID   string   `json:"entity_id"`
}

// HasGenAIAncestor returns true if any process in the ancestry chain is a GenAI agent.
func (p *ProcessAncestry) HasGenAIAncestor() bool {
	for _, ancestor := range p.Ancestry {
		if IsGenAIProcess(ancestor) {
			return true
		}
	}
	return IsGenAIProcess(p.ParentName)
}

// GenAIAncestorName returns the name of the GenAI ancestor, or empty string if none.
func (p *ProcessAncestry) GenAIAncestorName() string {
	if IsGenAIProcess(p.ParentName) {
		return p.ParentName
	}
	for _, ancestor := range p.Ancestry {
		if IsGenAIProcess(ancestor) {
			return ancestor
		}
	}
	return ""
}
