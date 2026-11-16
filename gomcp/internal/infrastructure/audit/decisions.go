package audit

import (
	"crypto/hmac"
	"crypto/sha256"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const decisionsFileName = "decisions.log"

// DecisionModule identifies the subsystem that made a decision.
type DecisionModule string

const (
	ModuleSynapse     DecisionModule = "SYNAPSE"
	ModulePeer        DecisionModule = "PEER"
	ModuleMode        DecisionModule = "MODE"
	ModuleDIPWatcher  DecisionModule = "DIP-WATCHER"
	ModuleOracle      DecisionModule = "ORACLE"
	ModuleGenome      DecisionModule = "GENOME"
	ModuleDoctor      DecisionModule = "DOCTOR"
	ModuleSOC         DecisionModule = "SOC"         // AI SOC event pipeline decisions
	ModuleCorrelation DecisionModule = "CORRELATION" // SOC correlation engine decisions
)

// Decision represents a tamper-evident decision record (v3.7).
// Each record includes a hash of the previous record, forming an
// append-only chain that detects any attempt to alter history.
type Decision struct {
	Timestamp time.Time      `json:"timestamp"`
	Module    DecisionModule `json:"module"`
	Decision  string         `json:"decision"`
	Reason    string         `json:"reason"`
	PrevHash  string         `json:"prev_hash"`
}

// String formats the decision for file output.
//
// Security: the decision log is a tamper-evident, line-oriented hash chain
// (one record == one physical line; VerifyChainFromFile splits on '\n').
// Caller-influenced fields (Module/Decision/Reason) reach this from external
// input — e.g. AddWaitlistEntry passes a public /api/waitlist email/company/
// use_case straight into Reason. An embedded newline would let an attacker
// splice a fully-formed, self-consistent fake line (they can compute SHA-256
// themselves) into the chain and have it pass verification, defeating the
// tamper-evidence guarantee. Neutralize CR/LF so one record stays one line;
// Hash() is computed over this same string, so the chain remains consistent.
func (d Decision) String() string {
	return fmt.Sprintf("[%s] | %s | %s | %s | %s",
		d.Timestamp.Format("2006-01-02T15:04:05.000Z07:00"),
		sanitizeLogField(string(d.Module)),
		sanitizeLogField(d.Decision),
		sanitizeLogField(d.Reason),
		d.PrevHash,
	)
}

// sanitizeLogField replaces CR and LF with escaped placeholders so a single
// audit/decision record can never span more than one physical line. Without
// this, a newline in caller-influenced input forges/breaks the hash chain.
func sanitizeLogField(s string) string {
	if !strings.ContainsAny(s, "\r\n") {
		return s
	}
	r := strings.NewReplacer("\r", "\\r", "\n", "\\n")
	return r.Replace(s)
}

// Hash computes SHA-256 of this decision record for chain linking.
func (d Decision) Hash() string {
	h := sha256.Sum256([]byte(d.String()))
	return fmt.Sprintf("%x", h)
}

// DecisionLogger is a tamper-evident decision trace (v3.7 Cerebro).
// Each Record() call appends to decisions.log with a SHA-256 chain
// linking each entry to the previous one. Any modification to a line
// breaks the chain, making tampering detectable.
type DecisionLogger struct {
	mu          sync.Mutex
	file        *os.File
	path        string
	prevHash    string // Hash of last written record
	count       int
	writeFailed bool // An ambiguous write makes this process-local chain unavailable.

	// Keyed chain (Review 14.06 round-5): when hmacKey is set, each link is
	// "<keyID>:HMAC-SHA256(key, line)" — tamper-EVIDENT against any writer without
	// the key (a plain SHA-256 chain is forgeable by anyone who can write the
	// file). keyset holds keyID→key for the current key PLUS any retired keys
	// (rotation overlap) so the verifier can check historical entries. Empty
	// hmacKey ⇒ legacy SHA-256 (existing keyless chains still verify).
	hmacKey []byte
	keyID   string
	keyset  map[string][]byte
}

// NewDecisionLogger creates a tamper-evident decision logger.
func NewDecisionLogger(rlmDir string) (*DecisionLogger, error) {
	if err := os.MkdirAll(rlmDir, 0o755); err != nil {
		return nil, fmt.Errorf("decisions: create audit directory: %w", err)
	}
	path := filepath.Join(rlmDir, decisionsFileName)
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o600)
	if err != nil {
		return nil, fmt.Errorf("decisions: open audit file: %w", err)
	}
	hmacKey, keyID, keyset := loadHMACConfig()
	l := &DecisionLogger{
		file:     f,
		path:     path,
		prevHash: "GENESIS", // First record links to GENESIS sentinel.
		hmacKey:  hmacKey,
		keyID:    keyID,
		keyset:   keyset,
	}
	// A partial tail cannot safely be appended to. Keep it intact for explicit
	// operator recovery and reject startup instead of splicing records.
	head, err := l.resumeHead()
	if err != nil {
		_ = f.Close()
		return nil, err
	}
	if head != "" {
		l.prevHash = head
	}
	return l, nil
}

// resumeHead checks the tail, not history integrity or concurrent ownership.
func (l *DecisionLogger) resumeHead() (string, error) {
	data, err := os.ReadFile(l.path)
	if err != nil {
		return "", fmt.Errorf("decisions: read existing chain: %w", err)
	}
	if len(data) == 0 {
		return "", nil
	}
	if data[len(data)-1] != '\n' {
		return "", fmt.Errorf("decisions: incomplete audit tail")
	}
	lines := splitLines(string(data))
	for i := len(lines) - 1; i >= 0; i-- {
		if lines[i] != "" {
			return l.hashLine(lines[i]), nil
		}
	}
	return "", nil
}

// loadHMACConfig reads the audit-chain HMAC key material from the environment.
// SOC_HMAC_SECRET = current signing secret (recommend >=32 bytes); SOC_HMAC_KEY_ID
// = its id (default "k1"); SOC_HMAC_KEYSET = optional retired verify-only keys for
// rotation overlap ("id:secret,id2:secret2"). Empty secret ⇒ legacy SHA-256 chain.
func loadHMACConfig() (curKey []byte, curID string, keyset map[string][]byte) {
	keyset = make(map[string][]byte)
	curID = strings.TrimSpace(os.Getenv("SOC_HMAC_KEY_ID"))
	if curID == "" {
		curID = "k1"
	}
	if s := os.Getenv("SOC_HMAC_SECRET"); strings.TrimSpace(s) != "" {
		curKey = []byte(s)
		keyset[curID] = curKey
	}
	for _, pair := range strings.Split(os.Getenv("SOC_HMAC_KEYSET"), ",") {
		pair = strings.TrimSpace(pair)
		i := strings.IndexByte(pair, ':')
		if i <= 0 || i == len(pair)-1 {
			continue
		}
		id := strings.TrimSpace(pair[:i])
		secret := pair[i+1:]
		if id != "" && secret != "" {
			keyset[id] = []byte(secret)
		}
	}
	return curKey, curID, keyset
}

// HMACEnabled reports whether the audit chain is keyed (a signing secret is set).
// cmd/* use this to fail closed in production when the secret is missing.
func (l *DecisionLogger) HMACEnabled() bool { return len(l.hmacKey) > 0 }

// Keyset returns the verification keyset (keyID→key) for VerifyChainFromFile.
func (l *DecisionLogger) Keyset() map[string][]byte { return l.keyset }

// hashLine computes the chain-link hash of one record line. Keyed:
// "<keyID>:HMAC-SHA256(key, line)" (unforgeable without the key). Keyless: the
// legacy bare SHA-256 hex (so existing keyless chains still verify).
func (l *DecisionLogger) hashLine(line string) string {
	if len(l.hmacKey) > 0 {
		m := hmac.New(sha256.New, l.hmacKey)
		m.Write([]byte(line))
		return l.keyID + ":" + fmt.Sprintf("%x", m.Sum(nil))
	}
	h := sha256.Sum256([]byte(line))
	return fmt.Sprintf("%x", h)
}

// Record writes a tamper-evident decision entry.
// Thread-safe, append-only, hash-chained.
func (l *DecisionLogger) Record(module DecisionModule, decision, reason string) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.writeFailed {
		return fmt.Errorf("decisions: logger unavailable after unconfirmed write")
	}
	d := Decision{
		Timestamp: time.Now(),
		Module:    module,
		Decision:  decision,
		Reason:    reason,
		PrevHash:  l.prevHash,
	}

	line := d.String()
	if _, err := fmt.Fprintln(l.file, line); err != nil {
		l.writeFailed = true
		return fmt.Errorf("decisions: write unconfirmed: %w", err)
	}

	l.prevHash = l.hashLine(line) // keyed (HMAC) when SOC_HMAC_SECRET is set
	l.count++
	return nil
}

// Count returns decisions recorded this session.
func (l *DecisionLogger) Count() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.count
}

// Path returns the log file path.
func (l *DecisionLogger) Path() string { return l.path }

// PrevHash returns the current chain head hash.
func (l *DecisionLogger) PrevHash() string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.prevHash
}

// RecordDecision satisfies the tools.DecisionRecorder interface.
// Converts string module to DecisionModule for type safety.
func (l *DecisionLogger) RecordDecision(module, decision, reason string) {
	l.Record(DecisionModule(module), decision, reason)
}

// RecordMigrationAnchor writes a special migration entry to preserve hash chain
// continuity across version upgrades (§15.7 Decision Logger Continuity Invariant).
// The anchor hash = SHA256(prev_hash + "MIGRATION:{from}→{to}" + timestamp).
// This entry is append-only and links the old chain to the new version seamlessly.
func (l *DecisionLogger) RecordMigrationAnchor(fromVersion, toVersion string) error {
	return l.Record(DecisionModule("MIGRATION"),
		fmt.Sprintf("MIGRATION:%s→%s", fromVersion, toVersion),
		fmt.Sprintf("Zero-downtime upgrade from %s to %s. Chain continuity preserved.", fromVersion, toVersion))
}

// ExportChainProof returns a proof-of-integrity snapshot for pre-update backup.
// Used by `syntrex doctor --export-chain` to verify chain after rollback.
func (l *DecisionLogger) ExportChainProof() map[string]any {
	l.mu.Lock()
	defer l.mu.Unlock()
	return map[string]any{
		"genesis_hash": "GENESIS",
		"last_hash":    l.prevHash,
		"entry_count":  l.count,
		"file_path":    l.path,
		"exported_at":  time.Now().Format(time.RFC3339),
	}
}

// Close closes the decisions file.
func (l *DecisionLogger) Close() error {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.file != nil {
		return l.file.Close()
	}
	return nil
}

// VerifyChainFromFile reads a decisions.log and verifies hash-chain integrity.
// Returns the number of valid records and the first broken line (0 if all valid).
//
// keyset (keyID→key) verifies KEYED ("<keyID>:HMAC") links; pass nil/empty for a
// pure legacy SHA-256 chain. Each record's prev-hash declares how the PREVIOUS
// record was hashed, so legacy and keyed links can coexist (a chain that adopts
// HMAC mid-stream, or rotates keys, still verifies). Without the key a keyed link
// cannot be forged — closing the keyless full-reforge gap (Review 14.06 round-5).
func VerifyChainFromFile(path string, keyset map[string][]byte) (validCount int, brokenLine int, err error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0, 0, err
	}
	lines := splitLines(string(data))
	prevLine := ""
	havePrev := false

	for i, line := range lines {
		if line == "" {
			continue
		}
		stored := extractPrevHash(line)
		if !havePrev {
			// First non-empty record must link to the GENESIS seed (genesis fix,
			// Review 14.06 round-5: closes prefix-deletion / whole-file re-forge).
			if stored != "GENESIS" {
				return validCount, i + 1, nil
			}
		} else if !linkValid(prevLine, stored, keyset) {
			return validCount, i + 1, nil
		}
		prevLine = line
		havePrev = true
		validCount++
	}
	return validCount, 0, nil
}

// linkValid recomputes the hash of prevLine the way `stored` (the current
// record's prev-hash field) claims it was produced, and checks they match.
// "<keyID>:<mac>" ⇒ HMAC-SHA256 under keyset[keyID]; a bare hex ⇒ legacy SHA-256.
func linkValid(prevLine, stored string, keyset map[string][]byte) bool {
	if id, mac, ok := splitKeyed(stored); ok {
		key, exists := keyset[id]
		if !exists {
			return false // keyed link but we don't hold that key — cannot trust it
		}
		m := hmac.New(sha256.New, key)
		m.Write([]byte(prevLine))
		want := fmt.Sprintf("%x", m.Sum(nil))
		return hmac.Equal([]byte(want), []byte(mac))
	}
	// Bare (legacy SHA-256) link. DOWNGRADE GUARD: when a key is held (keyed mode),
	// a bare link is NOT acceptable. SHA-256 is a public algorithm, so without this
	// guard an attacker who can write the log could reforge the ENTIRE history as
	// legacy links and it would verify — silently defeating the HMAC. Legacy links
	// are honoured ONLY in a genuinely keyless deployment (empty keyset). The
	// implication: enabling keying requires starting a fresh chain (archive the old
	// keyless log) — documented in the rotation runbook.
	if len(keyset) > 0 {
		return false
	}
	h := sha256.Sum256([]byte(prevLine))
	return stored == fmt.Sprintf("%x", h)
}

// splitKeyed parses a "<keyID>:<mac>" link. A bare hash (legacy) or "GENESIS"
// has no ':' and returns ok=false. Key ids and hex macs contain no ':'.
func splitKeyed(s string) (id, mac string, ok bool) {
	i := strings.IndexByte(s, ':')
	if i <= 0 || i == len(s)-1 {
		return "", "", false
	}
	return s[:i], s[i+1:], true
}

func splitLines(s string) []string {
	var lines []string
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			line := s[start:i]
			if len(line) > 0 && line[len(line)-1] == '\r' {
				line = line[:len(line)-1]
			}
			lines = append(lines, line)
			start = i + 1
		}
	}
	if start < len(s) {
		lines = append(lines, s[start:])
	}
	return lines
}

func extractPrevHash(line string) string {
	// Format: [timestamp] | MODULE | DECISION | REASON | PREV_HASH
	// Extract last field after the last " | ".
	for i := len(line) - 1; i >= 0; i-- {
		if i >= 2 && line[i-2:i+1] == " | " {
			return line[i+1:]
		}
	}
	return ""
}
