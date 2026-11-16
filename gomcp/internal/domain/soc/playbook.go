package soc

import (
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// PlaybookEngine implements §10 — automated incident response.
// Executes predefined response actions when incidents match playbook triggers.
type PlaybookEngine struct {
	mu        sync.RWMutex
	playbooks map[string]*Playbook
	execLog   []PlaybookExecution
	maxLog    int
	handler   ActionHandler
}

// ActionContext carries the incident context a playbook action needs to act on.
// IMP6: the previous handler signature passed only the incident ID, so real
// executors (notify/webhook/escalate) received an EMPTY severity/category and
// emitted blank alerts. Threading this struct from Execute closes that gap — the
// notification payloads now carry the real severity, category, rule, and counts.
type ActionContext struct {
	IncidentID     string
	Severity       string
	Category       string
	KillChainPhase string
	Description    string
	RuleName       string
	EventCount     int
}

// ActionHandler executes playbook actions. Implement for real integrations.
type ActionHandler interface {
	Handle(action PlaybookAction, ctx ActionContext) error
}

// LogHandler is the default action handler — logs what would be executed.
type LogHandler struct{}

func (h LogHandler) Handle(action PlaybookAction, ctx ActionContext) error {
	slog.Info("playbook action", "action", action.Type, "incident", ctx.IncidentID,
		"severity", ctx.Severity, "category", ctx.Category, "params", action.Params)
	return nil
}

// Playbook defines an automated response procedure.
type Playbook struct {
	ID          string           `json:"id"`
	Name        string           `json:"name"`
	Description string           `json:"description"`
	Trigger     PlaybookTrigger  `json:"trigger"`
	Actions     []PlaybookAction `json:"actions"`
	Enabled     bool             `json:"enabled"`
	Priority    int              `json:"priority"`
	CreatedAt   time.Time        `json:"created_at"`
}

// PlaybookTrigger defines when a playbook activates.
type PlaybookTrigger struct {
	Severity       string   `json:"severity,omitempty"`
	Categories     []string `json:"categories,omitempty"`
	Keywords       []string `json:"keywords,omitempty"`
	KillChainPhase string   `json:"kill_chain_phase,omitempty"`
}

// PlaybookAction is a single response step.
type PlaybookAction struct {
	Type   string            `json:"type"`
	Params map[string]string `json:"params"`
	Order  int               `json:"order"`
}

// PlaybookExecution records a playbook run.
type PlaybookExecution struct {
	ID         string    `json:"id"`
	PlaybookID string    `json:"playbook_id"`
	IncidentID string    `json:"incident_id"`
	Status     string    `json:"status"`
	ActionsRun int       `json:"actions_run"`
	Duration   string    `json:"duration"`
	Error      string    `json:"error,omitempty"`
	Timestamp  time.Time `json:"timestamp"`
}

// NewPlaybookEngine creates the automated response engine with built-in playbooks.
func NewPlaybookEngine() *PlaybookEngine {
	pe := &PlaybookEngine{
		playbooks: make(map[string]*Playbook),
		maxLog:    200,
		handler:   LogHandler{},
	}
	pe.loadDefaults()
	return pe
}

// SetHandler replaces the action handler (for real integrations: webhook, SOAR, etc.).
func (pe *PlaybookEngine) SetHandler(h ActionHandler) {
	pe.mu.Lock()
	defer pe.mu.Unlock()
	pe.handler = h
}

func (pe *PlaybookEngine) loadDefaults() {
	defaults := []Playbook{
		{
			ID: "pb-block-jailbreak", Name: "Auto-Block Jailbreak Source",
			Description: "Blocks source IP on confirmed jailbreak attempts",
			Trigger:     PlaybookTrigger{Severity: "CRITICAL", Categories: []string{"jailbreak"}},
			Actions: []PlaybookAction{
				{Type: "log", Params: map[string]string{"message": "Jailbreak detected"}, Order: 1},
				{Type: "block_ip", Params: map[string]string{"duration": "3600"}, Order: 2},
				{Type: "notify", Params: map[string]string{"channel": "soc-alerts"}, Order: 3},
			},
			Enabled: true, Priority: 1,
		},
		{
			ID: "pb-quarantine-exfil", Name: "Quarantine Data Exfiltration",
			Description: "Isolates sessions on data exfiltration detection",
			Trigger:     PlaybookTrigger{Severity: "HIGH", Categories: []string{"exfiltration"}},
			Actions: []PlaybookAction{
				{Type: "quarantine", Params: map[string]string{"scope": "session"}, Order: 1},
				{Type: "escalate", Params: map[string]string{"team": "ir-team"}, Order: 2},
			},
			Enabled: true, Priority: 2,
		},
		{
			ID: "pb-notify-injection", Name: "Alert on Prompt Injection",
			Description: "Sends notification on prompt injection detection",
			Trigger:     PlaybookTrigger{Severity: "MEDIUM", Categories: []string{"injection"}},
			Actions: []PlaybookAction{
				{Type: "log", Params: map[string]string{"message": "Prompt injection detected"}, Order: 1},
				{Type: "notify", Params: map[string]string{"channel": "soc-alerts"}, Order: 2},
			},
			Enabled: true, Priority: 3,
		},
		{
			ID: "pb-c2-killchain", Name: "Kill Chain C2 Response",
			Description: "Immediate response to C2 communication detection",
			Trigger:     PlaybookTrigger{KillChainPhase: "command_control"},
			Actions: []PlaybookAction{
				{Type: "block_ip", Params: map[string]string{"duration": "86400"}, Order: 1},
				{Type: "quarantine", Params: map[string]string{"scope": "host"}, Order: 2},
				{Type: "webhook", Params: map[string]string{"event": "kill_chain_alert"}, Order: 3},
				{Type: "escalate", Params: map[string]string{"team": "threat-hunters"}, Order: 4},
			},
			Enabled: true, Priority: 1,
		},
	}
	for i := range defaults {
		defaults[i].CreatedAt = time.Now()
		pe.playbooks[defaults[i].ID] = &defaults[i]
	}
}

// AddPlaybook registers a custom playbook.
func (pe *PlaybookEngine) AddPlaybook(pb Playbook) {
	pe.mu.Lock()
	defer pe.mu.Unlock()
	if pb.ID == "" {
		pb.ID = fmt.Sprintf("pb-%d", time.Now().UnixNano())
	}
	pb.CreatedAt = time.Now()
	pe.playbooks[pb.ID] = &pb
}

// RemovePlaybook deactivates a playbook.
func (pe *PlaybookEngine) RemovePlaybook(id string) {
	pe.mu.Lock()
	defer pe.mu.Unlock()
	if pb, ok := pe.playbooks[id]; ok {
		pb.Enabled = false
	}
}

// Execute runs matching playbooks for an incident, identified by the severity,
// category, and kill-chain phase. Retained for callers/tests that hold only these
// fields; ExecuteForIncident threads the full incident context (description, rule,
// event count) into the action handler for richer notifications.
func (pe *PlaybookEngine) Execute(incidentID, severity, category, killChainPhase string) []PlaybookExecution {
	return pe.execute(ActionContext{
		IncidentID:     incidentID,
		Severity:       severity,
		Category:       category,
		KillChainPhase: killChainPhase,
	})
}

// ExecuteForIncident runs matching playbooks with the FULL incident context so
// notify/webhook/escalate actions carry the real severity, category, rule name,
// description, and event count (IMP6). category is the triggering event category
// (the incident object has no single category field). The incident's own
// KillChainPhase selects kill-chain playbooks.
func (pe *PlaybookEngine) ExecuteForIncident(inc *Incident, category string) []PlaybookExecution {
	if inc == nil {
		return nil
	}
	return pe.execute(ActionContext{
		IncidentID:     inc.ID,
		Severity:       string(inc.Severity),
		Category:       category,
		KillChainPhase: inc.KillChainPhase,
		Description:    inc.Description,
		RuleName:       inc.CorrelationRule,
		EventCount:     inc.EventCount,
	})
}

// execute is the shared matching + dispatch core for Execute/ExecuteForIncident.
func (pe *PlaybookEngine) execute(ctx ActionContext) []PlaybookExecution {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	var results []PlaybookExecution
	for _, pb := range pe.playbooks {
		if !pb.Enabled || !pe.matches(pb, ctx.Severity, ctx.Category, ctx.KillChainPhase) {
			continue
		}
		start := time.Now()
		exec := PlaybookExecution{
			ID:         genID("exec"),
			PlaybookID: pb.ID,
			IncidentID: ctx.IncidentID,
			Status:     "success",
			ActionsRun: len(pb.Actions),
			Timestamp:  start,
		}
		for _, action := range pb.Actions {
			if err := pe.handler.Handle(action, ctx); err != nil {
				exec.Status = "partial_failure"
				exec.Error = err.Error()
				break
			}
		}
		exec.Duration = time.Since(start).String()
		if len(pe.execLog) >= pe.maxLog {
			copy(pe.execLog, pe.execLog[1:])
			pe.execLog[len(pe.execLog)-1] = exec
		} else {
			pe.execLog = append(pe.execLog, exec)
		}
		results = append(results, exec)
	}
	return results
}

func (pe *PlaybookEngine) matches(pb *Playbook, severity, category, killChainPhase string) bool {
	t := pb.Trigger
	if t.Severity != "" && severityRank(severity) < severityRank(t.Severity) {
		return false
	}
	if len(t.Categories) > 0 {
		found := false
		for _, c := range t.Categories {
			if c == category {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	if t.KillChainPhase != "" && t.KillChainPhase != killChainPhase {
		return false
	}
	return true
}

func severityRank(s string) int {
	switch s {
	case "CRITICAL":
		return 4
	case "HIGH":
		return 3
	case "MEDIUM":
		return 2
	case "LOW":
		return 1
	default:
		return 0
	}
}

// ListPlaybooks returns all playbooks.
func (pe *PlaybookEngine) ListPlaybooks() []Playbook {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	result := make([]Playbook, 0, len(pe.playbooks))
	for _, pb := range pe.playbooks {
		result = append(result, *pb)
	}
	return result
}

// ExecutionLog returns recent playbook executions.
func (pe *PlaybookEngine) ExecutionLog(limit int) []PlaybookExecution {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	if limit <= 0 || limit > len(pe.execLog) {
		limit = len(pe.execLog)
	}
	start := len(pe.execLog) - limit
	result := make([]PlaybookExecution, limit)
	copy(result, pe.execLog[start:])
	return result
}

// PlaybookStats returns engine statistics.
func (pe *PlaybookEngine) PlaybookStats() map[string]any {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	enabled := 0
	for _, pb := range pe.playbooks {
		if pb.Enabled {
			enabled++
		}
	}
	return map[string]any{
		"total_playbooks":  len(pe.playbooks),
		"enabled":          enabled,
		"total_executions": len(pe.execLog),
	}
}
