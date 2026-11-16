package audit

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// PeerBackupPayload is the data sent to trusted peers for log backup.
type PeerBackupPayload struct {
	PeerID    string    `json:"peer_id"`
	Timestamp time.Time `json:"timestamp"`
	LogHash   string    `json:"log_hash"` // SHA-256 of decisions.log
	Entries   int       `json:"entries"`  // Number of decision entries
	Snapshot  string    `json:"snapshot"` // Last N entries for quick restore
}

// PeerBackupResult describes the outcome of a backup attempt.
type PeerBackupResult struct {
	BackedUp bool   `json:"backed_up"`
	FilePath string `json:"file_path,omitempty"`
	Size     int64  `json:"size,omitempty"`
}

// CreateBackupSnapshot creates a local backup snapshot of decisions.log
// that can be sent to trusted peers via P2P transport.
// Saves to .rlm/decisions_backup.json for peer sync.
func CreateBackupSnapshot(rlmDir, peerID string, maxEntries int) (*PeerBackupPayload, error) {
	logPath := filepath.Join(rlmDir, decisionsFileName)
	data, err := os.ReadFile(logPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("backup: no decisions.log to back up")
		}
		return nil, fmt.Errorf("backup: read: %w", err)
	}

	lines := splitLines(string(data))
	// Filter empty lines.
	var entries []string
	for _, l := range lines {
		if l != "" {
			entries = append(entries, l)
		}
	}

	// Take last N entries for snapshot.
	if maxEntries <= 0 {
		maxEntries = 100
	}
	snapshot := entries
	if len(entries) > maxEntries {
		snapshot = entries[len(entries)-maxEntries:]
	}

	snapshotJSON, _ := json.Marshal(snapshot)

	payload := &PeerBackupPayload{
		PeerID:    peerID,
		Timestamp: time.Now(),
		Entries:   len(entries),
		Snapshot:  string(snapshotJSON),
	}

	// Save backup file locally.
	backupPath := filepath.Join(rlmDir, "decisions_backup.json")
	backupData, _ := json.MarshalIndent(payload, "", "  ")
	if err := os.WriteFile(backupPath, backupData, 0o644); err != nil {
		return nil, fmt.Errorf("backup: write: %w", err)
	}

	return payload, nil
}

// RestoreFromBackup loads a backup snapshot (received from a peer).
func RestoreFromBackup(rlmDir string) (*PeerBackupPayload, error) {
	backupPath := filepath.Join(rlmDir, "decisions_backup.json")
	data, err := os.ReadFile(backupPath)
	if err != nil {
		return nil, fmt.Errorf("restore: %w", err)
	}
	var payload PeerBackupPayload
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil, fmt.Errorf("restore: parse: %w", err)
	}
	return &payload, nil
}
