// Package vectorstore implements persistent storage for intent vectors (DIP H2.1).
//
// Intent vectors are the output of the Intent Distiller (H0.2). Storing them
// enables neuroplastic routing — matching new intents against known patterns
// to determine optimal processing paths.
//
// Features:
//   - In-memory store with capacity management (LRU eviction)
//   - Cosine similarity search for nearest-neighbor matching
//   - QJL 1-bit quantized approximate search (TurboQuant §20)
//   - Route labels for categorized intent patterns
//   - Thread-safe for concurrent access
package vectorstore

import (
	"fmt"
	"math"
	"sort"
	"sync"
	"time"
)

// IntentRecord stores a distilled intent with metadata.
type IntentRecord struct {
	ID             string    `json:"id"`
	Text           string    `json:"text"`            // Original text
	CompressedText string    `json:"compressed_text"` // Distilled form
	Vector         []float64 `json:"vector"`          // Intent embedding vector
	Route          string    `json:"route"`           // Assigned route label
	Verdict        string    `json:"verdict"`         // Oracle verdict (ALLOW/DENY/REVIEW)
	SincerityScore float64   `json:"sincerity_score"`
	Entropy        float64   `json:"entropy"`
	CreatedAt      time.Time `json:"created_at"`
}

// SearchResult holds a similarity search result.
type SearchResult struct {
	Record     *IntentRecord `json:"record"`
	Similarity float64       `json:"similarity"` // Cosine similarity [0, 1]
}

// Stats holds store statistics.
type Stats struct {
	TotalRecords      int            `json:"total_records"`
	Capacity          int            `json:"capacity"`
	RouteCount        map[string]int `json:"route_counts"`
	VerdictCount      map[string]int `json:"verdict_counts"`
	AvgEntropy        float64        `json:"avg_entropy"`
	QJLEnabled        bool           `json:"qjl_enabled"`
	QJLProjections    int            `json:"qjl_projections"`
	QJLBitsPerVec     int            `json:"qjl_bits_per_vector"`
	QJLBytesPerVec    int            `json:"qjl_bytes_per_vector"`
	PQEnabled         bool           `json:"pq_enabled"`
	PQBitsPerDim      int            `json:"pq_bits_per_dim"`
	PQBytesPerVec     int            `json:"pq_bytes_per_vector"`
	PQCompressionRate float64        `json:"pq_compression_ratio"`
	PQDropFloat64     bool           `json:"pq_drop_float64"`
}

// Config configures the vector store.
type Config struct {
	Capacity       int   // Max records before LRU eviction. Default: 1000.
	QJLProjections int   // Number of QJL random projections (bits). -1 = disabled. Default: 256.
	QJLSeed        int64 // PRNG seed for reproducible QJL projections. Default: 42.
	QJLVectorDim   int   // Expected vector dimensionality for QJL. Default: 128.
	PQBitsPerDim   int   // PolarQuant bits per dimension (0 = disabled, 4 or 8). Default: 0.
	PQSeed         int64 // PRNG seed for PolarQuant rotation matrix. Default: 7.
	PQDropFloat64  bool  // If true, discard the original float64 vectors to save memory. Default: false.
}

// DefaultConfig returns sensible defaults.
func DefaultConfig() Config {
	return Config{
		Capacity:       1000,
		QJLProjections: 256,
		QJLSeed:        42,
		QJLVectorDim:   128,
		PQBitsPerDim:   0,  // Disabled by default.
		PQSeed:         7,
	}
}

// Store is an in-memory intent vector store with similarity search.
type Store struct {
	mu         sync.RWMutex
	records    []*IntentRecord
	signatures []QJLSignature      // Parallel QJL signatures (same index as records)
	compressed []CompressedVector  // Parallel PolarQuant codes (same index as records)
	index      map[string]int      // id → position in records
	capacity   int
	nextID     int
	qjl        *QJLProjection      // nil if QJL disabled
	pq         *PolarQuantCodec    // nil if PolarQuant disabled
	dropFloat  bool                // If true, clear rec.Vector after encoding
}

// New creates a new vector store.
func New(cfg *Config) *Store {
	c := DefaultConfig()
	if cfg != nil {
		if cfg.Capacity > 0 {
			c.Capacity = cfg.Capacity
		}
		if cfg.QJLProjections > 0 {
			c.QJLProjections = cfg.QJLProjections
		}
		if cfg.QJLSeed != 0 {
			c.QJLSeed = cfg.QJLSeed
		}
		if cfg.QJLVectorDim > 0 {
			c.QJLVectorDim = cfg.QJLVectorDim
		}
		if cfg.QJLProjections == -1 {
			c.QJLProjections = 0
		}
		if cfg.PQBitsPerDim > 0 {
			c.PQBitsPerDim = cfg.PQBitsPerDim
		}
		if cfg.PQSeed != 0 {
			c.PQSeed = cfg.PQSeed
		}
	}

	s := &Store{
		index:     make(map[string]int),
		capacity:  c.Capacity,
		dropFloat: cfg != nil && cfg.PQDropFloat64,
	}

	// Initialize QJL projection if enabled.
	if c.QJLProjections > 0 {
		s.qjl = NewQJLProjection(c.QJLProjections, c.QJLVectorDim, c.QJLSeed)
	}

	// Initialize PolarQuant codec if enabled.
	if c.PQBitsPerDim > 0 {
		s.pq = NewPolarQuantCodec(c.QJLVectorDim, c.PQBitsPerDim, c.PQSeed)
	}

	return s
}

// Add stores an intent record. Returns the assigned ID.
func (s *Store) Add(rec *IntentRecord) string {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Assign ID if empty.
	if rec.ID == "" {
		s.nextID++
		rec.ID = fmt.Sprintf("intent-%d", s.nextID)
	}
	if rec.CreatedAt.IsZero() {
		rec.CreatedAt = time.Now()
	}

	// LRU eviction: remove oldest if at capacity.
	if len(s.records) >= s.capacity {
		oldest := s.records[0]
		delete(s.index, oldest.ID)
		s.records = s.records[1:]
		if len(s.signatures) > 0 {
			s.signatures = s.signatures[1:]
		}
		if len(s.compressed) > 0 {
			s.compressed = s.compressed[1:]
		}
		// Rebuild index after shift.
		for i, r := range s.records {
			s.index[r.ID] = i
		}
	}

	s.index[rec.ID] = len(s.records)
	s.records = append(s.records, rec)

	// Auto-compute QJL signature if enabled and vector is present.
	if s.qjl != nil && len(rec.Vector) > 0 {
		sig := s.qjl.Quantize(rec.Vector)
		s.signatures = append(s.signatures, sig)
	} else {
		s.signatures = append(s.signatures, nil)
	}

	// Auto-compute PolarQuant compressed vector if enabled.
	if s.pq != nil && len(rec.Vector) > 0 {
		cv := s.pq.Encode(rec.Vector)
		s.compressed = append(s.compressed, cv)
		// Reclaim memory if configured.
		if s.dropFloat {
			rec.Vector = nil
		}
	} else {
		s.compressed = append(s.compressed, CompressedVector{})
	}

	return rec.ID
}

// Search finds the k most similar records to the given vector.
func (s *Store) Search(vector []float64, k int) []SearchResult {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.searchLocked(vector, k)
}

// searchLocked is the inner brute-force search. Caller must hold s.mu.RLock.
func (s *Store) searchLocked(vector []float64, k int) []SearchResult {
	if len(s.records) == 0 || len(vector) == 0 || k <= 0 {
		return nil
	}

	type scored struct {
		idx int
		sim float64
	}

	scores := make([]scored, 0, len(s.records))

	// Pre-encode query once if PolarQuant is active.
	var queryCv CompressedVector
	pqActive := s.pq != nil
	if pqActive {
		queryCv = s.pq.Encode(vector)
	}

	for i, rec := range s.records {
		var sim float64
		if len(rec.Vector) > 0 {
			// Exact cosine if vector is present.
			sim = CosineSimilarity(vector, rec.Vector)
		} else if pqActive && i < len(s.compressed) && len(s.compressed[i].Data) > 0 {
			// Fallback to compressed similarity if vector was dropped.
			sim = s.pq.CompressedSimilarity(queryCv, s.compressed[i])
		} else {
			continue
		}
		scores = append(scores, scored{idx: i, sim: sim})
	}

	// Sort by similarity descending.
	sort.Slice(scores, func(i, j int) bool {
		return scores[i].sim > scores[j].sim
	})

	if k > len(scores) {
		k = len(scores)
	}

	results := make([]SearchResult, k)
	for i := 0; i < k; i++ {
		results[i] = SearchResult{
			Record:     s.records[scores[i].idx],
			Similarity: scores[i].sim,
		}
	}
	return results
}

// SearchByRoute finds records matching a specific route.
func (s *Store) SearchByRoute(route string) []*IntentRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var results []*IntentRecord
	for _, rec := range s.records {
		if rec.Route == route {
			results = append(results, rec)
		}
	}
	return results
}

// Get retrieves a record by ID.
func (s *Store) Get(id string) *IntentRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()

	idx, ok := s.index[id]
	if !ok {
		return nil
	}
	return s.records[idx]
}

// SearchQJL performs two-phase approximate nearest-neighbor search using QJL.
//
// Phase 1: Score all records via POPCNT Hamming similarity on QJL signatures (O(bits/64) per record).
// Phase 2: Take top-2k candidates and rerank with exact CosineSimilarity.
// Returns top-k results with exact cosine similarity scores.
//
// Falls back to brute-force searchLocked() if QJL is not enabled.
func (s *Store) SearchQJL(vector []float64, k int) []SearchResult {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// Fallback to brute-force if QJL not enabled.
	if s.qjl == nil {
		return s.searchLocked(vector, k)
	}

	if len(s.records) == 0 || len(vector) == 0 || k <= 0 {
		return nil
	}

	// Phase 1: QJL approximate filter.
	querySig := s.qjl.Quantize(vector)
	numBits := s.qjl.NumProjections()

	type scored struct {
		idx int
		sim float64
	}

	candidates := make([]scored, 0, len(s.records))
	for i := range s.records {
		if i >= len(s.signatures) || s.signatures[i] == nil {
			continue
		}
		sim := HammingSimilarity(querySig, s.signatures[i], numBits)
		candidates = append(candidates, scored{idx: i, sim: sim})
	}

	// Sort by approximate similarity descending.
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].sim > candidates[j].sim
	})

	// Phase 2: Rerank top-2k candidates with higher-fidelity similarity.
	rankPool := 2 * k
	if rankPool > len(candidates) {
		rankPool = len(candidates)
	}

	exact := make([]scored, 0, rankPool)

	// Pre-encode query once for PolarQuant rerank (avoid re-encoding per candidate).
	var queryCv CompressedVector
	pqActive := s.pq != nil
	if pqActive {
		queryCv = s.pq.Encode(vector)
	}

	for i := 0; i < rankPool; i++ {
		idx := candidates[i].idx
		var sim float64

		if pqActive && idx < len(s.compressed) && len(s.compressed[idx].Data) > 0 {
			// PolarQuant compressed similarity (no full float64 decode).
			sim = s.pq.CompressedSimilarity(queryCv, s.compressed[idx])
		} else {
			// Full float64 cosine similarity.
			rec := s.records[idx]
			if len(rec.Vector) == 0 {
				continue
			}
			sim = CosineSimilarity(vector, rec.Vector)
		}
		exact = append(exact, scored{idx: idx, sim: sim})
	}

	// Sort by exact/compressed similarity descending.
	sort.Slice(exact, func(i, j int) bool {
		return exact[i].sim > exact[j].sim
	})

	if k > len(exact) {
		k = len(exact)
	}

	results := make([]SearchResult, k)
	for i := 0; i < k; i++ {
		results[i] = SearchResult{
			Record:     s.records[exact[i].idx],
			Similarity: exact[i].sim,
		}
	}
	return results
}

// QJLEnabled returns whether QJL quantization is active.
func (s *Store) QJLEnabled() bool {
	return s.qjl != nil
}

// PQEnabled returns whether PolarQuant compressed storage is active.
func (s *Store) PQEnabled() bool {
	return s.pq != nil
}

// GetStats returns store statistics.
func (s *Store) GetStats() Stats {
	s.mu.RLock()
	defer s.mu.RUnlock()

	stats := Stats{
		TotalRecords: len(s.records),
		Capacity:     s.capacity,
		RouteCount:   make(map[string]int),
		VerdictCount: make(map[string]int),
	}

	var totalEntropy float64
	for _, rec := range s.records {
		if rec.Route != "" {
			stats.RouteCount[rec.Route]++
		}
		if rec.Verdict != "" {
			stats.VerdictCount[rec.Verdict]++
		}
		totalEntropy += rec.Entropy
	}
	if len(s.records) > 0 {
		stats.AvgEntropy = totalEntropy / float64(len(s.records))
	}

	// QJL statistics.
	if s.qjl != nil {
		stats.QJLEnabled = true
		stats.QJLProjections = s.qjl.NumProjections()
		stats.QJLBitsPerVec = s.qjl.NumProjections()
		stats.QJLBytesPerVec = (s.qjl.NumProjections() + 63) / 64 * 8
	}

	// PolarQuant statistics.
	if s.pq != nil {
		stats.PQEnabled = true
		stats.PQBitsPerDim = s.pq.BitsPerDim()
		stats.PQBytesPerVec = s.pq.CompressedBytes() + 4 // +4 for float32 radius
		stats.PQCompressionRate = s.pq.CompressionRatio()
		stats.PQDropFloat64 = s.dropFloat
	}

	return stats
}

// Count returns the total number of records.
func (s *Store) Count() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.records)
}

// CosineSimilarity computes cosine similarity between two vectors.
// Returns value in [-1, 1], where 1 = identical direction.
func CosineSimilarity(a, b []float64) float64 {
	if len(a) != len(b) || len(a) == 0 {
		return 0
	}

	var dot, normA, normB float64
	for i := range a {
		dot += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}

	denom := math.Sqrt(normA) * math.Sqrt(normB)
	if denom == 0 {
		return 0
	}
	return dot / denom
}
