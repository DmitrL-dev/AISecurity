package stealth

import (
	"math/rand/v2"
	"time"
)

// Jitter adds Gaussian-distributed random delays to operations.
// This prevents traffic analysis from identifying tunnel traffic
// by its timing patterns.
type Jitter struct {
	// Mean delay in milliseconds.
	Mean float64

	// StdDev is the standard deviation in milliseconds.
	StdDev float64
}

// NewJitter creates a jitter with typical browser-like timing.
func NewJitter() *Jitter {
	return &Jitter{
		Mean:   50, // 50ms average
		StdDev: 20, // ±20ms spread
	}
}

// Wait blocks for a random duration drawn from the
// Gaussian distribution. Mimics natural human/browser timing.
func (j *Jitter) Wait() {
	delay := j.Mean + j.StdDev*rand.NormFloat64()
	if delay < 1 {
		delay = 1
	}
	time.Sleep(time.Duration(delay) * time.Millisecond)
}

// Duration returns a random duration without blocking.
func (j *Jitter) Duration() time.Duration {
	delay := j.Mean + j.StdDev*rand.NormFloat64()
	if delay < 1 {
		delay = 1
	}
	return time.Duration(delay) * time.Millisecond
}
