package shadow_ai

import (
	"log/slog"
	"math"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

// --- AI Signature Database ---

// AISignatureDB contains known AI service signatures for detection.
type AISignatureDB struct {
	mu                sync.RWMutex
	services          []AIServiceInfo
	domainPatterns    []*domainPattern
	apiKeyPatterns    []*APIKeyPattern
	httpSignatures    []string
	injectionPatterns []*regexp.Regexp
}

type domainPattern struct {
	original string
	regex    *regexp.Regexp
	service  string
}

// APIKeyPattern defines a regex pattern for detecting AI API keys.
type APIKeyPattern struct {
	Name    string         `json:"name"`
	Pattern *regexp.Regexp `json:"-"`
	Entropy float64        `json:"min_entropy"`
}

// NewAISignatureDB creates a signature database pre-loaded with known AI services.
func NewAISignatureDB() *AISignatureDB {
	db := &AISignatureDB{}
	db.loadDefaults()
	return db
}

// loadDefaults populates the database with known AI services and patterns.
func (db *AISignatureDB) loadDefaults() {
	db.services = defaultAIServices()

	// Compile domain patterns.
	for _, svc := range db.services {
		for _, d := range svc.Domains {
			pattern := domainToRegex(d)
			db.domainPatterns = append(db.domainPatterns, &domainPattern{
				original: d,
				regex:    pattern,
				service:  svc.Name,
			})
		}
	}

	// API key patterns.
	db.apiKeyPatterns = defaultAPIKeyPatterns()

	// HTTP header signatures.
	db.httpSignatures = []string{
		"authorization: bearer sk-",     // OpenAI
		"authorization: bearer ant-",    // Anthropic
		"x-api-key: sk-ant-",            // Anthropic v2
		"x-goog-api-key:",              // Google AI
		"authorization: bearer gsk_",   // Groq
		"authorization: bearer hf_",    // HuggingFace
		"api-key:",                      // Azure OpenAI (x-ms header)
		"x-api-key: xai-",              // xAI Grok API
	}

	// Prompt injection / jailbreak patterns
	injectionStrs := []string{
		`(?i)ignore (?:all )?(?:previous )?instructions`,
		`(?i)system prompt`,
		`(?i)you are now`,
		`(?i)jailbreak`,
		`(?i)\bdan\b`,
	}
	for _, p := range injectionStrs {
		db.injectionPatterns = append(db.injectionPatterns, regexp.MustCompile(p))
	}
}

// domainToRegex converts a wildcard domain (e.g., "*.openai.com") to a regex.
func domainToRegex(domain string) *regexp.Regexp {
	escaped := regexp.QuoteMeta(domain)
	escaped = strings.ReplaceAll(escaped, `\*`, `[a-zA-Z0-9\-]+`)
	return regexp.MustCompile("(?i)^" + escaped + "$")
}

// MatchDomain checks if a domain matches any known AI service.
// Returns the service name or empty string.
func (db *AISignatureDB) MatchDomain(domain string) string {
	db.mu.RLock()
	defer db.mu.RUnlock()

	domain = strings.ToLower(strings.TrimSpace(domain))
	for _, dp := range db.domainPatterns {
		if dp.regex.MatchString(domain) {
			return dp.service
		}
	}
	return ""
}

// MatchHTTPHeaders checks if HTTP headers contain known AI service signatures.
func (db *AISignatureDB) MatchHTTPHeaders(headers map[string]string) string {
	db.mu.RLock()
	defer db.mu.RUnlock()

	for key, value := range headers {
		headerLine := strings.ToLower(key + ": " + value)
		for _, sig := range db.httpSignatures {
			if strings.Contains(headerLine, sig) {
				return sig
			}
		}
	}
	return ""
}

// ScanForAPIKeys scans content for AI API keys.
// Returns the matched pattern name or empty string.
func (db *AISignatureDB) ScanForAPIKeys(content string) string {
	db.mu.RLock()
	defer db.mu.RUnlock()

	for _, pattern := range db.apiKeyPatterns {
		if pattern.Pattern.MatchString(content) {
			return pattern.Name
		}
	}
	return ""
}

// ServiceCount returns the number of known AI services.
func (db *AISignatureDB) ServiceCount() int {
	db.mu.RLock()
	defer db.mu.RUnlock()
	return len(db.services)
}

// DomainPatternCount returns the number of compiled domain patterns.
func (db *AISignatureDB) DomainPatternCount() int {
	db.mu.RLock()
	defer db.mu.RUnlock()
	return len(db.domainPatterns)
}

// ScanForInjection scans content for prompt injection or jailbreak patterns.
// Returns true if a malicious payload is detected.
func (db *AISignatureDB) ScanForInjection(content string) bool {
	db.mu.RLock()
	defer db.mu.RUnlock()
	
	for _, pattern := range db.injectionPatterns {
		if pattern.MatchString(content) {
			return true
		}
	}
	return false
}

// AddService adds a custom AI service to the database.
func (db *AISignatureDB) AddService(svc AIServiceInfo) {
	db.mu.Lock()
	defer db.mu.Unlock()

	db.services = append(db.services, svc)
	for _, d := range svc.Domains {
		pattern := domainToRegex(d)
		db.domainPatterns = append(db.domainPatterns, &domainPattern{
			original: d,
			regex:    pattern,
			service:  svc.Name,
		})
	}
}

// --- Network Detector ---

// NetworkEvent represents a network connection event for analysis.
type NetworkEvent struct {
	User        string            `json:"user"`
	Hostname    string            `json:"hostname"`
	Destination string            `json:"destination"` // Domain or IP
	Port        int               `json:"port"`
	HTTPHeaders map[string]string `json:"http_headers,omitempty"`
	TLSJA3      string            `json:"tls_ja3,omitempty"`
	DataSize    int64             `json:"data_size"`
	Timestamp   time.Time         `json:"timestamp"`
}

// NetworkDetector analyzes network events for AI service access.
type NetworkDetector struct {
	signatures *AISignatureDB
	logger     *slog.Logger
}

// NewNetworkDetector creates a new network detector with the default signature DB.
func NewNetworkDetector() *NetworkDetector {
	return &NetworkDetector{
		signatures: NewAISignatureDB(),
		logger:     slog.Default().With("component", "shadow-ai-network"),
	}
}

// NewNetworkDetectorWithDB creates a detector with a custom signature database.
func NewNetworkDetectorWithDB(db *AISignatureDB) *NetworkDetector {
	return &NetworkDetector{
		signatures: db,
		logger:     slog.Default().With("component", "shadow-ai-network"),
	}
}

// Analyze checks a network event for AI service access.
// Returns a ShadowAIEvent if detected, nil otherwise.
func (nd *NetworkDetector) Analyze(event NetworkEvent) *ShadowAIEvent {
	// Check domain match.
	if service := nd.signatures.MatchDomain(event.Destination); service != "" {
		nd.logger.Info("AI domain detected",
			"user", event.User,
			"destination", event.Destination,
			"service", service,
		)
		return &ShadowAIEvent{
			UserID:          event.User,
			Hostname:        event.Hostname,
			Destination:     event.Destination,
			AIService:       service,
			DetectionMethod: DetectNetwork,
			Action:          "detected",
			DataSize:        event.DataSize,
			Timestamp:       event.Timestamp,
		}
	}

	// Check HTTP header signatures.
	if sig := nd.signatures.MatchHTTPHeaders(event.HTTPHeaders); sig != "" {
		nd.logger.Info("AI HTTP signature detected",
			"user", event.User,
			"destination", event.Destination,
			"signature", sig,
		)
		return &ShadowAIEvent{
			UserID:          event.User,
			Hostname:        event.Hostname,
			Destination:     event.Destination,
			AIService:       "unknown",
			DetectionMethod: DetectHTTP,
			Action:          "detected",
			DataSize:        event.DataSize,
			Timestamp:       event.Timestamp,
			Metadata:        map[string]string{"http_signature": sig},
		}
	}

	return nil
}

// SignatureDB returns the underlying signature database for extension.
func (nd *NetworkDetector) SignatureDB() *AISignatureDB {
	return nd.signatures
}

// --- Behavioral Detector ---

// UserBehaviorProfile tracks a user's AI access behavior for anomaly detection.
type UserBehaviorProfile struct {
	UserID            string    `json:"user_id"`
	AccessFrequency   float64   `json:"access_frequency"`    // Requests per hour
	DataVolumePerHour float64   `json:"data_volume_per_hour"` // Bytes per hour
	KnownDestinations []string  `json:"known_destinations"`
	UpdatedAt         time.Time `json:"updated_at"`
}

// BehavioralAlert is emitted when anomalous AI access is detected.
type BehavioralAlert struct {
	UserID      string  `json:"user_id"`
	AnomalyType string  `json:"anomaly_type"` // "access_spike", "new_destination", "data_volume_spike"
	Current     float64 `json:"current"`
	Baseline    float64 `json:"baseline"`
	ZScore      float64 `json:"z_score"`
	Destination string  `json:"destination,omitempty"`
	Severity    string  `json:"severity"`
}

// BehavioralDetector detects anomalous AI usage patterns per user.
type BehavioralDetector struct {
	mu        sync.RWMutex
	baselines map[string]*UserBehaviorProfile
	current   map[string]*UserBehaviorProfile
	alertBus  chan BehavioralAlert
	logger    *slog.Logger
}

// NewBehavioralDetector creates a behavioral detector with a buffered alert bus.
func NewBehavioralDetector(alertBufSize int) *BehavioralDetector {
	if alertBufSize <= 0 {
		alertBufSize = 100
	}
	return &BehavioralDetector{
		baselines: make(map[string]*UserBehaviorProfile),
		current:   make(map[string]*UserBehaviorProfile),
		alertBus:  make(chan BehavioralAlert, alertBufSize),
		logger:    slog.Default().With("component", "shadow-ai-behavioral"),
	}
}

// RecordAccess records a single AI access attempt for behavioral tracking.
func (bd *BehavioralDetector) RecordAccess(userID, destination string, dataSize int64) {
	bd.mu.Lock()
	defer bd.mu.Unlock()

	profile, ok := bd.current[userID]
	if !ok {
		profile = &UserBehaviorProfile{
			UserID: userID,
		}
		bd.current[userID] = profile
	}

	profile.AccessFrequency++
	profile.DataVolumePerHour += float64(dataSize)
	profile.UpdatedAt = time.Now()

	// Track destinations.
	found := false
	for _, d := range profile.KnownDestinations {
		if d == destination {
			found = true
			break
		}
	}
	if !found {
		profile.KnownDestinations = append(profile.KnownDestinations, destination)
	}
}

// SetBaseline sets the known baseline behavior for a user.
func (bd *BehavioralDetector) SetBaseline(userID string, profile *UserBehaviorProfile) {
	bd.mu.Lock()
	defer bd.mu.Unlock()
	bd.baselines[userID] = profile
}

// DetectAnomalies compares current behavior to baselines and emits alerts.
func (bd *BehavioralDetector) DetectAnomalies() []BehavioralAlert {
	bd.mu.RLock()
	defer bd.mu.RUnlock()

	var alerts []BehavioralAlert

	for userID, current := range bd.current {
		baseline, ok := bd.baselines[userID]
		if !ok {
			// No baseline — any AI access from this user is suspicious.
			if current.AccessFrequency > 0 {
				alert := BehavioralAlert{
					UserID:      userID,
					AnomalyType: "first_ai_access",
					Current:     current.AccessFrequency,
					Baseline:    0,
					Severity:    "WARNING",
				}
				alerts = append(alerts, alert)
				bd.emitAlert(alert)
			}
			continue
		}

		// Z-score for access frequency.
		if baseline.AccessFrequency > 0 {
			zscore := (current.AccessFrequency - baseline.AccessFrequency) / math.Max(baseline.AccessFrequency*0.3, 1)
			if math.Abs(zscore) > 3.0 {
				alert := BehavioralAlert{
					UserID:      userID,
					AnomalyType: "access_spike",
					Current:     current.AccessFrequency,
					Baseline:    baseline.AccessFrequency,
					ZScore:      zscore,
					Severity:    "WARNING",
				}
				alerts = append(alerts, alert)
				bd.emitAlert(alert)
			}
		}

		// Detect new AI destinations.
		for _, dest := range current.KnownDestinations {
			isNew := true
			for _, known := range baseline.KnownDestinations {
				if dest == known {
					isNew = false
					break
				}
			}
			if isNew {
				alert := BehavioralAlert{
					UserID:      userID,
					AnomalyType: "new_ai_destination",
					Destination: dest,
					Severity:    "HIGH",
				}
				alerts = append(alerts, alert)
				bd.emitAlert(alert)
			}
		}

		// Z-score for data volume.
		if baseline.DataVolumePerHour > 0 {
			zscore := (current.DataVolumePerHour - baseline.DataVolumePerHour) / math.Max(baseline.DataVolumePerHour*0.3, 1)
			if math.Abs(zscore) > 3.0 {
				alert := BehavioralAlert{
					UserID:      userID,
					AnomalyType: "data_volume_spike",
					Current:     current.DataVolumePerHour,
					Baseline:    baseline.DataVolumePerHour,
					ZScore:      zscore,
					Severity:    "CRITICAL",
				}
				alerts = append(alerts, alert)
				bd.emitAlert(alert)
			}
		}
	}

	return alerts
}

// Alerts returns the alert channel for consuming behavioral alerts.
func (bd *BehavioralDetector) Alerts() <-chan BehavioralAlert {
	return bd.alertBus
}

// ResetCurrent clears the current period data (call after each analysis window).
func (bd *BehavioralDetector) ResetCurrent() {
	bd.mu.Lock()
	defer bd.mu.Unlock()
	bd.current = make(map[string]*UserBehaviorProfile)
}

func (bd *BehavioralDetector) emitAlert(alert BehavioralAlert) {
	select {
	case bd.alertBus <- alert:
	default:
		bd.logger.Warn("behavioral alert bus full, dropping alert",
			"user", alert.UserID,
			"type", alert.AnomalyType,
		)
	}
}

// --- Default Data ---

func defaultAIServices() []AIServiceInfo {
	return []AIServiceInfo{
		{Name: "ChatGPT", Vendor: "OpenAI", Domains: []string{"chat.openai.com", "api.openai.com", "*.openai.com"}, Category: "llm"},
		{Name: "Claude", Vendor: "Anthropic", Domains: []string{"claude.ai", "api.anthropic.com", "*.anthropic.com"}, Category: "llm"},
		{Name: "Gemini", Vendor: "Google", Domains: []string{"gemini.google.com", "generativelanguage.googleapis.com", "aistudio.google.com"}, Category: "llm"},
		{Name: "Copilot", Vendor: "Microsoft", Domains: []string{"copilot.microsoft.com", "*.copilot.microsoft.com"}, Category: "code_assist"},
		{Name: "Cohere", Vendor: "Cohere", Domains: []string{"api.cohere.ai", "dashboard.cohere.com", "*.cohere.ai"}, Category: "llm"},
		{Name: "AI21", Vendor: "AI21 Labs", Domains: []string{"api.ai21.com", "studio.ai21.com", "*.ai21.com"}, Category: "llm"},
		{Name: "HuggingFace", Vendor: "Hugging Face", Domains: []string{"api-inference.huggingface.co", "huggingface.co", "*.huggingface.co"}, Category: "llm"},
		{Name: "Replicate", Vendor: "Replicate", Domains: []string{"api.replicate.com", "replicate.com", "*.replicate.com"}, Category: "llm"},
		{Name: "Mistral", Vendor: "Mistral AI", Domains: []string{"api.mistral.ai", "chat.mistral.ai", "*.mistral.ai"}, Category: "llm"},
		{Name: "Perplexity", Vendor: "Perplexity", Domains: []string{"api.perplexity.ai", "perplexity.ai", "*.perplexity.ai"}, Category: "llm"},
		{Name: "Groq", Vendor: "Groq", Domains: []string{"api.groq.com", "groq.com", "*.groq.com"}, Category: "llm"},
		{Name: "Together", Vendor: "Together AI", Domains: []string{"api.together.xyz", "together.ai", "*.together.ai"}, Category: "llm"},
		{Name: "Stability", Vendor: "Stability AI", Domains: []string{"api.stability.ai", "*.stability.ai"}, Category: "image_gen"},
		{Name: "Midjourney", Vendor: "Midjourney", Domains: []string{"midjourney.com", "*.midjourney.com"}, Category: "image_gen"},
		{Name: "DALL-E", Vendor: "OpenAI", Domains: []string{"labs.openai.com"}, Category: "image_gen"},
		{Name: "Cursor", Vendor: "Cursor", Domains: []string{"api2.cursor.sh", "*.cursor.sh"}, Category: "code_assist"},
		{Name: "Replit AI", Vendor: "Replit", Domains: []string{"replit.com", "*.replit.com"}, Category: "code_assist"},
		{Name: "Codeium", Vendor: "Codeium", Domains: []string{"*.codeium.com", "codeium.com"}, Category: "code_assist"},
		{Name: "Tabnine", Vendor: "Tabnine", Domains: []string{"*.tabnine.com", "tabnine.com"}, Category: "code_assist"},
		{Name: "Qwen", Vendor: "Alibaba", Domains: []string{"dashscope.aliyuncs.com", "*.dashscope.aliyuncs.com"}, Category: "llm"},
		{Name: "DeepSeek", Vendor: "DeepSeek", Domains: []string{"api.deepseek.com", "chat.deepseek.com", "*.deepseek.com"}, Category: "llm"},
		{Name: "Kimi", Vendor: "Moonshot AI", Domains: []string{"api.moonshot.cn", "kimi.moonshot.cn", "*.moonshot.cn"}, Category: "llm"},
		{Name: "Baidu ERNIE", Vendor: "Baidu", Domains: []string{"aip.baidubce.com", "erniebot.baidu.com"}, Category: "llm"},
		{Name: "Jasper", Vendor: "Jasper", Domains: []string{"app.jasper.ai", "api.jasper.ai", "*.jasper.ai"}, Category: "llm"},
		{Name: "Writer", Vendor: "Writer", Domains: []string{"writer.com", "api.writer.com", "*.writer.com"}, Category: "llm"},
		{Name: "Notion AI", Vendor: "Notion", Domains: []string{"www.notion.so"}, Category: "productivity"},
		{Name: "Grammarly AI", Vendor: "Grammarly", Domains: []string{"*.grammarly.com"}, Category: "productivity"},
		{Name: "Runway", Vendor: "Runway", Domains: []string{"app.runwayml.com", "api.runwayml.com", "*.runwayml.com"}, Category: "video_gen"},
		{Name: "Pika", Vendor: "Pika", Domains: []string{"pika.art", "*.pika.art"}, Category: "video_gen"},
		{Name: "ElevenLabs", Vendor: "ElevenLabs", Domains: []string{"api.elevenlabs.io", "elevenlabs.io", "*.elevenlabs.io"}, Category: "audio_gen"},
		{Name: "Suno", Vendor: "Suno", Domains: []string{"suno.com", "*.suno.com"}, Category: "audio_gen"},
		{Name: "OpenRouter", Vendor: "OpenRouter", Domains: []string{"openrouter.ai", "*.openrouter.ai"}, Category: "llm"},
		{Name: "Scale AI", Vendor: "Scale", Domains: []string{"scale.com", "api.scale.com", "*.scale.com"}, Category: "llm"},
		{Name: "Inflection Pi", Vendor: "Inflection", Domains: []string{"pi.ai", "api.inflection.ai"}, Category: "llm"},
		{Name: "Grok", Vendor: "xAI", Domains: []string{"grok.x.ai", "api.x.ai", "console.x.ai"}, Category: "llm"},
		{Name: "Character.AI", Vendor: "Character.AI", Domains: []string{"character.ai", "*.character.ai"}, Category: "llm"},
		{Name: "Poe", Vendor: "Quora", Domains: []string{"poe.com", "*.poe.com"}, Category: "llm"},
		{Name: "You.com", Vendor: "You.com", Domains: []string{"you.com", "api.you.com"}, Category: "llm"},
		{Name: "Phind", Vendor: "Phind", Domains: []string{"phind.com", "*.phind.com"}, Category: "llm"},
		// Cloud provider AI services (Feb 2026 gap closure)
		{Name: "Azure OpenAI", Vendor: "Microsoft", Domains: []string{"*.openai.azure.com", "*.cognitiveservices.azure.com"}, Category: "llm"},
		{Name: "Amazon Bedrock", Vendor: "AWS", Domains: []string{"bedrock-runtime.*.amazonaws.com", "bedrock.*.amazonaws.com"}, Category: "llm"},
		{Name: "Meta Llama API", Vendor: "Meta", Domains: []string{"llama-api.meta.com", "api.llama.meta.com", "*.llama.meta.com"}, Category: "llm"},
		{Name: "xAI API v2", Vendor: "xAI", Domains: []string{"api.x.ai", "console.x.ai"}, Category: "llm"},
	}
}

func defaultAPIKeyPatterns() []*APIKeyPattern {
	return []*APIKeyPattern{
		{Name: "OpenAI API Key", Pattern: regexp.MustCompile(`sk-[a-zA-Z0-9]{20,}T3BlbkFJ[a-zA-Z0-9]{20,}`), Entropy: 4.5},
		{Name: "OpenAI Project Key", Pattern: regexp.MustCompile(`sk-proj-[a-zA-Z0-9\-_]{48,}`), Entropy: 4.5},
		{Name: "Anthropic API Key", Pattern: regexp.MustCompile(`sk-ant-[a-zA-Z0-9\-_]{90,}`), Entropy: 4.5},
		{Name: "Google AI API Key", Pattern: regexp.MustCompile(`AIza[0-9A-Za-z\-_]{35}`), Entropy: 4.0},
		{Name: "HuggingFace Token", Pattern: regexp.MustCompile(`hf_[a-zA-Z0-9]{34}`), Entropy: 4.5},
		{Name: "Groq API Key", Pattern: regexp.MustCompile(`gsk_[a-zA-Z0-9]{52}`), Entropy: 4.5},
		{Name: "Cohere API Key", Pattern: regexp.MustCompile(`[a-zA-Z0-9]{10,}-[a-zA-Z0-9]{4,}-[a-zA-Z0-9]{4,}-[a-zA-Z0-9]{4,}-[a-zA-Z0-9]{12,}`), Entropy: 4.5},
		{Name: "Replicate API Token", Pattern: regexp.MustCompile(`r8_[a-zA-Z0-9]{37}`), Entropy: 4.5},
		// Feb 2026 gap closure: Azure OpenAI, Bedrock, xAI
		{Name: "Azure OpenAI API Key", Pattern: regexp.MustCompile(`[a-f0-9]{32}`), Entropy: 3.8},
		{Name: "xAI API Key", Pattern: regexp.MustCompile(`xai-[a-zA-Z0-9]{48,}`), Entropy: 4.5},
	}
}

// ServicesByCategory returns AI services grouped by category.
func ServicesByCategory() map[string][]AIServiceInfo {
	services := defaultAIServices()
	result := make(map[string][]AIServiceInfo)
	for _, svc := range services {
		result[svc.Category] = append(result[svc.Category], svc)
	}
	// Sort each category by name for deterministic output.
	for cat := range result {
		sort.Slice(result[cat], func(i, j int) bool {
			return result[cat][i].Name < result[cat][j].Name
		})
	}
	return result
}
