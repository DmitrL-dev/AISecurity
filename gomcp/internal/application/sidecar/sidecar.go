package sidecar

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"sync/atomic"
	"time"
)

// Config holds sidecar runtime configuration.
type Config struct {
	SensorType   string        // sentinel-core, shield, immune, generic
	LogPath      string        // Path to sensor log file, or "stdin"
	BusURL       string        // SOC Event Bus URL (e.g., http://localhost:9100)
	SensorID     string        // Sensor registration ID
	APIKey       string        // Sensor API key
	PollInterval time.Duration // Log file poll interval
}

// Stats tracks sidecar runtime metrics (thread-safe via atomic).
type Stats struct {
	LinesRead  atomic.Int64
	EventsSent atomic.Int64
	Errors     atomic.Int64
	StartedAt  time.Time
}

// StatsSnapshot is a non-atomic copy for reading/logging.
type StatsSnapshot struct {
	LinesRead  int64     `json:"lines_read"`
	EventsSent int64     `json:"events_sent"`
	Errors     int64     `json:"errors"`
	StartedAt  time.Time `json:"started_at"`
}

// Sidecar is the main orchestrator: tailer → parser → bus client.
type Sidecar struct {
	config Config
	parser Parser
	client *BusClient
	tailer *Tailer
	stats  Stats
}

// New creates a Sidecar with the given config.
func New(cfg Config) *Sidecar {
	return &Sidecar{
		config: cfg,
		parser: ParserForSensor(cfg.SensorType),
		client: NewBusClient(cfg.BusURL, cfg.SensorID, cfg.APIKey),
		tailer: NewTailer(cfg.PollInterval),
		stats:  Stats{StartedAt: time.Now()},
	}
}

// Run starts the sidecar pipeline: tail → parse → send.
// Blocks until ctx is cancelled.
func (s *Sidecar) Run(ctx context.Context) error {
	slog.Info("sidecar: starting",
		"sensor_type", s.config.SensorType,
		"log_path", s.config.LogPath,
		"bus_url", s.config.BusURL,
		"sensor_id", s.config.SensorID,
	)

	// Start line source.
	var lines <-chan string
	if s.config.LogPath == "stdin" || s.config.LogPath == "-" {
		lines = s.tailer.FollowStdin(ctx)
	} else {
		var err error
		lines, err = s.tailer.FollowFile(ctx, s.config.LogPath)
		if err != nil {
			return fmt.Errorf("sidecar: open log: %w", err)
		}
	}

	// Heartbeat goroutine.
	go s.heartbeatLoop(ctx)

	// Main pipeline loop (shared with RunReader).
	return s.processLines(ctx, lines)
}

// RunReader runs the sidecar from any io.Reader (for testing).
func (s *Sidecar) RunReader(ctx context.Context, r io.Reader) error {
	lines := s.tailer.FollowReader(ctx, r)
	return s.processLines(ctx, lines)
}

// processLines is the shared pipeline loop: parse → send → stats.
// Extracted to DRY between Run() and RunReader() (H-3 fix).
func (s *Sidecar) processLines(ctx context.Context, lines <-chan string) error {
	for {
		select {
		case <-ctx.Done():
			slog.Info("sidecar: shutting down",
				"lines_read", s.stats.LinesRead.Load(),
				"events_sent", s.stats.EventsSent.Load(),
				"errors", s.stats.Errors.Load(),
			)
			return nil

		case line, ok := <-lines:
			if !ok {
				slog.Info("sidecar: input closed")
				return nil
			}

			s.stats.LinesRead.Add(1)

			evt, ok := s.parser.Parse(line)
			if !ok {
				continue // Not a security event.
			}

			evt.SensorID = s.config.SensorID
			if err := s.client.SendEvent(ctx, evt); err != nil {
				s.stats.Errors.Add(1)
				slog.Error("sidecar: send failed",
					"error", err,
					"category", evt.Category,
				)
				continue
			}
			s.stats.EventsSent.Add(1)
		}
	}
}

// GetStats returns a snapshot of current runtime metrics (thread-safe).
func (s *Sidecar) GetStats() StatsSnapshot {
	return StatsSnapshot{
		LinesRead:  s.stats.LinesRead.Load(),
		EventsSent: s.stats.EventsSent.Load(),
		Errors:     s.stats.Errors.Load(),
		StartedAt:  s.stats.StartedAt,
	}
}

func (s *Sidecar) heartbeatLoop(ctx context.Context) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if err := s.client.Heartbeat(); err != nil {
				slog.Warn("sidecar: heartbeat failed", "error", err)
			}
		}
	}
}
