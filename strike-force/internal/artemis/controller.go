package artemis

import (
	"fmt"
	"log"
	"sync"
)

// Controller implements the ARTEMIS Adaptive Attack Controller logic
type Controller struct {
	mu                   sync.RWMutex
	successfulTechniques map[string][]string
	blockedTechniques    map[string]map[string]bool
	consecutiveBlocks    int
	testedVectors        map[string]bool
	requiredVectors      map[string]bool
}

// NewController creates a new thread-safe Artemis controller
func NewController() *Controller {
	return &Controller{
		successfulTechniques: make(map[string][]string),
		blockedTechniques:    make(map[string]map[string]bool),
		testedVectors:        make(map[string]bool),
		requiredVectors:      make(map[string]bool),
	}
}

// RecordBlock records a blocked attempt and triggers technique rotation if needed
func (c *Controller) RecordBlock(attackType, technique string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if _, exists := c.blockedTechniques[attackType]; !exists {
		c.blockedTechniques[attackType] = make(map[string]bool)
	}
	c.blockedTechniques[attackType][technique] = true
	c.consecutiveBlocks++

	if c.consecutiveBlocks >= 5 && c.consecutiveBlocks%5 == 0 {
		log.Printf("⚡ ARTEMIS: %d consecutive blocks, switching techniques", c.consecutiveBlocks)
	}
}

// RecordBypass records a successful bypass
func (c *Controller) RecordBypass(attackType, technique string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.successfulTechniques[attackType] = append(c.successfulTechniques[attackType], technique)
	c.consecutiveBlocks = 0 // Reset blocks on success
}

// GetBestTechnique selects the best technique excluding blocked ones
func (c *Controller) GetBestTechnique(attackType string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	allTechniques := []string{
		"HPP_GET", "HPP_POST", "HEADER_INJECT", "CHUNKED_POST",
		"MULTIPART", "POST_JSON", "CLTE_SMUGGLE", "TECL_SMUGGLE",
	}

	blocked := c.blockedTechniques[attackType]
	for _, tech := range allTechniques {
		if !blocked[tech] {
			return tech
		}
	}
	return "HPP_GET" // Fallback
}

// Exhaustion Principle: Mark vector as tested
func (c *Controller) MarkVectorTested(vector, param string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	key := fmt.Sprintf("%s:%s", vector, param)
	c.testedVectors[key] = true
}

// Check if exhausted
func (c *Controller) IsExhausted() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if len(c.requiredVectors) == 0 {
		return true
	}
	for req := range c.requiredVectors {
		if !c.testedVectors[req] {
			return false
		}
	}
	return true
}
