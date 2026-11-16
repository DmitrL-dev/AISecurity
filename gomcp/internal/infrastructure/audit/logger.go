// Package audit provides an append-only audit trail for Zero-G operations.
// The audit logger writes to .rlm/zero_g.audit with O_APPEND semantics,
// making programmatic deletion of records impossible.
package audit

import (
	"crypto/sha256"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

const auditFileName = "zero_g.audit"

// Record represents a single audit log entry.
type Record struct {
	Timestamp      time.Time
	IntentHash     string // SHA-256 of raw data
	DataSnippet    string // First 200 chars of raw data
	SystemReaction string // What the system did
}

// String formats the record for file output.
//
// Security: this is an append-only audit trail where one record must be one
// physical line. DataSnippet holds up to 200 chars of raw (attacker-influenced)
// data and SystemReaction is free-form; an embedded newline would let a caller
// splice forged lines into the trail. sanitizeLogField neutralizes CR/LF so the
// one-record-per-line invariant holds. (Helper defined in decisions.go.)
func (r Record) String() string {
	// IntentHash is normally a 64-char SHA-256 hex, but String() is exported on
	// an exported struct: a Record built with a short/empty hash would make a
	// bare r.IntentHash[:16] panic with slice-out-of-bounds. Truncate safely.
	intent := r.IntentHash
	if len(intent) > 16 {
		intent = intent[:16]
	}
	return fmt.Sprintf("[%s] | %s | %s | %s",
		r.Timestamp.Format("2006-01-02T15:04:05.000Z07:00"),
		intent,
		sanitizeLogField(r.DataSnippet),
		sanitizeLogField(r.SystemReaction))
}

// Logger is the append-only Zero-G audit trail.
type Logger struct {
	mu       sync.Mutex
	file     *os.File
	filePath string
	count    int
}

// NewLogger creates a new audit logger. Opens the file with O_APPEND.
func NewLogger(rlmDir string) (*Logger, error) {
	path := filepath.Join(rlmDir, auditFileName)
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return nil, fmt.Errorf("audit: cannot open %s: %w", path, err)
	}
	return &Logger{file: f, filePath: path}, nil
}

// Log writes an audit record. Thread-safe, append-only.
func (l *Logger) Log(rawData, reaction string) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	hash := sha256.Sum256([]byte(rawData))
	snippet := rawData
	if len(snippet) > 200 {
		snippet = snippet[:200] + "..."
	}

	record := Record{
		Timestamp:      time.Now(),
		IntentHash:     fmt.Sprintf("%x", hash),
		DataSnippet:    snippet,
		SystemReaction: reaction,
	}

	_, err := fmt.Fprintln(l.file, record.String())
	if err != nil {
		return fmt.Errorf("audit: write failed: %w", err)
	}

	l.count++
	return nil
}

// Count returns the number of records written in this session.
func (l *Logger) Count() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.count
}

// Path returns the audit file path.
func (l *Logger) Path() string {
	return l.filePath
}

// Close closes the audit file.
func (l *Logger) Close() error {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.file != nil {
		return l.file.Close()
	}
	return nil
}
