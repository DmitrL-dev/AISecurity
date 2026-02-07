package artemis

import (
	"encoding/json"
	"os"
	"sort"
	"sync"

	"github.com/sentinel-community/strike-force/internal/domain/entity"
	"github.com/sentinel-community/strike-force/internal/domain/port"
)

// Controller implements the Brain interface with full adaptive logic
type Controller struct {
	mu sync.RWMutex

	// State
	testedVectors        map[string]bool
	successfulTechniques map[string]int      // technique -> count
	blockedTechniques    map[string]struct{} // set of blocked techniques globally (simplified)

	// Strategies
	strategies []string
	payloads   map[string][]string
}

// NewController creates a new Artemis Brain
func NewController() port.Brain {
	return &Controller{
		testedVectors:        make(map[string]bool),
		successfulTechniques: make(map[string]int),
		blockedTechniques:    make(map[string]struct{}),
		strategies: []string{
			"HPP_GET", "HPP_POST", "HEADER_INJECT", "CHUNKED_POST",
			"MULTIPART", "POST_JSON", "CLTE_SMUGGLE", "TECL_SMUGGLE",
			"SQLi", "XSS", "TRAVERSAL",
		},
		payloads: make(map[string][]string),
	}
}

func (c *Controller) SetPayloads(payloads map[string][]string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.payloads = payloads
}

// DecideNext selects the best technique based on weighted success history
func (c *Controller) DecideNext(target entity.Target, history []entity.Result) (*entity.Payload, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	// 1. Filter available strategies (not blocked, not exhausted for this target)
	candidates := []string{}
	for _, s := range c.strategies {
		if _, blocked := c.blockedTechniques[s]; !blocked {
			// Check if specifically exhausted for this target
			// Complex exhaustion check (simplified here: 1 shot per technique per target for now)
			// Ideally we iterate through all payloads for a technique.
			// Let's assume we want to try at least 1 payload per technique.
			key := target.ID + ":" + s
			if !c.testedVectors[key] {
				candidates = append(candidates, s)
			}
		}
	}

	if len(candidates) == 0 {
		return nil, false // Exhausted
	}

	// 2. Sort candidates by global success rate (Reinforcement Learning)
	sort.Slice(candidates, func(i, j int) bool {
		scoreI := c.successfulTechniques[candidates[i]]
		scoreJ := c.successfulTechniques[candidates[j]]
		return scoreI > scoreJ // Descending
	})

	// 3. Select best
	best := candidates[0]
	c.testedVectors[target.ID+":"+best] = true

	// 4. Select Payload
	value := "' OR 1=1 --" // Default fallback
	if list, ok := c.payloads[best]; ok && len(list) > 0 {
		// Pick one (random or sequential?)
		// For MVP, pick first for determinism, or random?
		// Let's pick first for now to ensure we hit a real payload.
		// TODO: Implement payload cursor
		value = list[0]
	}

	return &entity.Payload{
		ID:        target.ID + "_" + best,
		Value:     value,
		Type:      best,
		Technique: best,
	}, true
}

func (c *Controller) ReportResult(result entity.Result) {
	c.mu.Lock()
	defer c.mu.Unlock()

	// Extract technique from Payload (assuming Payload.Technique is set correctly)
	// For this MVP, we need to pass technique back or infer it.
	// We'll assuming the Engine passes the unmodified Payload.Technique back in an ideal world,
	// but currently Result struct doesn't have it. We'll skip precise tracking updates for this specific stub
	// unless we update the Result entity.

	// However, we CAN track global blocking:
	if result.Blocked {
		// Identify technique causing block (Hard without technique in Result)
		// TODO: Add Technique field to Result entity for precise feedback loop
	}
}

func (c *Controller) IsExhausted() bool {
	return false
}

func (c *Controller) Stats() map[string]interface{} {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return map[string]interface{}{
		"tested":         len(c.testedVectors),
		"blocked_global": len(c.blockedTechniques),
	}
}

// Persistence Struct
type BrainState struct {
	TestedVectors        map[string]bool `json:"tested_vectors"`
	SuccessfulTechniques map[string]int  `json:"successful_techniques"`
	BlockedTechniques    []string        `json:"blocked_techniques"` // Map not JSON friendly as set
}

func (c *Controller) SaveState(path string) error {
	c.mu.RLock()
	defer c.mu.RUnlock()

	blockedList := make([]string, 0, len(c.blockedTechniques))
	for k := range c.blockedTechniques {
		blockedList = append(blockedList, k)
	}

	state := BrainState{
		TestedVectors:        c.testedVectors,
		SuccessfulTechniques: c.successfulTechniques,
		BlockedTechniques:    blockedList,
	}

	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(path, data, 0644)
}

func (c *Controller) LoadState(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	var state BrainState
	if err := json.Unmarshal(data, &state); err != nil {
		return err
	}

	c.mu.Lock()
	defer c.mu.Unlock()

	c.testedVectors = state.TestedVectors
	c.successfulTechniques = state.SuccessfulTechniques

	c.blockedTechniques = make(map[string]struct{})
	for _, k := range state.BlockedTechniques {
		c.blockedTechniques[k] = struct{}{}
	}

	return nil
}
