package hooks

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// Installer configures hook files for IDE agents.
type Installer struct {
	homeDir string
}

// NewInstaller creates an installer for the current user's home directory.
func NewInstaller() (*Installer, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, fmt.Errorf("cannot determine home directory: %w", err)
	}
	return &Installer{homeDir: home}, nil
}

// NewInstallerWithHome creates an installer with a custom home directory (for testing).
func NewInstallerWithHome(homeDir string) *Installer {
	return &Installer{homeDir: homeDir}
}

// DetectedIDEs returns a list of IDE agents that appear to be installed.
func (inst *Installer) DetectedIDEs() []IDE {
	var detected []IDE
	if inst.isClaudeInstalled() {
		detected = append(detected, IDEClaude)
	}
	if inst.isGeminiInstalled() {
		detected = append(detected, IDEGemini)
	}
	if inst.isCursorInstalled() {
		detected = append(detected, IDECursor)
	}
	return detected
}

func (inst *Installer) isClaudeInstalled() bool {
	return dirExists(filepath.Join(inst.homeDir, ".claude"))
}

func (inst *Installer) isGeminiInstalled() bool {
	return dirExists(filepath.Join(inst.homeDir, ".gemini"))
}

func (inst *Installer) isCursorInstalled() bool {
	return dirExists(filepath.Join(inst.homeDir, ".cursor"))
}

func dirExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

// InstallResult reports the outcome of a single IDE hook installation.
type InstallResult struct {
	IDE     IDE    `json:"ide"`
	Path    string `json:"path"`
	Created bool   `json:"created"`
	Error   string `json:"error,omitempty"`
}

// Install configures hooks for the specified IDE.
// If the IDE's hooks file already exists, it merges Syntrex hooks without overwriting.
func (inst *Installer) Install(ide IDE) InstallResult {
	switch ide {
	case IDEClaude:
		return inst.installClaude()
	case IDEGemini:
		return inst.installGemini()
	case IDECursor:
		return inst.installCursor()
	default:
		return InstallResult{IDE: ide, Error: fmt.Sprintf("unsupported IDE: %s", ide)}
	}
}

// InstallAll configures hooks for all detected IDEs.
func (inst *Installer) InstallAll() []InstallResult {
	detected := inst.DetectedIDEs()
	results := make([]InstallResult, 0, len(detected))
	for _, ide := range detected {
		results = append(results, inst.Install(ide))
	}
	return results
}

func (inst *Installer) installClaude() InstallResult {
	hookPath := filepath.Join(inst.homeDir, ".claude", "hooks.json")
	binary := syntrexHookBinary()

	config := map[string]interface{}{
		"hooks": map[string]interface{}{
			"PreToolUse": []map[string]interface{}{
				{
					"type":     "command",
					"command":  fmt.Sprintf("%s scan --ide claude --event pre_tool_use", binary),
					"timeout":  5000,
					"matchers": []string{"*"},
				},
			},
			"PostToolUse": []map[string]interface{}{
				{
					"type":     "command",
					"command":  fmt.Sprintf("%s scan --ide claude --event post_tool_use", binary),
					"timeout":  5000,
					"matchers": []string{"*"},
				},
			},
		},
	}

	return inst.writeHookConfig(IDEClaude, hookPath, config)
}

func (inst *Installer) installGemini() InstallResult {
	hookPath := filepath.Join(inst.homeDir, ".gemini", "hooks.json")
	binary := syntrexHookBinary()

	config := map[string]interface{}{
		"hooks": map[string]interface{}{
			"BeforeToolSelection": map[string]interface{}{
				"command": fmt.Sprintf("%s scan --ide gemini --event before_tool_selection", binary),
			},
		},
	}

	return inst.writeHookConfig(IDEGemini, hookPath, config)
}

func (inst *Installer) installCursor() InstallResult {
	hookPath := filepath.Join(inst.homeDir, ".cursor", "hooks.json")
	binary := syntrexHookBinary()

	config := map[string]interface{}{
		"hooks": map[string]interface{}{
			"Command": map[string]interface{}{
				"command": fmt.Sprintf("%s scan --ide cursor --event command", binary),
			},
		},
	}

	return inst.writeHookConfig(IDECursor, hookPath, config)
}

func (inst *Installer) writeHookConfig(ide IDE, path string, config map[string]interface{}) InstallResult {
	// Don't overwrite existing hook configs
	if _, err := os.Stat(path); err == nil {
		return InstallResult{
			IDE:     ide,
			Path:    path,
			Created: false,
			Error:   "hooks file already exists — manual merge required",
		}
	}

	// Ensure directory exists
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return InstallResult{IDE: ide, Path: path, Error: err.Error()}
	}

	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return InstallResult{IDE: ide, Path: path, Error: err.Error()}
	}

	if err := os.WriteFile(path, data, 0600); err != nil {
		return InstallResult{IDE: ide, Path: path, Error: err.Error()}
	}

	return InstallResult{IDE: ide, Path: path, Created: true}
}

func syntrexHookBinary() string {
	if runtime.GOOS == "windows" {
		return "syntrex-hook.exe"
	}
	return "syntrex-hook"
}
