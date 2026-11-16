// Package main provides the Universal Sidecar CLI entry point (§5.5).
//
// Usage:
//
//	sentinel-sidecar --sensor-type=sentinel-core --log-path=/var/log/core.log --bus-url=http://localhost:9100
//	sentinel-sidecar --sensor-type=shield --stdin --bus-url=http://localhost:9100
//	echo "[DETECT] engine=jailbreak confidence=0.95 pattern=DAN" | sentinel-sidecar --sensor-type=sentinel-core --stdin
//
// Environment variables:
//
//	SIDECAR_SENSOR_TYPE    sentinel-core|shield|immune|generic
//	SIDECAR_LOG_PATH       Path to sensor log file (or "stdin")
//	SIDECAR_BUS_URL        SOC Event Bus URL (default: http://localhost:9100)
//	SIDECAR_SENSOR_ID      Sensor ID for registration
//	SIDECAR_API_KEY        Sensor API key
package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/syntrex/gomcp/internal/application/sidecar"
)

func main() {
	sensorType := flag.String("sensor-type", env("SIDECAR_SENSOR_TYPE", "sentinel-core"),
		"Sensor type: sentinel-core, shield, immune, generic")
	logPath := flag.String("log-path", env("SIDECAR_LOG_PATH", ""),
		"Path to sensor log file")
	useStdin := flag.Bool("stdin", false,
		"Read from stdin instead of log file")
	busURL := flag.String("bus-url", env("SIDECAR_BUS_URL", "http://localhost:9100"),
		"SOC Event Bus URL")
	sensorID := flag.String("sensor-id", env("SIDECAR_SENSOR_ID", ""),
		"Sensor registration ID")
	apiKey := flag.String("api-key", env("SIDECAR_API_KEY", ""),
		"Sensor API key")

	flag.Parse()

	// Derive sensor ID from type if not set.
	if *sensorID == "" {
		*sensorID = fmt.Sprintf("sidecar-%s", *sensorType)
	}

	// Determine log source.
	source := *logPath
	if *useStdin || source == "" {
		source = "stdin"
	}

	cfg := sidecar.Config{
		SensorType:   *sensorType,
		LogPath:      source,
		BusURL:       *busURL,
		SensorID:     *sensorID,
		APIKey:       *apiKey,
		PollInterval: 200 * time.Millisecond,
	}

	slog.Info("sentinel-sidecar starting",
		"sensor_type", cfg.SensorType,
		"log_path", cfg.LogPath,
		"bus_url", cfg.BusURL,
		"sensor_id", cfg.SensorID,
	)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	sc := sidecar.New(cfg)
	if err := sc.Run(ctx); err != nil {
		slog.Error("sidecar exited with error", "error", err)
		os.Exit(1)
	}

	slog.Info("sentinel-sidecar stopped", "stats", sc.GetStats())
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
