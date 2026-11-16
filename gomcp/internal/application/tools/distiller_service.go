package tools

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

// DistillerService collapses raw conversation messages from the L4
// conversation_log into denser L2/L3 hierarchical_facts. This is the
// Crystal-Principle lossy reduction: many low-density transient messages
// → one summary fact + a handful of notable user-question facts.
//
// Heuristic, no LLM: a session's summary is built from message counts,
// start/end timestamps, and previews of the first user message and last
// assistant message. Long-enough user messages become separate L3 facts
// hung off the summary as their parent. Distillation is fast, deterministic,
// and lossy by design — raw messages remain in conversation_log until
// pruned, so detail recovery is always possible.
type DistillerService struct {
	conversations conversationDistillStore
	facts         memory.FactStore
	embedder      vectorstore.Embedder // optional — if set, distilled facts get embeddings
}

type conversationDistillStore interface {
	GetSession(context.Context, string) ([]sqlite.ConversationEntry, error)
	GetUndistilled(context.Context, int) ([]sqlite.ConversationEntry, error)
	MarkDistilled(context.Context, []int64) error
}

// NewDistillerService wires the pipeline.
func NewDistillerService(conv *sqlite.ConversationLogRepo, facts memory.FactStore) *DistillerService {
	return &DistillerService{conversations: conv, facts: facts}
}

// SetEmbedder enables embedding generation for distilled facts.
// Without an embedder, distillation still works — facts just won't carry
// vectors and will be invisible to semantic search and centroid rollup.
func (s *DistillerService) SetEmbedder(e vectorstore.Embedder) {
	s.embedder = e
}

// DistillResult summarises one DistillSession or DistillBatch call.
type DistillResult struct {
	SessionsProcessed  int      `json:"sessions_processed"`
	SummaryFactsAdded  int      `json:"summary_facts_added"`
	QuestionFactsAdded int      `json:"question_facts_added"`
	MessagesMarked     int      `json:"messages_marked_distilled"`
	Sessions           []string `json:"sessions,omitempty"`
}

// QuestionMinChars is the cutoff above which a user message graduates from
// "trivial chat" to "worth its own L3 fact". Tunable, conservative default.
const QuestionMinChars = 200

// DistillSession produces hierarchical facts from one session's raw
// messages and marks every contributing message distilled. Idempotent —
// already-distilled messages are skipped. Returns DistillResult counts.
func (s *DistillerService) DistillSession(ctx context.Context, sessionID string) (DistillResult, error) {
	res := DistillResult{}
	if _, err := rlmscope.RequireSessionScope(ctx, sessionID); err != nil {
		return res, err
	}
	sessionFacts, ok := s.facts.(memory.SessionFactStore)
	if !ok {
		return res, fmt.Errorf("session memory is unavailable: fact store does not support exact session isolation")
	}

	all, err := s.conversations.GetSession(ctx, sessionID)
	if err != nil {
		return res, fmt.Errorf("get session: %w", err)
	}

	// Filter out already-distilled.
	live := make([]sqlite.ConversationEntry, 0, len(all))
	for _, e := range all {
		if !e.Distilled {
			live = append(live, e)
		}
	}
	if len(live) == 0 {
		return res, nil
	}

	summary, summaryFact, err := s.buildSummaryFact(ctx, sessionID, live)
	if err != nil {
		return res, err
	}
	if summary == "" {
		// Trivial session (e.g. one empty message); mark distilled and move on.
		ids := make([]int64, 0, len(live))
		for _, e := range live {
			ids = append(ids, e.ID)
		}
		if err := s.conversations.MarkDistilled(ctx, ids); err != nil {
			return res, fmt.Errorf("mark trivial session distilled: %w", err)
		}
		res.MessagesMarked = len(ids)
		return res, nil
	}
	if err := sessionFacts.AddForSession(ctx, sessionID, summaryFact); err != nil {
		return res, fmt.Errorf("add summary fact: %w", err)
	}
	res.SummaryFactsAdded = 1

	// Promote notable user questions to standalone L3 facts.
	for _, e := range live {
		if e.Role != "user" {
			continue
		}
		trimmed := strings.TrimSpace(e.Content)
		if len([]rune(trimmed)) < QuestionMinChars {
			continue
		}
		qf := memory.NewFact(trimmed, memory.LevelModule, "conversation", "user-question")
		qf.Source = "auto:distill"
		// External, not user, even though this is lifted from a user message.
		//
		// The distiller reads `conversation_log` indiscriminately, and a conversation carries
		// tool output and document text alongside what the person typed. It cannot tell which
		// is which, so the honest classification is the conservative one — and the consequence
		// is correct on its own terms: a distilled session summary should never become a
		// standing instruction. Origin governs instruction authority, NOT visibility: these
		// facts are still injected as information.
		qf.Origin = memory.OriginExternal
		qf.ParentID = summaryFact.ID
		if s.embedder != nil {
			if vec, embErr := s.embedder.Embed(ctx, trimmed); embErr == nil {
				qf.Embedding = vec
			}
		}
		if err := sessionFacts.AddForSession(ctx, sessionID, qf); err != nil {
			return res, fmt.Errorf("add question fact: %w", err)
		}
		res.QuestionFactsAdded++
	}

	// Mark every contributing message distilled.
	ids := make([]int64, 0, len(live))
	for _, e := range live {
		ids = append(ids, e.ID)
	}
	if err := s.conversations.MarkDistilled(ctx, ids); err != nil {
		return res, fmt.Errorf("mark distilled: %w", err)
	}
	res.MessagesMarked = len(ids)
	res.SessionsProcessed = 1
	res.Sessions = []string{sessionID}
	return res, nil
}

// DistillBatch finds undistilled messages, groups them by session, and
// distills every session whose latest message is older than idle. This
// avoids distilling a still-live session prematurely. Limit caps the
// number of sessions processed in one call.
func (s *DistillerService) DistillBatch(ctx context.Context, idle time.Duration, limit int) (DistillResult, error) {
	res := DistillResult{}
	if _, err := rlmscope.RequireSessionProject(ctx); err != nil {
		return res, fmt.Errorf("distill batch: %w", err)
	}
	if limit <= 0 {
		limit = 50
	}

	// Pull a generous slice of undistilled messages — enough to cover
	// several sessions even if some are large.
	und, err := s.conversations.GetUndistilled(ctx, limit*200)
	if err != nil {
		return res, fmt.Errorf("get undistilled: %w", err)
	}
	if len(und) == 0 {
		return res, nil
	}

	// Group by session, track latest timestamp per session.
	type bucket struct {
		latest time.Time
	}
	buckets := map[string]*bucket{}
	for _, e := range und {
		b, ok := buckets[e.SessionID]
		if !ok {
			b = &bucket{latest: e.Timestamp}
			buckets[e.SessionID] = b
		}
		if e.Timestamp.After(b.latest) {
			b.latest = e.Timestamp
		}
	}

	now := time.Now().UTC()
	cutoff := now.Add(-idle)
	ready := make([]string, 0, len(buckets))
	for sid, b := range buckets {
		if !b.latest.After(cutoff) {
			ready = append(ready, sid)
		}
	}
	sort.Strings(ready) // deterministic order
	if len(ready) > limit {
		ready = ready[:limit]
	}

	for _, sid := range ready {
		r, err := s.DistillSession(ctx, sid)
		if err != nil {
			return res, fmt.Errorf("distill session %s: %w", sid, err)
		}
		res.SessionsProcessed += r.SessionsProcessed
		res.SummaryFactsAdded += r.SummaryFactsAdded
		res.QuestionFactsAdded += r.QuestionFactsAdded
		res.MessagesMarked += r.MessagesMarked
		res.Sessions = append(res.Sessions, r.Sessions...)
	}
	return res, nil
}

// buildSummaryFact constructs the per-session L2 summary fact. The summary
// string is also returned so the caller can detect "trivial session" cases
// (empty string).
func (s *DistillerService) buildSummaryFact(ctx context.Context, sessionID string, msgs []sqlite.ConversationEntry) (string, *memory.Fact, error) {
	if len(msgs) == 0 {
		return "", nil, nil
	}

	var firstUser, lastAssistant string
	userCount, assistantCount := 0, 0
	for _, m := range msgs {
		switch m.Role {
		case "user":
			userCount++
			if firstUser == "" {
				firstUser = trimPreview(m.Content, 200)
			}
		case "assistant":
			assistantCount++
			lastAssistant = trimPreview(m.Content, 200)
		}
	}

	if userCount == 0 && assistantCount == 0 {
		return "", nil, nil
	}

	start := msgs[0].Timestamp
	end := msgs[len(msgs)-1].Timestamp

	var b strings.Builder
	fmt.Fprintf(&b, "Session %s (%s – %s, %d messages: %d user / %d assistant)",
		shortID(sessionID),
		start.Format("2006-01-02 15:04Z"),
		end.Format("2006-01-02 15:04Z"),
		len(msgs), userCount, assistantCount)
	if firstUser != "" {
		fmt.Fprintf(&b, "\nFirst question: %s", firstUser)
	}
	if lastAssistant != "" {
		fmt.Fprintf(&b, "\nLast response: %s", lastAssistant)
	}
	summary := b.String()

	module := "session-" + shortID(sessionID)
	f := memory.NewFact(summary, memory.LevelModule, "conversation", module)
	f.Source = "auto:distill"
	// See the note on the question fact above: summarised conversation is external.
	f.Origin = memory.OriginExternal
	f.SessionID = sessionID
	if s.embedder != nil {
		if vec, embErr := s.embedder.Embed(ctx, summary); embErr == nil {
			f.Embedding = vec
		}
	}
	return summary, f, nil
}

// trimPreview returns at most n runes of s, with single-line whitespace.
func trimPreview(s string, n int) string {
	s = strings.Join(strings.Fields(strings.TrimSpace(s)), " ")
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "…"
}

// shortID returns the first 8 characters of an ID, or the full string if
// shorter. Used to keep human-readable summaries compact.
func shortID(id string) string {
	if len(id) <= 8 {
		return id
	}
	return id[:8]
}
