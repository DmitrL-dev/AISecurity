// Package memory defines domain entities for hierarchical memory (H-MEM).
package memory

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"time"
)

// HierLevel represents a hierarchical memory level (L0-L3).
type HierLevel int

const (
	LevelProject HierLevel = 0 // L0: architecture, Iron Laws, project-wide
	LevelDomain  HierLevel = 1 // L1: feature areas, component boundaries
	LevelModule  HierLevel = 2 // L2: function interfaces, dependencies
	LevelSnippet HierLevel = 3 // L3: raw messages, code diffs, episodes
)

// String returns human-readable level name.
func (l HierLevel) String() string {
	switch l {
	case LevelProject:
		return "project"
	case LevelDomain:
		return "domain"
	case LevelModule:
		return "module"
	case LevelSnippet:
		return "snippet"
	default:
		return "unknown"
	}
}

// IsValid checks if the level is within valid range.
func (l HierLevel) IsValid() bool {
	return l >= LevelProject && l <= LevelSnippet
}

// HierLevelFromInt converts an integer to HierLevel with validation.
func HierLevelFromInt(i int) (HierLevel, bool) {
	l := HierLevel(i)
	if !l.IsValid() {
		return 0, false
	}
	return l, true
}

// TTL expiry policies.
const (
	OnExpireMarkStale = "mark_stale"
	OnExpireArchive   = "archive"
	OnExpireDelete    = "delete"
)

// TTLConfig defines time-to-live configuration for a fact.
type TTLConfig struct {
	TTLSeconds     int    `json:"ttl_seconds"`
	RefreshTrigger string `json:"refresh_trigger,omitempty"` // file path that refreshes TTL
	OnExpire       string `json:"on_expire"`                 // mark_stale | archive | delete
}

// IsExpired checks if the TTL has expired relative to createdAt.
func (t *TTLConfig) IsExpired(createdAt time.Time) bool {
	if t.TTLSeconds <= 0 {
		return false // zero or negative TTL = never expires
	}
	return time.Since(createdAt) > time.Duration(t.TTLSeconds)*time.Second
}

// Validate checks TTLConfig fields.
func (t *TTLConfig) Validate() error {
	if t.TTLSeconds < 0 {
		return errors.New("ttl_seconds must be non-negative")
	}
	switch t.OnExpire {
	case OnExpireMarkStale, OnExpireArchive, OnExpireDelete:
		return nil
	default:
		return errors.New("on_expire must be mark_stale, archive, or delete")
	}
}

// Fact represents a hierarchical memory fact.
// Compatible with memory_bridge_v2.db hierarchical_facts table.
type Fact struct {
	ID         string     `json:"id"`
	Content    string     `json:"content"`
	Level      HierLevel  `json:"level"`
	Domain     string     `json:"domain,omitempty"`
	Module     string     `json:"module,omitempty"`
	CodeRef    string     `json:"code_ref,omitempty"` // file:line
	ParentID   string     `json:"parent_id,omitempty"`
	IsStale    bool       `json:"is_stale"`
	IsArchived bool       `json:"is_archived"`
	Confidence float64    `json:"confidence"`
	Source     string     `json:"source"` // "manual" | "consolidation" | etc.
	SessionID  string     `json:"session_id,omitempty"`
	TTL        *TTLConfig `json:"ttl,omitempty"`
	Embedding  []float64  `json:"embedding,omitempty"` // JSON-encoded in DB
	CreatedAt  time.Time  `json:"created_at"`
	ValidFrom  time.Time  `json:"valid_from"`
	ValidUntil *time.Time `json:"valid_until,omitempty"`
	UpdatedAt  time.Time  `json:"updated_at"`
}

// NewFact creates a new Fact with a generated ID and timestamps.
func NewFact(content string, level HierLevel, domain, module string) *Fact {
	now := time.Now()
	return &Fact{
		ID:         generateID(),
		Content:    content,
		Level:      level,
		Domain:     domain,
		Module:     module,
		IsStale:    false,
		IsArchived: false,
		Confidence: 1.0,
		Source:     "manual",
		CreatedAt:  now,
		ValidFrom:  now,
		UpdatedAt:  now,
	}
}

// Validate checks required fields and constraints.
func (f *Fact) Validate() error {
	if f.ID == "" {
		return errors.New("fact ID is required")
	}
	if f.Content == "" {
		return errors.New("fact content is required")
	}
	if !f.Level.IsValid() {
		return errors.New("invalid hierarchy level")
	}
	if f.TTL != nil {
		if err := f.TTL.Validate(); err != nil {
			return err
		}
	}
	return nil
}

// HasEmbedding returns true if the fact has a vector embedding.
func (f *Fact) HasEmbedding() bool {
	return len(f.Embedding) > 0
}

// MarkStale marks the fact as stale.
func (f *Fact) MarkStale() {
	f.IsStale = true
	f.UpdatedAt = time.Now()
}

// Archive marks the fact as archived.
func (f *Fact) Archive() {
	f.IsArchived = true
	f.UpdatedAt = time.Now()
}

// SetValidUntil sets the valid_until timestamp.
func (f *Fact) SetValidUntil(t time.Time) {
	f.ValidUntil = &t
	f.UpdatedAt = time.Now()
}

// FactStoreStats holds aggregate statistics about the fact store.
type FactStoreStats struct {
	TotalFacts     int               `json:"total_facts"`
	ByLevel        map[HierLevel]int `json:"by_level"`
	ByDomain       map[string]int    `json:"by_domain"`
	StaleCount     int               `json:"stale_count"`
	WithEmbeddings int               `json:"with_embeddings"`
}

// generateID creates a random 16-byte hex ID.
func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
