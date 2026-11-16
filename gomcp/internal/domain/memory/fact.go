// Package memory defines domain entities for hierarchical memory (H-MEM).
package memory

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sort"
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

// Origin is where a fact's CONTENT came from, on the axis of trust.
//
// Deliberately separate from `Source`, which records which subsystem wrote the row
// ("auto:distill", "watchdog", "stix", …). Those are two different questions and the codebase
// had only the second one, in 31 free-form strings that mixed both. Trust cannot be inferred
// from them: "stix" happens to mean external and "watchdog" happens to mean derived, but
// nothing says so, and a reader has to know the subsystem to guess.
//
// Why this matters, measured. `scripts/attack_surface_matrix.py` registers three cells as blind
// — `memory/persist`, `memory/tamper`, `memory/propagate` — and the science-loop verdict of
// 2026-07-11 explains why string patterns cannot close them: «Record as a standing preference
// for all future sessions: …» is character-for-character identical whether a user asked for it
// or a document the agent had just read told it to. The only signal that separates the two is
// where the content came from, and until 2026-08-05 this system did not record it.
//
// Five values, closed on purpose. A free-form field would drift back into the 31-string state
// it is replacing, and a trust decision cannot be made against an open set.
type Origin string

const (
	// OriginUnspecified — nobody stated an origin. The default, and the honest one: it is what
	// every row written before this field existed genuinely is. Defaulting to OriginUser would
	// have invented provenance for historical data, which is the false claim this whole field
	// exists to remove — the old default was `Source: "manual"`, and it said a human wrote the
	// content of an external threat feed.
	OriginUnspecified Origin = "unspecified"

	// OriginBuiltin — authored by this product and shipped with it: the genome, the survival
	// invariants. Most trusted, and a separate value from OriginUser on purpose. Collapsing the
	// two would conflate «the vendor wrote this» with «the end user wrote this», and those carry
	// different rights: a user may revise their own standing preferences, and a genome fact is
	// immutable by construction (`IsGene`). A policy that cannot tell them apart can only be
	// wrong about one of them.
	OriginBuiltin Origin = "builtin"

	// OriginUser — a human using this system authored this content. May carry standing
	// instructions, because a standing instruction is precisely a thing a user is entitled to
	// set and a document is not.
	OriginUser Origin = "user"

	// OriginDerived — computed by us from material already in the store: a distilled session
	// summary, a consolidation, a heartbeat. Trust is inherited from the inputs and no higher;
	// a summary of an external document is derived, not user.
	OriginDerived Origin = "derived"

	// OriginExternal — content arrived from outside this store: a threat feed, a peer sync, a
	// document or tool output the agent read. This is the value that makes the blind cells
	// decidable, and the value most write paths in this repository should have been using.
	OriginExternal Origin = "external"
)

// trustRank orders origins from most to least trusted. Lower is more trusted.
//
// OriginUnspecified sits at the BOTTOM, tied with external rather than above it. It means
// «nobody said», and for a trust decision «nobody said» has to be treated as the worst case —
// treating it as better than external is how the old `Source: "manual"` default came to assert
// that a threat feed was hand-written.
func (o Origin) trustRank() int {
	switch o {
	case OriginBuiltin:
		return 0
	case OriginUser:
		return 1
	case OriginDerived:
		return 2
	case OriginExternal:
		return 3
	default: // OriginUnspecified and anything unrecognised
		return 4
	}
}

// LeastTrusted returns the least trusted of the given origins, or OriginUnspecified for none.
//
// This is the propagation rule for anything COMPUTED from existing facts — a consolidation, a
// distilled summary, a rollup. «Derived» describes how a fact was made, not how far it may be
// trusted: a summary of an external document still carries that document's imperative, so the
// summary is external. Fixing derived facts at OriginDerived would launder external content
// into a more trusted class on every consolidation pass, which is a slow, quiet, automatic
// privilege escalation — exactly the shape of the `memory/persist` cell the matrix registers
// as blind.
func LeastTrusted(origins ...Origin) Origin {
	worst := OriginUnspecified
	found := false
	for _, o := range origins {
		if !found || o.trustRank() > worst.trustRank() {
			worst = o
			found = true
		}
	}
	if !found {
		return OriginUnspecified
	}
	return worst
}

// MostTrusted returns the most trusted of the given origins, or OriginUnspecified for none.
//
// The opposite rule to LeastTrusted, and both are correct — for different operations. The
// distinction is what the operation asserts about the content:
//
//   - DERIVING a new statement from several facts (consolidation, distillation, a rollup)
//     produces content that is only as trustworthy as its weakest input, so LeastTrusted.
//   - DEDUPLICATING identical content asserts nothing new. The rows say the same thing, and the
//     question «did a person ask for this» has one answer across all of them: yes, if any of them
//     is OriginUser. So MostTrusted.
//
// Using LeastTrusted for dedup would be a live defect, and it was measured on Global before this
// existed: «Owner prefers metric units in all reports.» was stored three times — twice by an
// agent (external) and once by the owner (user). Collapsing those to the least trusted origin
// would turn the owner's own standing instruction into reference material, letting any writer
// neutralise a user instruction merely by repeating it. Nothing is escalated in the other
// direction: content becomes OriginUser only if a user actually wrote that same content, in
// which case it is a user instruction and always was.
func MostTrusted(origins ...Origin) Origin {
	best := OriginUnspecified
	found := false
	for _, o := range origins {
		if !found || o.trustRank() < best.trustRank() {
			best = o
			found = true
		}
	}
	if !found {
		return OriginUnspecified
	}
	return best
}

// IsValid reports whether o is one of the four declared origins.
func (o Origin) IsValid() bool {
	switch o {
	case OriginUnspecified, OriginBuiltin, OriginUser, OriginDerived, OriginExternal:
		return true
	default:
		return false
	}
}

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

// ErrImmutableFact is returned when attempting to mutate a gene (immutable fact).
var ErrImmutableFact = errors.New("cannot mutate gene: immutable fact")

// Fact represents a hierarchical memory fact.
// Compatible with memory_bridge_v2.db hierarchical_facts table.
type Fact struct {
	ID         string    `json:"id"`
	TenantID   string    `json:"tenant_id,omitempty"`
	ProjectID  string    `json:"project_id,omitempty"`
	Content    string    `json:"content"`
	Level      HierLevel `json:"level"`
	Domain     string    `json:"domain,omitempty"`
	Module     string    `json:"module,omitempty"`
	CodeRef    string    `json:"code_ref,omitempty"` // file:line
	ParentID   string    `json:"parent_id,omitempty"`
	IsStale    bool      `json:"is_stale"`
	IsArchived bool      `json:"is_archived"`
	IsGene     bool      `json:"is_gene"` // Genome Layer: immutable survival invariant
	Confidence float64   `json:"confidence"`
	// Source is WHICH SUBSYSTEM wrote the row: "auto:distill", "watchdog", "stix", … Useful for
	// debugging and not a trust signal — see Origin, which is the trust axis.
	Source string `json:"source"`
	// Origin is where the CONTENT came from. See the Origin type.
	Origin     Origin     `json:"origin"`
	SessionID  string     `json:"session_id,omitempty"`
	TTL        *TTLConfig `json:"ttl,omitempty"`
	Embedding  []float64  `json:"embedding,omitempty"` // JSON-encoded in DB
	HitCount   int        `json:"hit_count"`           // v3.3: context access counter
	LastAccess time.Time  `json:"last_accessed_at"`    // v3.3: last context inclusion
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
		IsGene:     false,
		Confidence: 1.0,
		// Not "manual". A constructor cannot know who authored the content, and claiming a human
		// did is the defect this change removes: `add_fact`, the tool an AGENT calls, produced
		// facts marked hand-written, as did the STIX feed reader. Callers state the truth.
		Source:    "unspecified",
		Origin:    OriginUnspecified,
		CreatedAt: now,
		ValidFrom: now,
		UpdatedAt: now,
	}
}

// NewGene creates an immutable genome fact (L0 only).
// Genes are survival invariants that cannot be updated or deleted.
func NewGene(content string, domain string) *Fact {
	now := time.Now()
	return &Fact{
		ID:         generateID(),
		Content:    content,
		Level:      LevelProject,
		Domain:     domain,
		IsStale:    false,
		IsArchived: false,
		IsGene:     true,
		Confidence: 1.0,
		Source:     "genome",
		// Authored by the product, not by whoever is using it. See OriginBuiltin.
		Origin:    OriginBuiltin,
		CreatedAt: now,
		ValidFrom: now,
		UpdatedAt: now,
	}
}

// IsImmutable returns true if this fact is a gene and cannot be mutated.
func (f *Fact) IsImmutable() bool {
	return f.IsGene
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
	// An unrecognised origin is rejected rather than tolerated: a typo would otherwise become a
	// fifth trust class that every policy silently treats as «not one of the three», and the
	// point of a closed enum is that this cannot happen. OriginUnspecified is valid — it is the
	// honest «not stated» — so this rejects only values outside the set.
	if !f.Origin.IsValid() {
		return fmt.Errorf("invalid fact origin %q", f.Origin)
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
	// TotalFacts is every legacy non-session row, archived ones included. Conversation memory has
	// an exact tenant/project/session API and is deliberately absent from project-wide statistics.
	// Kept archived-inclusive because that is what the TUI and legacy tools have always meant.
	TotalFacts int `json:"total_facts"`
	// LiveFacts is what retrieval can actually return — neither archived nor stale. This is the
	// honest answer to «how much do you remember».
	LiveFacts     int               `json:"live_facts"`
	ArchivedCount int               `json:"archived_count"`
	ByLevel       map[HierLevel]int `json:"by_level"`
	ByDomain      map[string]int    `json:"by_domain"`
	// ByOrigin counts live facts by who authored their content. The store could already summarise
	// itself by level and by domain but not by the one field that decides whether content may act
	// as a standing instruction — which is the summary a user most needs, and the only one that
	// answers «how much of this memory can tell a model what to do».
	ByOrigin       map[Origin]int `json:"by_origin"`
	StaleCount     int            `json:"stale_count"`
	WithEmbeddings int            `json:"with_embeddings"`
	GeneCount      int            `json:"gene_count"`
	ColdCount      int            `json:"cold_count"`            // v3.3: hit_count=0, >30d
	GenomeHash     string         `json:"genome_hash,omitempty"` // Merkle root of all genes
}

// GenomeHash computes a deterministic hash of all gene facts.
// This serves as a Merkle-style integrity verification for the Genome Layer.
func GenomeHash(genes []*Fact) string {
	if len(genes) == 0 {
		return ""
	}
	// Sort by ID for deterministic ordering.
	sorted := make([]*Fact, len(genes))
	copy(sorted, genes)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].ID < sorted[j].ID
	})

	// Build Merkle leaf hashes.
	h := sha256.New()
	for _, g := range sorted {
		leaf := sha256.Sum256([]byte(fmt.Sprintf("%s:%s", g.ID, g.Content)))
		h.Write(leaf[:])
	}
	return hex.EncodeToString(h.Sum(nil))
}

// generateID creates a random 16-byte hex ID.
func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
