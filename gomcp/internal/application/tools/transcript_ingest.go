package tools

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// claudeRawEntry mirrors the subset of fields we care about in a Claude Code
// JSONL transcript. The format mixes control records ("permission-mode",
// "file-history-snapshot", "attachment", ...) with actual conversation
// records ("user", "assistant"). Control records are skipped at parse time.
type claudeRawEntry struct {
	Type      string             `json:"type"`
	SessionID string             `json:"sessionId,omitempty"`
	Timestamp string             `json:"timestamp,omitempty"`
	UUID      string             `json:"uuid,omitempty"`
	Message   *claudeRawMessage  `json:"message,omitempty"`
}

type claudeRawMessage struct {
	Role    string          `json:"role"`
	Content json.RawMessage `json:"content"` // string OR array of blocks
}

type claudeContentBlock struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

// IngestResult summarises what an IngestTranscript call did.
type IngestResult struct {
	SessionID  string `json:"session_id"`
	Inserted   int    `json:"inserted"`
	Skipped    int    `json:"skipped"`     // control records or empty
	Duplicates int    `json:"duplicates"`  // entries the repo refused (UNIQUE constraint)
}

// IngestTranscript reads a Claude Code JSONL transcript and persists every
// user/assistant message into the conversation_log. Control records and
// empty messages are silently skipped. Idempotent — re-running on the same
// file is a no-op for already-stored (session_id, msg_index) pairs.
//
// sessionOverride: if non-empty, overrides the sessionId embedded in the
// transcript (useful when the file is part of a fork or migration).
func IngestTranscript(ctx context.Context, repo *sqlite.ConversationLogRepo, path, sessionOverride string) (IngestResult, error) {
	f, err := os.Open(path)
	if err != nil {
		return IngestResult{}, fmt.Errorf("open transcript: %w", err)
	}
	defer f.Close()
	return ingestReader(ctx, repo, f, sessionOverride)
}

// ingestReader is the testable seam — IngestTranscript wraps it with file IO.
func ingestReader(ctx context.Context, repo *sqlite.ConversationLogRepo, r io.Reader, sessionOverride string) (IngestResult, error) {
	result := IngestResult{}

	scanner := bufio.NewScanner(r)
	// Claude transcripts can contain very long lines (full assistant outputs).
	// Default Scanner buffer is 64KB; expand to 8MB.
	const maxLine = 8 * 1024 * 1024
	scanner.Buffer(make([]byte, 0, 64*1024), maxLine)

	var entries []sqlite.ConversationEntry
	msgIndex := 0

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var raw claudeRawEntry
		if err := json.Unmarshal(line, &raw); err != nil {
			result.Skipped++
			continue
		}
		// Skip control / system / attachment / tool_result records.
		if raw.Type != "user" && raw.Type != "assistant" {
			result.Skipped++
			continue
		}
		if raw.Message == nil {
			result.Skipped++
			continue
		}

		text := extractText(raw.Message)
		if strings.TrimSpace(text) == "" {
			result.Skipped++
			continue
		}

		sessionID := sessionOverride
		if sessionID == "" {
			sessionID = raw.SessionID
		}
		if sessionID == "" {
			result.Skipped++
			continue
		}
		result.SessionID = sessionID

		ts, _ := time.Parse(time.RFC3339Nano, raw.Timestamp)
		if ts.IsZero() {
			ts, _ = time.Parse(time.RFC3339, raw.Timestamp)
		}

		metadata := ""
		if raw.UUID != "" {
			metadata = fmt.Sprintf(`{"uuid":%q}`, raw.UUID)
		}

		entries = append(entries, sqlite.ConversationEntry{
			SessionID: sessionID,
			Role:      raw.Message.Role,
			Content:   text,
			MsgIndex:  msgIndex,
			Timestamp: ts,
			Metadata:  metadata,
		})
		msgIndex++
	}
	if err := scanner.Err(); err != nil {
		return result, fmt.Errorf("scan transcript: %w", err)
	}

	wantInserted := len(entries)
	inserted, err := repo.RecordBatch(ctx, entries)
	if err != nil {
		return result, err
	}
	result.Inserted = inserted
	result.Duplicates = wantInserted - inserted
	return result, nil
}

// extractText flattens Claude's content payload into a single string.
// User messages typically have content as a plain string; assistant messages
// have an array of blocks with optional text. Non-text blocks (tool_use,
// tool_result) are dropped — their contribution belongs to the tool layer,
// not the conversation layer.
func extractText(msg *claudeRawMessage) string {
	if len(msg.Content) == 0 {
		return ""
	}
	// Try as plain string first.
	var s string
	if err := json.Unmarshal(msg.Content, &s); err == nil {
		return s
	}
	// Fallback: array of blocks.
	var blocks []claudeContentBlock
	if err := json.Unmarshal(msg.Content, &blocks); err == nil {
		var b strings.Builder
		for _, blk := range blocks {
			if blk.Type == "text" && blk.Text != "" {
				if b.Len() > 0 {
					b.WriteString("\n\n")
				}
				b.WriteString(blk.Text)
			}
		}
		return b.String()
	}
	return ""
}
