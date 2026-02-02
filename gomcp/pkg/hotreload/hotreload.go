// Package hotreload provides file-watching and dynamic tool reloading for GoMCP.
package hotreload

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// ToolConfig represents a tool configuration loaded from file
type ToolConfig struct {
	Name           string          `json:"name"`
	Description    string          `json:"description"`
	InputSchema    json.RawMessage `json:"inputSchema"`
	Command        string          `json:"command,omitempty"`
	Args           []string        `json:"args,omitempty"`
	DefaultTimeout int             `json:"defaultTimeoutMs,omitempty"`
}

// ConfigFile represents a tools configuration file
type ConfigFile struct {
	Version string       `json:"version"`
	Tools   []ToolConfig `json:"tools"`
}

// ReloadEvent represents a configuration change
type ReloadEvent struct {
	Timestamp time.Time
	FilePath  string
	Action    ReloadAction
	Tools     []ToolConfig
	Error     error
}

// ReloadAction describes what happened
type ReloadAction string

const (
	ActionLoaded   ReloadAction = "loaded"
	ActionReloaded ReloadAction = "reloaded"
	ActionRemoved  ReloadAction = "removed"
	ActionError    ReloadAction = "error"
)

// Watcher monitors configuration files for changes and triggers reloads
type Watcher struct {
	paths      []string
	interval   time.Duration
	handlers   []func(ReloadEvent)
	fileHashes map[string]string
	mu         sync.RWMutex
	ctx        context.Context
	cancel     context.CancelFunc
	running    bool
}

// WatcherConfig configures the file watcher
type WatcherConfig struct {
	// Paths to watch (files or directories)
	Paths []string
	// PollInterval for checking changes (default: 1s)
	PollInterval time.Duration
}

// NewWatcher creates a new configuration watcher
func NewWatcher(cfg WatcherConfig) *Watcher {
	if cfg.PollInterval == 0 {
		cfg.PollInterval = time.Second
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &Watcher{
		paths:      cfg.Paths,
		interval:   cfg.PollInterval,
		handlers:   make([]func(ReloadEvent), 0),
		fileHashes: make(map[string]string),
		ctx:        ctx,
		cancel:     cancel,
	}
}

// OnReload registers a handler for reload events
func (w *Watcher) OnReload(handler func(ReloadEvent)) {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.handlers = append(w.handlers, handler)
}

// Start begins watching for configuration changes
func (w *Watcher) Start() error {
	w.mu.Lock()
	if w.running {
		w.mu.Unlock()
		return nil
	}
	w.running = true
	w.mu.Unlock()

	// Initial load
	if err := w.loadAll(); err != nil {
		return fmt.Errorf("initial load failed: %w", err)
	}

	go w.watchLoop()
	return nil
}

// Stop stops watching for changes
func (w *Watcher) Stop() {
	w.cancel()
}

func (w *Watcher) watchLoop() {
	ticker := time.NewTicker(w.interval)
	defer ticker.Stop()

	for {
		select {
		case <-w.ctx.Done():
			return
		case <-ticker.C:
			w.checkForChanges()
		}
	}
}

func (w *Watcher) loadAll() error {
	files, err := w.collectConfigFiles()
	if err != nil {
		return err
	}

	for _, path := range files {
		w.loadFile(path, ActionLoaded)
	}

	return nil
}

func (w *Watcher) collectConfigFiles() ([]string, error) {
	var files []string

	for _, path := range w.paths {
		info, err := os.Stat(path)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return nil, err
		}

		if info.IsDir() {
			matches, err := filepath.Glob(filepath.Join(path, "*.json"))
			if err != nil {
				return nil, err
			}
			files = append(files, matches...)
		} else {
			files = append(files, path)
		}
	}

	return files, nil
}

func (w *Watcher) checkForChanges() {
	files, err := w.collectConfigFiles()
	if err != nil {
		w.emit(ReloadEvent{
			Timestamp: time.Now(),
			Action:    ActionError,
			Error:     err,
		})
		return
	}

	currentFiles := make(map[string]bool)
	for _, path := range files {
		currentFiles[path] = true
		w.checkFile(path)
	}

	// Check for removed files
	w.mu.RLock()
	removedFiles := make([]string, 0)
	for path := range w.fileHashes {
		if !currentFiles[path] {
			removedFiles = append(removedFiles, path)
		}
	}
	w.mu.RUnlock()

	for _, path := range removedFiles {
		w.mu.Lock()
		delete(w.fileHashes, path)
		w.mu.Unlock()

		w.emit(ReloadEvent{
			Timestamp: time.Now(),
			FilePath:  path,
			Action:    ActionRemoved,
		})
	}
}

func (w *Watcher) checkFile(path string) {
	hash, err := w.fileHash(path)
	if err != nil {
		w.emit(ReloadEvent{
			Timestamp: time.Now(),
			FilePath:  path,
			Action:    ActionError,
			Error:     err,
		})
		return
	}

	w.mu.RLock()
	oldHash, exists := w.fileHashes[path]
	w.mu.RUnlock()

	if !exists || oldHash != hash {
		action := ActionReloaded
		if !exists {
			action = ActionLoaded
		}
		w.loadFile(path, action)
	}
}

func (w *Watcher) loadFile(path string, action ReloadAction) {
	data, err := os.ReadFile(path)
	if err != nil {
		w.emit(ReloadEvent{
			Timestamp: time.Now(),
			FilePath:  path,
			Action:    ActionError,
			Error:     err,
		})
		return
	}

	var cfg ConfigFile
	if err := json.Unmarshal(data, &cfg); err != nil {
		w.emit(ReloadEvent{
			Timestamp: time.Now(),
			FilePath:  path,
			Action:    ActionError,
			Error:     fmt.Errorf("invalid JSON: %w", err),
		})
		return
	}

	hash := fmt.Sprintf("%x", sha256.Sum256(data))
	w.mu.Lock()
	w.fileHashes[path] = hash
	w.mu.Unlock()

	w.emit(ReloadEvent{
		Timestamp: time.Now(),
		FilePath:  path,
		Action:    action,
		Tools:     cfg.Tools,
	})
}

func (w *Watcher) fileHash(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", sha256.Sum256(data)), nil
}

func (w *Watcher) emit(event ReloadEvent) {
	w.mu.RLock()
	handlers := make([]func(ReloadEvent), len(w.handlers))
	copy(handlers, w.handlers)
	w.mu.RUnlock()

	for _, h := range handlers {
		h(event)
	}
}

// IsRunning returns whether the watcher is active
func (w *Watcher) IsRunning() bool {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return w.running
}

// LoadedTools returns currently loaded tool configs from all files
func (w *Watcher) LoadedTools() []ToolConfig {
	files, _ := w.collectConfigFiles()
	var allTools []ToolConfig

	for _, path := range files {
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}

		var cfg ConfigFile
		if err := json.Unmarshal(data, &cfg); err != nil {
			continue
		}

		allTools = append(allTools, cfg.Tools...)
	}

	return allTools
}
