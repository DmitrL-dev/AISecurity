package challenge

import (
	"testing"
	"time"
)

func TestEngine_GenerateChallenge(t *testing.T) {
	engine := NewEngine(DefaultConfig())
	
	challenge := engine.GenerateChallenge("test-client", 0)
	
	if challenge.ID == "" {
		t.Error("challenge ID should not be empty")
	}
	if challenge.Nonce == "" {
		t.Error("challenge nonce should not be empty")
	}
	if challenge.Difficulty != 4 {
		t.Errorf("expected default difficulty 4, got %d", challenge.Difficulty)
	}
}

func TestEngine_VerifySolution_Valid(t *testing.T) {
	engine := NewEngine(Config{
		DefaultDifficulty: 2, // Low difficulty for fast test
		ChallengeTTL:      5 * time.Minute,
		Algorithm:         "fast",
	})
	
	challenge := engine.GenerateChallenge("test-client", 2)
	
	// Solve the challenge
	answer, iterations := SolveChallenge(challenge.Nonce, challenge.Difficulty)
	t.Logf("Solved challenge in %d iterations", iterations)
	
	solution := &Solution{
		ChallengeID: challenge.ID,
		Nonce:       challenge.Nonce,
		Answer:      answer,
	}
	
	result := engine.VerifySolution(solution)
	
	if !result.Valid {
		t.Errorf("expected valid solution, got: %s", result.Message)
	}
}

func TestEngine_VerifySolution_Invalid(t *testing.T) {
	engine := NewEngine(DefaultConfig())
	
	challenge := engine.GenerateChallenge("test-client", 4)
	
	// Submit wrong answer
	solution := &Solution{
		ChallengeID: challenge.ID,
		Nonce:       challenge.Nonce,
		Answer:      "wrong-answer",
	}
	
	result := engine.VerifySolution(solution)
	
	if result.Valid {
		t.Error("expected invalid solution")
	}
}

func TestEngine_VerifySolution_NotFound(t *testing.T) {
	engine := NewEngine(DefaultConfig())
	
	solution := &Solution{
		ChallengeID: "nonexistent",
		Nonce:       "test",
		Answer:      "answer",
	}
	
	result := engine.VerifySolution(solution)
	
	if result.Valid {
		t.Error("expected invalid for nonexistent challenge")
	}
	if result.Message != "challenge not found or expired" {
		t.Errorf("unexpected message: %s", result.Message)
	}
}

func TestEngine_OneTimeUse(t *testing.T) {
	engine := NewEngine(Config{
		DefaultDifficulty: 2,
		ChallengeTTL:      5 * time.Minute,
		Algorithm:         "fast",
	})
	
	challenge := engine.GenerateChallenge("test-client", 2)
	answer, _ := SolveChallenge(challenge.Nonce, challenge.Difficulty)
	
	solution := &Solution{
		ChallengeID: challenge.ID,
		Nonce:       challenge.Nonce,
		Answer:      answer,
	}
	
	// First verification should succeed
	result1 := engine.VerifySolution(solution)
	if !result1.Valid {
		t.Error("first verification should succeed")
	}
	
	// Second verification should fail (challenge consumed)
	result2 := engine.VerifySolution(solution)
	if result2.Valid {
		t.Error("second verification should fail (one-time use)")
	}
}

func TestVerifyPoW(t *testing.T) {
	// Test with known values
	nonce := "test_nonce"
	
	// Find a valid answer for difficulty 1
	answer, iterations := SolveChallenge(nonce, 1)
	t.Logf("Difficulty 1: solved in %d iterations", iterations)
	
	if !verifyPoW(nonce, answer, 1) {
		t.Error("should verify valid PoW")
	}
	
	if verifyPoW(nonce, "invalid", 1) {
		t.Error("should not verify invalid PoW")
	}
}

func TestSolveChallenge_Performance(t *testing.T) {
	nonce := "benchmark_nonce"
	
	difficulties := []int{1, 2, 3, 4}
	
	for _, diff := range difficulties {
		start := time.Now()
		_, iterations := SolveChallenge(nonce, diff)
		duration := time.Since(start)
		
		t.Logf("Difficulty %d: %d iterations, %v", diff, iterations, duration)
	}
}

func BenchmarkVerifyPoW(b *testing.B) {
	nonce := "bench_nonce"
	answer, _ := SolveChallenge(nonce, 4)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		verifyPoW(nonce, answer, 4)
	}
}

func BenchmarkSolveChallenge_Difficulty4(b *testing.B) {
	for i := 0; i < b.N; i++ {
		SolveChallenge("bench_nonce", 4)
	}
}
