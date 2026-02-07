package transport

import (
	"context"
	"math/rand"
	"net/http"
	"sync"
	"time"
)

// ============================================================================
// COVER TRAFFIC — Timing Correlation Mitigation
// ============================================================================
// If an adversary can observe both our outbound traffic AND the target's
// inbound traffic, they can correlate requests by timing.
//
// Cover traffic generates legitimate-looking HTTP requests to popular
// services CONCURRENTLY with the real probe, creating noise that makes
// timing correlation significantly harder.
//
// Usage:
//
//	ct := NewCoverTraffic()
//	go ct.GenerateBurst(ctx, 5)  // Fire 5 cover requests in background
//	probe.Execute(ctx)            // Real probe runs simultaneously
// ============================================================================

// CoverResult tracks a single cover traffic request.
type CoverResult struct {
	Target   string
	Status   int
	Duration time.Duration
	Error    string
}

// CoverTraffic generates noise requests to legitimate services.
type CoverTraffic struct {
	targets []string
	client  *http.Client
}

// NewCoverTraffic creates a cover traffic generator.
func NewCoverTraffic() *CoverTraffic {
	return &CoverTraffic{
		targets: []string{
			"https://www.google.com/generate_204",
			"https://www.gstatic.com/generate_204",
			"https://connectivity-check.ubuntu.com/",
			"https://www.apple.com/library/test/success.html",
			"https://detectportal.firefox.com/success.txt",
			"https://www.msftconnecttest.com/connecttest.txt",
			"https://cloudflare.com/cdn-cgi/trace",
			"https://api.github.com/zen",
			"https://httpbin.org/status/200",
			"https://www.cloudflare.com/favicon.ico",
		},
		client: &http.Client{
			Timeout: 10 * time.Second,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				if len(via) >= 3 {
					return http.ErrUseLastResponse
				}
				return nil
			},
		},
	}
}

// GenerateBurst fires `count` cover requests concurrently.
// Returns results for each request.
func (ct *CoverTraffic) GenerateBurst(ctx context.Context, count int) []CoverResult {
	if count <= 0 {
		return nil
	}

	var mu sync.Mutex
	results := make([]CoverResult, 0, count)
	var wg sync.WaitGroup

	for i := 0; i < count; i++ {
		select {
		case <-ctx.Done():
			break
		default:
		}

		wg.Add(1)
		target := ct.targets[rand.Intn(len(ct.targets))]

		go func(t string) {
			defer wg.Done()
			result := ct.doRequest(ctx, t)
			mu.Lock()
			results = append(results, result)
			mu.Unlock()
		}(target)

		// Stagger slightly (50-200ms) to look natural
		time.Sleep(time.Duration(50+rand.Intn(150)) * time.Millisecond)
	}

	wg.Wait()
	return results
}

// doRequest performs a single cover traffic request.
func (ct *CoverTraffic) doRequest(ctx context.Context, target string) CoverResult {
	start := time.Now()
	result := CoverResult{Target: target}

	req, err := http.NewRequestWithContext(ctx, "GET", target, nil)
	if err != nil {
		result.Error = err.Error()
		result.Duration = time.Since(start)
		return result
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "*/*")

	resp, err := ct.client.Do(req)
	if err != nil {
		result.Error = err.Error()
		result.Duration = time.Since(start)
		return result
	}
	resp.Body.Close()

	result.Status = resp.StatusCode
	result.Duration = time.Since(start)
	return result
}
