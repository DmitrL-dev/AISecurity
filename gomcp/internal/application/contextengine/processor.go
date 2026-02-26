// Package contextengine — processor.go
// Processes unprocessed interaction log entries into session summary facts.
// This closes the memory loop: tool calls → interaction log → summary facts → boot instructions.
package contextengine

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/sentinel-community/gomcp/internal/domain/memory"
	"github.com/sentinel-community/gomcp/internal/infrastructure/sqlite"
)

// InteractionProcessor processes unprocessed interaction log entries
// and creates session summary facts from them.
type InteractionProcessor struct {
	repo      *sqlite.InteractionLogRepo
	factStore memory.FactStore
}

// NewInteractionProcessor creates a new processor.
func NewInteractionProcessor(repo *sqlite.InteractionLogRepo, store memory.FactStore) *InteractionProcessor {
	return &InteractionProcessor{repo: repo, factStore: store}
}

// ProcessStartup processes unprocessed entries from a previous (possibly crashed) session.
// It creates an L1 "session summary" fact and marks all entries as processed.
// Returns the summary text (empty if nothing to process).
func (p *InteractionProcessor) ProcessStartup(ctx context.Context) (string, error) {
	entries, err := p.repo.GetUnprocessed(ctx)
	if err != nil {
		return "", fmt.Errorf("get unprocessed: %w", err)
	}
	if len(entries) == 0 {
		return "", nil
	}

	summary := buildSessionSummary(entries, "previous session (recovered)")
	if summary == "" {
		return "", nil
	}

	// Save as L1 fact (domain-level, not project-level)
	fact := memory.NewFact(summary, memory.LevelDomain, "session-history", "interaction-processor")
	fact.Source = "auto:interaction-processor"
	if err := p.factStore.Add(ctx, fact); err != nil {
		return "", fmt.Errorf("save session summary fact: %w", err)
	}

	// Mark all as processed
	ids := make([]int64, len(entries))
	for i, e := range entries {
		ids[i] = e.ID
	}
	if err := p.repo.MarkProcessed(ctx, ids); err != nil {
		return "", fmt.Errorf("mark processed: %w", err)
	}

	return summary, nil
}

// ProcessShutdown processes entries from the current session at graceful shutdown.
// Similar to ProcessStartup but labels differently.
func (p *InteractionProcessor) ProcessShutdown(ctx context.Context) (string, error) {
	entries, err := p.repo.GetUnprocessed(ctx)
	if err != nil {
		return "", fmt.Errorf("get unprocessed: %w", err)
	}
	if len(entries) == 0 {
		return "", nil
	}

	summary := buildSessionSummary(entries, "session ending "+time.Now().Format("2006-01-02 15:04"))
	if summary == "" {
		return "", nil
	}

	fact := memory.NewFact(summary, memory.LevelDomain, "session-history", "interaction-processor")
	fact.Source = "auto:session-shutdown"
	if err := p.factStore.Add(ctx, fact); err != nil {
		return "", fmt.Errorf("save session summary fact: %w", err)
	}

	ids := make([]int64, len(entries))
	for i, e := range entries {
		ids[i] = e.ID
	}
	if err := p.repo.MarkProcessed(ctx, ids); err != nil {
		return "", fmt.Errorf("mark processed: %w", err)
	}

	return summary, nil
}

// buildSessionSummary creates a compact text summary from interaction log entries.
func buildSessionSummary(entries []sqlite.InteractionEntry, label string) string {
	if len(entries) == 0 {
		return ""
	}

	// Count tool calls
	toolCounts := make(map[string]int)
	for _, e := range entries {
		toolCounts[e.ToolName]++
	}

	// Sort by count descending
	type toolStat struct {
		name  string
		count int
	}
	stats := make([]toolStat, 0, len(toolCounts))
	for name, count := range toolCounts {
		stats = append(stats, toolStat{name, count})
	}
	sort.Slice(stats, func(i, j int) bool { return stats[i].count > stats[j].count })

	// Extract topics from args (unique string values)
	topics := extractTopicsFromEntries(entries)

	// Time range
	var earliest, latest time.Time
	for _, e := range entries {
		if earliest.IsZero() || e.Timestamp.Before(earliest) {
			earliest = e.Timestamp
		}
		if latest.IsZero() || e.Timestamp.After(latest) {
			latest = e.Timestamp
		}
	}

	var b strings.Builder
	b.WriteString(fmt.Sprintf("Session summary (%s): %d tool calls", label, len(entries)))
	if !earliest.IsZero() {
		duration := latest.Sub(earliest)
		if duration > 0 {
			b.WriteString(fmt.Sprintf(" over %s", formatDuration(duration)))
		}
	}
	b.WriteString(". ")

	// Top tools used
	b.WriteString("Tools used: ")
	for i, ts := range stats {
		if i >= 8 {
			b.WriteString(fmt.Sprintf(" +%d more", len(stats)-8))
			break
		}
		if i > 0 {
			b.WriteString(", ")
		}
		b.WriteString(fmt.Sprintf("%s(%d)", ts.name, ts.count))
	}
	b.WriteString(". ")

	// Topics
	if len(topics) > 0 {
		b.WriteString("Topics: ")
		limit := 10
		if len(topics) < limit {
			limit = len(topics)
		}
		b.WriteString(strings.Join(topics[:limit], ", "))
		if len(topics) > limit {
			b.WriteString(fmt.Sprintf(" +%d more", len(topics)-limit))
		}
		b.WriteString(".")
	}

	return b.String()
}

// extractTopicsFromEntries pulls unique meaningful strings from tool arguments.
func extractTopicsFromEntries(entries []sqlite.InteractionEntry) []string {
	seen := make(map[string]bool)
	var topics []string

	for _, e := range entries {
		if e.ArgsJSON == "" {
			continue
		}
		// Simple extraction: find quoted strings in JSON args
		// ArgsJSON looks like {"query":"architecture","content":"some fact"}
		parts := strings.Split(e.ArgsJSON, "\"")
		for i := 3; i < len(parts); i += 4 {
			// Values are at odd positions after the key
			val := parts[i]
			if len(val) < 3 || len(val) > 100 {
				continue
			}
			// Skip common non-topic values
			lower := strings.ToLower(val)
			if lower == "true" || lower == "false" || lower == "null" || lower == "" {
				continue
			}
			if !seen[lower] {
				seen[lower] = true
				topics = append(topics, val)
			}
		}
	}

	return topics
}

// formatDuration formats a duration into a human-readable string.
func formatDuration(d time.Duration) string {
	if d < time.Minute {
		return fmt.Sprintf("%ds", int(d.Seconds()))
	}
	if d < time.Hour {
		return fmt.Sprintf("%dm", int(d.Minutes()))
	}
	return fmt.Sprintf("%dh%dm", int(d.Hours()), int(d.Minutes())%60)
}

// GetLastSessionSummary searches the fact store for the most recent session summary.
func GetLastSessionSummary(ctx context.Context, store memory.FactStore) string {
	facts, err := store.Search(ctx, "Session summary", 5)
	if err != nil || len(facts) == 0 {
		return ""
	}

	// Find the most recent one from session-history domain
	var best *memory.Fact
	for _, f := range facts {
		if f.Domain != "session-history" {
			continue
		}
		if f.IsStale || f.IsArchived {
			continue
		}
		if best == nil || f.CreatedAt.After(best.CreatedAt) {
			best = f
		}
	}

	if best == nil {
		return ""
	}
	return best.Content
}
