package artemis

import (
	"testing"
)

func TestArtemisController(t *testing.T) {
	c := NewController()

	// 1. Test Best Technique Selection
	tech := c.GetBestTechnique("sqli")
	if tech == "" {
		t.Error("Expected valid technique, got empty string")
	}

	// 2. Test Blocking & Rotation
	// Block "HPP_GET" 5 times
	for i := 0; i < 5; i++ {
		c.RecordBlock("sqli", "HPP_GET")
	}

	// Should now pick something else or log rotation (logic dep)
	nextTech := c.GetBestTechnique("sqli")
	if nextTech == "HPP_GET" {
		t.Errorf("Technique HPP_GET should be blocked, got %s", nextTech)
	}

	// 3. Test Success Reset
	c.RecordBypass("sqli", "CHUNKED_POST")
	if c.consecutiveBlocks != 0 {
		t.Errorf("Expected consecutive blocks to reset to 0, got %d", c.consecutiveBlocks)
	}

	// 4. Test Exhaustion Principle
	c.requiredVectors["vec1:param1"] = true
	if c.IsExhausted() {
		t.Error("Should not be exhausted yet")
	}
	c.MarkVectorTested("vec1", "param1")
	if !c.IsExhausted() {
		t.Error("Should be exhausted now")
	}
}
