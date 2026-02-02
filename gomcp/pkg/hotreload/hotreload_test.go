package hotreload

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func TestWatcher_InitialLoad(t *testing.T) {
	// Create temp config file
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "tools.json")

	cfg := ConfigFile{
		Version: "1.0",
		Tools: []ToolConfig{
			{Name: "test_tool", Description: "A test tool"},
		},
	}
	data, _ := json.Marshal(cfg)
	os.WriteFile(cfgPath, data, 0644)

	// Create watcher
	w := NewWatcher(WatcherConfig{
		Paths:        []string{cfgPath},
		PollInterval: 50 * time.Millisecond,
	})

	var receivedEvents []ReloadEvent
	var mu sync.Mutex

	w.OnReload(func(event ReloadEvent) {
		mu.Lock()
		receivedEvents = append(receivedEvents, event)
		mu.Unlock()
	})

	err := w.Start()
	if err != nil {
		t.Fatalf("failed to start watcher: %v", err)
	}
	defer w.Stop()

	// Should have loaded initial config
	time.Sleep(100 * time.Millisecond)

	mu.Lock()
	eventCount := len(receivedEvents)
	mu.Unlock()

	if eventCount == 0 {
		t.Error("expected at least one load event")
	}

	if receivedEvents[0].Action != ActionLoaded {
		t.Errorf("expected action Loaded, got %s", receivedEvents[0].Action)
	}
	if len(receivedEvents[0].Tools) != 1 {
		t.Errorf("expected 1 tool, got %d", len(receivedEvents[0].Tools))
	}
}

func TestWatcher_DetectsFileChange(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "tools.json")

	// Initial config
	cfg := ConfigFile{
		Version: "1.0",
		Tools:   []ToolConfig{{Name: "tool1"}},
	}
	data, _ := json.Marshal(cfg)
	os.WriteFile(cfgPath, data, 0644)

	w := NewWatcher(WatcherConfig{
		Paths:        []string{cfgPath},
		PollInterval: 50 * time.Millisecond,
	})

	var events []ReloadEvent
	var mu sync.Mutex

	w.OnReload(func(event ReloadEvent) {
		mu.Lock()
		events = append(events, event)
		mu.Unlock()
	})

	w.Start()
	defer w.Stop()

	time.Sleep(100 * time.Millisecond)

	// Modify config
	cfg.Tools = append(cfg.Tools, ToolConfig{Name: "tool2"})
	data, _ = json.Marshal(cfg)
	os.WriteFile(cfgPath, data, 0644)

	time.Sleep(150 * time.Millisecond)

	mu.Lock()
	eventCount := len(events)
	mu.Unlock()

	if eventCount < 2 {
		t.Errorf("expected at least 2 events (load + reload), got %d", eventCount)
	}

	// Last event should be reload
	mu.Lock()
	lastEvent := events[len(events)-1]
	mu.Unlock()

	if lastEvent.Action != ActionReloaded {
		t.Errorf("expected ActionReloaded, got %s", lastEvent.Action)
	}
	if len(lastEvent.Tools) != 2 {
		t.Errorf("expected 2 tools after reload, got %d", len(lastEvent.Tools))
	}
}

func TestWatcher_DetectsFileRemoval(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "tools.json")

	cfg := ConfigFile{Version: "1.0", Tools: []ToolConfig{{Name: "temp"}}}
	data, _ := json.Marshal(cfg)
	os.WriteFile(cfgPath, data, 0644)

	// Watch the DIRECTORY, not the file directly, so we can detect removal
	w := NewWatcher(WatcherConfig{
		Paths:        []string{dir},
		PollInterval: 50 * time.Millisecond,
	})

	var events []ReloadEvent
	var mu sync.Mutex

	w.OnReload(func(event ReloadEvent) {
		mu.Lock()
		events = append(events, event)
		mu.Unlock()
	})

	w.Start()
	defer w.Stop()

	time.Sleep(100 * time.Millisecond)

	// Remove file
	os.Remove(cfgPath)

	// Use retry loop for more reliable detection on busy systems
	foundRemove := false
	for attempt := 0; attempt < 10; attempt++ {
		time.Sleep(100 * time.Millisecond)

		mu.Lock()
		for _, e := range events {
			if e.Action == ActionRemoved {
				foundRemove = true
				break
			}
		}
		mu.Unlock()

		if foundRemove {
			break
		}
	}

	if !foundRemove {
		t.Error("expected ActionRemoved event after file deletion")
	}
}

func TestWatcher_WatchesDirectory(t *testing.T) {
	dir := t.TempDir()

	// Create initial file
	cfg := ConfigFile{Version: "1.0", Tools: []ToolConfig{{Name: "dir_tool"}}}
	data, _ := json.Marshal(cfg)
	os.WriteFile(filepath.Join(dir, "config1.json"), data, 0644)

	w := NewWatcher(WatcherConfig{
		Paths:        []string{dir},
		PollInterval: 50 * time.Millisecond,
	})

	var events []ReloadEvent
	var mu sync.Mutex

	w.OnReload(func(event ReloadEvent) {
		mu.Lock()
		events = append(events, event)
		mu.Unlock()
	})

	w.Start()
	defer w.Stop()

	time.Sleep(100 * time.Millisecond)

	// Add new file
	cfg2 := ConfigFile{Version: "1.0", Tools: []ToolConfig{{Name: "new_tool"}}}
	data2, _ := json.Marshal(cfg2)
	os.WriteFile(filepath.Join(dir, "config2.json"), data2, 0644)

	time.Sleep(150 * time.Millisecond)

	mu.Lock()
	eventCount := len(events)
	mu.Unlock()

	if eventCount < 2 {
		t.Errorf("expected at least 2 events, got %d", eventCount)
	}
}

func TestWatcher_HandlesInvalidJSON(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "bad.json")

	os.WriteFile(cfgPath, []byte("not valid json"), 0644)

	w := NewWatcher(WatcherConfig{
		Paths:        []string{cfgPath},
		PollInterval: 50 * time.Millisecond,
	})

	var events []ReloadEvent
	var mu sync.Mutex

	w.OnReload(func(event ReloadEvent) {
		mu.Lock()
		events = append(events, event)
		mu.Unlock()
	})

	w.Start()
	defer w.Stop()

	time.Sleep(100 * time.Millisecond)

	mu.Lock()
	defer mu.Unlock()

	if len(events) == 0 {
		t.Fatal("expected at least one event")
	}

	if events[0].Action != ActionError {
		t.Errorf("expected ActionError for invalid JSON, got %s", events[0].Action)
	}
	if events[0].Error == nil {
		t.Error("expected error to be set for invalid JSON")
	}
}

func TestWatcher_LoadedTools(t *testing.T) {
	dir := t.TempDir()

	cfg1 := ConfigFile{Version: "1.0", Tools: []ToolConfig{{Name: "t1"}, {Name: "t2"}}}
	cfg2 := ConfigFile{Version: "1.0", Tools: []ToolConfig{{Name: "t3"}}}

	data1, _ := json.Marshal(cfg1)
	data2, _ := json.Marshal(cfg2)

	os.WriteFile(filepath.Join(dir, "a.json"), data1, 0644)
	os.WriteFile(filepath.Join(dir, "b.json"), data2, 0644)

	w := NewWatcher(WatcherConfig{Paths: []string{dir}})

	tools := w.LoadedTools()
	if len(tools) != 3 {
		t.Errorf("expected 3 tools, got %d", len(tools))
	}
}

func TestWatcher_IsRunning(t *testing.T) {
	w := NewWatcher(WatcherConfig{
		Paths:        []string{t.TempDir()},
		PollInterval: 50 * time.Millisecond,
	})

	if w.IsRunning() {
		t.Error("should not be running before Start()")
	}

	w.Start()
	if !w.IsRunning() {
		t.Error("should be running after Start()")
	}

	w.Stop()
	time.Sleep(100 * time.Millisecond)
}

// Benchmark
func BenchmarkWatcher_FileHash(b *testing.B) {
	dir := b.TempDir()
	cfgPath := filepath.Join(dir, "bench.json")

	cfg := ConfigFile{Version: "1.0", Tools: make([]ToolConfig, 100)}
	for i := 0; i < 100; i++ {
		cfg.Tools[i] = ToolConfig{Name: "tool_" + string(rune('A'+i%26))}
	}
	data, _ := json.Marshal(cfg)
	os.WriteFile(cfgPath, data, 0644)

	w := NewWatcher(WatcherConfig{Paths: []string{cfgPath}})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		w.fileHash(cfgPath)
	}
}
