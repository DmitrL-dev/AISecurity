package soc

import (
	"math"
	"sync"
	"time"
)

// AlertCluster groups related SOC events using temporal + categorical similarity.
// Phase 1: temporal+session_id fallback (cold start).
// Phase 2: embedding-based DBSCAN when enough events accumulated.
//
// Cold start strategy (§7.6):
//
//	fallback: temporal_clustering
//	timeout:  5m — force embedding mode after 5 minutes even if <50 events
//	min_events_for_embedding: 50
type AlertCluster struct {
	ID        string     `json:"id"`
	TenantID  string     `json:"tenant_id,omitempty"` // owning tenant (clusters never span tenants)
	Events    []string   `json:"events"`     // Event IDs
	Category  string     `json:"category"`   // Dominant category
	Severity  string     `json:"severity"`   // Max severity
	Source    string     `json:"source"`      // Dominant source
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
}

// ClusterEngine groups related alerts using configurable strategies.
type ClusterEngine struct {
	mu       sync.RWMutex
	clusters map[string]*AlertCluster
	config   ClusterConfig

	// Cold start tracking
	startTime  time.Time
	eventCount int
	mode       ClusterMode
}

// ClusterConfig holds Alert Clustering parameters.
type ClusterConfig struct {
	// Cold start (§7.6)
	MinEventsForEmbedding int           `yaml:"min_events_for_embedding" json:"min_events_for_embedding"`
	ColdStartTimeout      time.Duration `yaml:"cold_start_timeout" json:"cold_start_timeout"`

	// Temporal clustering parameters
	TemporalWindow time.Duration `yaml:"temporal_window" json:"temporal_window"` // Group events within this window
	MaxClusterSize int           `yaml:"max_cluster_size" json:"max_cluster_size"`

	// Embedding clustering parameters (Phase 2)
	SimilarityThreshold float64 `yaml:"similarity_threshold" json:"similarity_threshold"` // 0.0-1.0
	EmbeddingModel      string  `yaml:"embedding_model" json:"embedding_model"`           // e.g., "all-MiniLM-L6-v2"
}

// DefaultClusterConfig returns the default clustering configuration (§7.6).
func DefaultClusterConfig() ClusterConfig {
	return ClusterConfig{
		MinEventsForEmbedding: 50,
		ColdStartTimeout:      5 * time.Minute,
		TemporalWindow:        2 * time.Minute,
		MaxClusterSize:        50,
		SimilarityThreshold:   0.75,
		EmbeddingModel:        "all-MiniLM-L6-v2",
	}
}

// ClusterMode tracks the engine operating mode.
type ClusterMode int

const (
	ClusterModeColdStart  ClusterMode = iota // Temporal+session_id fallback
	ClusterModeEmbedding                     // Full embedding-based clustering
)

func (m ClusterMode) String() string {
	switch m {
	case ClusterModeEmbedding:
		return "embedding"
	default:
		return "cold_start"
	}
}

// NewClusterEngine creates a cluster engine with the given config.
func NewClusterEngine(config ClusterConfig) *ClusterEngine {
	return &ClusterEngine{
		clusters:  make(map[string]*AlertCluster),
		config:    config,
		startTime: time.Now(),
		mode:      ClusterModeColdStart,
	}
}

// AddEvent assigns an event to a cluster. Returns the cluster ID.
func (ce *ClusterEngine) AddEvent(event SOCEvent) string {
	ce.mu.Lock()
	defer ce.mu.Unlock()

	ce.eventCount++

	// Check if we should transition to embedding mode
	if ce.mode == ClusterModeColdStart {
		if ce.eventCount >= ce.config.MinEventsForEmbedding ||
			time.Since(ce.startTime) >= ce.config.ColdStartTimeout {
			ce.mode = ClusterModeEmbedding
		}
	}

	// Phase 2: Embedding/semantic clustering (DBSCAN-inspired)
	if ce.mode == ClusterModeEmbedding {
		clusterID := ce.findSemanticCluster(event)
		if clusterID != "" {
			return clusterID
		}
	}

	// Fallback: Temporal + category clustering (Phase 1)
	clusterID := ce.findOrCreateTemporalCluster(event)
	return clusterID
}

// findSemanticCluster uses cosine similarity of event descriptions to find matching clusters.
// This is a simplified DBSCAN-inspired approach that works without an external ML model.
func (ce *ClusterEngine) findSemanticCluster(event SOCEvent) string {
	if event.Description == "" {
		return ""
	}

	eventVec := textToVector(event.Description)
	bestScore := 0.0
	bestCluster := ""

	for id, cluster := range ce.clusters {
		if cluster.TenantID != event.TenantID {
			continue // clusters never span tenants (Review 14.06 round-3)
		}
		if len(cluster.Events) >= ce.config.MaxClusterSize {
			continue
		}
		// Use cluster category + source as proxy embedding when no ML model
		clusterVec := textToVector(cluster.Category + " " + cluster.Source)
		sim := cosineSimilarity(eventVec, clusterVec)
		if sim > ce.config.SimilarityThreshold && sim > bestScore {
			bestScore = sim
			bestCluster = id
		}
	}

	if bestCluster != "" {
		c := ce.clusters[bestCluster]
		c.Events = append(c.Events, event.ID)
		c.UpdatedAt = time.Now()
		if event.Severity.Rank() > EventSeverity(c.Severity).Rank() {
			c.Severity = string(event.Severity)
		}
		return bestCluster
	}
	return ""
}

// textToVector creates a simple character-frequency vector for cosine similarity.
// Serves as fallback when no external embedding model is available.
func textToVector(text string) map[rune]float64 {
	vec := make(map[rune]float64)
	for _, r := range text {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r == '_' {
			vec[r]++
		}
	}
	return vec
}

// cosineSimilarity computes cosine similarity between two sparse vectors.
func cosineSimilarity(a, b map[rune]float64) float64 {
	dot := 0.0
	magA := 0.0
	magB := 0.0
	for k, v := range a {
		magA += v * v
		if bv, ok := b[k]; ok {
			dot += v * bv
		}
	}
	for _, v := range b {
		magB += v * v
	}
	if magA == 0 || magB == 0 {
		return 0
	}
	return dot / (math.Sqrt(magA) * math.Sqrt(magB))
}

// findOrCreateTemporalCluster groups by (category + source) within temporal window.
func (ce *ClusterEngine) findOrCreateTemporalCluster(event SOCEvent) string {
	now := time.Now()
	key := event.TenantID + ":" + string(event.Source) + ":" + event.Category

	// Search existing clusters within temporal window (same tenant only —
	// Review 14.06 round-3: clusters must never co-mingle tenants' events).
	for id, cluster := range ce.clusters {
		if cluster.TenantID == event.TenantID &&
			cluster.Category == event.Category &&
			cluster.Source == string(event.Source) &&
			now.Sub(cluster.UpdatedAt) <= ce.config.TemporalWindow &&
			len(cluster.Events) < ce.config.MaxClusterSize {
			// Add to existing cluster
			cluster.Events = append(cluster.Events, event.ID)
			cluster.UpdatedAt = now
			if event.Severity.Rank() > EventSeverity(cluster.Severity).Rank() {
				cluster.Severity = string(event.Severity)
			}
			return id
		}
	}

	// Create new cluster
	clusterID := "clst-" + key + "-" + now.Format("150405")
	ce.clusters[clusterID] = &AlertCluster{
		ID:        clusterID,
		TenantID:  event.TenantID,
		Events:    []string{event.ID},
		Category:  event.Category,
		Severity:  string(event.Severity),
		Source:    string(event.Source),
		CreatedAt: now,
		UpdatedAt: now,
	}
	return clusterID
}

// Stats returns clustering statistics.
func (ce *ClusterEngine) Stats() map[string]any {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	totalEvents := 0
	maxSize := 0
	for _, c := range ce.clusters {
		totalEvents += len(c.Events)
		if len(c.Events) > maxSize {
			maxSize = len(c.Events)
		}
	}

	avgSize := 0.0
	if len(ce.clusters) > 0 {
		avgSize = math.Round(float64(totalEvents)/float64(len(ce.clusters))*100) / 100
	}

	uiHint := "Smart clustering active"
	if ce.mode == ClusterModeColdStart {
		uiHint = "Clustering warming up..."
	}

	return map[string]any{
		"mode":            ce.mode.String(),
		"ui_hint":         uiHint,
		"total_clusters":  len(ce.clusters),
		"total_events":    totalEvents,
		"avg_cluster_size": avgSize,
		"max_cluster_size": maxSize,
		"events_processed": ce.eventCount,
		"embedding_model":  ce.config.EmbeddingModel,
		"cold_start_threshold": ce.config.MinEventsForEmbedding,
	}
}

// Clusters returns all current clusters.
//
// Each returned *AlertCluster is a fresh copy (including its Events slice).
// Returning the internal pointers would race with AddEvent, which mutates
// cluster.Events/Severity/UpdatedAt under the write lock after this method
// has released the read lock.
func (ce *ClusterEngine) Clusters() []*AlertCluster {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	result := make([]*AlertCluster, 0, len(ce.clusters))
	for _, c := range ce.clusters {
		cp := *c
		cp.Events = append([]string(nil), c.Events...)
		result = append(result, &cp)
	}
	return result
}

// DeleteByTenant drops all alert clusters owned by a tenant — part of GDPR
// Art.17 erasure (clusters are in-memory and tenant-stamped). Review 14.06 round-5.
func (ce *ClusterEngine) DeleteByTenant(tenantID string) {
	ce.mu.Lock()
	defer ce.mu.Unlock()
	for id, c := range ce.clusters {
		if c.TenantID == tenantID {
			delete(ce.clusters, id)
		}
	}
}
