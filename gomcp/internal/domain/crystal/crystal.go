// Package crystal defines domain entities for code crystal indexing (C³).
package crystal

import "context"

// Primitive represents a code primitive extracted from a source file.
type Primitive struct {
	PType      string  `json:"ptype"` // function, class, method, variable, etc.
	Name       string  `json:"name"`
	Value      string  `json:"value"` // signature or definition
	SourceLine int     `json:"source_line"`
	Confidence float64 `json:"confidence"`
}

// Crystal represents an indexed code file with extracted primitives.
type Crystal struct {
	Path            string      `json:"path"` // file path (primary key)
	Name            string      `json:"name"` // file basename
	TokenCount      int         `json:"token_count"`
	ContentHash     string      `json:"content_hash"`
	Primitives      []Primitive `json:"primitives"`
	PrimitivesCount int         `json:"primitives_count"`
	IndexedAt       float64     `json:"indexed_at"`   // Unix timestamp
	SourceMtime     float64     `json:"source_mtime"` // Unix timestamp
	SourceHash      string      `json:"source_hash"`
	LastValidated   float64     `json:"last_validated"` // Unix timestamp, 0 if never
	HumanConfirmed  bool        `json:"human_confirmed"`
}

// CrystalStats holds aggregate statistics about the crystal store.
type CrystalStats struct {
	TotalCrystals   int            `json:"total_crystals"`
	TotalPrimitives int            `json:"total_primitives"`
	TotalTokens     int            `json:"total_tokens"`
	ByExtension     map[string]int `json:"by_extension"`
}

// CrystalStore defines the interface for crystal persistence.
type CrystalStore interface {
	Upsert(ctx context.Context, crystal *Crystal) error
	Get(ctx context.Context, path string) (*Crystal, error)
	Delete(ctx context.Context, path string) error
	List(ctx context.Context, pattern string, limit int) ([]*Crystal, error)
	Search(ctx context.Context, query string, limit int) ([]*Crystal, error)
	Stats(ctx context.Context) (*CrystalStats, error)
}
