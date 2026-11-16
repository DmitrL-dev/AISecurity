package hardware

import (
	"context"
	"os"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/alert"
)

func testConfig(dir string) LeashConfig {
	return LeashConfig{
		KeyPath:       filepath.Join(dir, ".sentinel_key"),
		LeashPath:     filepath.Join(dir, ".sentinel_leash"),
		CheckInterval: 100 * time.Millisecond,
		MissThreshold: 3,
		SignalDir:     dir,
	}
}

func TestLeash_ArmedWhenKeyExists(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)

	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, nil)

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)
	assert.Equal(t, LeashArmed, leash.Status())
	cancel()
}

func TestLeash_TriggersOnMissingKey(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)

	var triggered atomic.Int32
	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, func() { triggered.Add(1) })

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	os.Remove(cfg.KeyPath)
	time.Sleep(350 * time.Millisecond)
	assert.GreaterOrEqual(t, triggered.Load(), int32(1))
	assert.Equal(t, LeashTriggered, leash.Status())
	cancel()
}

func TestLeash_ReArmsWhenKeyRestored(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)

	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, nil)

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	os.Remove(cfg.KeyPath)
	time.Sleep(120 * time.Millisecond)
	os.WriteFile(cfg.KeyPath, nil, 0o644)
	time.Sleep(120 * time.Millisecond)

	assert.Equal(t, LeashArmed, leash.Status())
	cancel()
}

func TestLeash_SignalExtract(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)

	var extracted atomic.Int32
	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, func() { extracted.Add(1) }, nil)

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	os.WriteFile(filepath.Join(dir, "signal_extract"), nil, 0o644)
	time.Sleep(120 * time.Millisecond)
	assert.GreaterOrEqual(t, extracted.Load(), int32(1))
	cancel()
}

func TestLeash_SignalApoptosis(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)

	var triggered atomic.Int32
	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, func() { triggered.Add(1) })

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	os.WriteFile(filepath.Join(dir, "signal_apoptosis"), nil, 0o644)
	time.Sleep(120 * time.Millisecond)
	assert.GreaterOrEqual(t, triggered.Load(), int32(1))
	assert.Equal(t, LeashTriggered, leash.Status())
	cancel()
}

func TestLeashStatus_String(t *testing.T) {
	assert.Equal(t, "DISARMED", LeashDisarmed.String())
	assert.Equal(t, "ARMED", LeashArmed.String())
	assert.Equal(t, "TRIGGERED", LeashTriggered.String())
}

// --- v3.2 State Machine Tests ---

func TestParseMode(t *testing.T) {
	assert.Equal(t, ModeArmed, ParseMode("ARMED"))
	assert.Equal(t, ModeArmed, ParseMode("armed"))
	assert.Equal(t, ModeArmed, ParseMode("anything"))
	assert.Equal(t, ModeArmed, ParseMode(""))
	assert.Equal(t, ModeZeroG, ParseMode("ZERO-G"))
	assert.Equal(t, ModeZeroG, ParseMode("ZEROG"))
	assert.Equal(t, ModeZeroG, ParseMode("ZERO_G"))
	assert.Equal(t, ModeZeroG, ParseMode("  zero-g  "))
	assert.Equal(t, ModeSafe, ParseMode("SAFE"))
	assert.Equal(t, ModeSafe, ParseMode("READ-ONLY"))
	assert.Equal(t, ModeSafe, ParseMode("READONLY"))
}

func TestSystemMode_String(t *testing.T) {
	assert.Equal(t, "ARMED", ModeArmed.String())
	assert.Equal(t, "ZERO-G", ModeZeroG.String())
	assert.Equal(t, "SAFE", ModeSafe.String())
}

func TestLeash_ModeDefault(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)

	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, nil)

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	// No .sentinel_leash file → ModeArmed.
	assert.Equal(t, ModeArmed, leash.Mode())
	cancel()
}

func TestLeash_ModeZeroG(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)
	os.WriteFile(cfg.LeashPath, []byte("ZERO-G"), 0o644)

	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, nil)

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	assert.Equal(t, ModeZeroG, leash.Mode())
	cancel()
}

func TestLeash_ModeSafe(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)
	os.WriteFile(cfg.LeashPath, []byte("SAFE"), 0o644)

	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, nil)

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	assert.Equal(t, ModeSafe, leash.Mode())
	cancel()
}

func TestLeash_ModeTransition(t *testing.T) {
	dir := t.TempDir()
	cfg := testConfig(dir)
	os.WriteFile(cfg.KeyPath, nil, 0o644)

	var transitions atomic.Int32
	bus := alert.NewBus(10)
	leash := NewLeash(cfg, bus, nil, nil)
	leash.SetModeChangeCallback(func(m SystemMode) {
		transitions.Add(1)
	})

	ctx, cancel := context.WithCancel(context.Background())
	go leash.Start(ctx)
	time.Sleep(120 * time.Millisecond)

	// ARMED → ZERO-G.
	require.NoError(t, os.WriteFile(cfg.LeashPath, []byte("ZERO-G"), 0o644))
	time.Sleep(200 * time.Millisecond)
	assert.Equal(t, ModeZeroG, leash.Mode())

	// ZERO-G → SAFE.
	require.NoError(t, os.WriteFile(cfg.LeashPath, []byte("SAFE"), 0o644))
	time.Sleep(200 * time.Millisecond)
	assert.Equal(t, ModeSafe, leash.Mode())

	assert.GreaterOrEqual(t, transitions.Load(), int32(2))
	cancel()
}
