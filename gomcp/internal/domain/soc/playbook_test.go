package soc

import (
	"testing"
)

func TestPlaybookEngine_DefaultPlaybooks(t *testing.T) {
	pe := NewPlaybookEngine()
	pbs := pe.ListPlaybooks()
	if len(pbs) != 4 {
		t.Fatalf("expected 4 default playbooks, got %d", len(pbs))
	}
}

func TestPlaybookEngine_ExecuteJailbreak(t *testing.T) {
	pe := NewPlaybookEngine()
	execs := pe.Execute("inc-001", "CRITICAL", "jailbreak", "")
	if len(execs) == 0 {
		t.Fatal("should match jailbreak playbook")
	}
	found := false
	for _, e := range execs {
		if e.PlaybookID == "pb-block-jailbreak" {
			found = true
			if e.Status != "success" {
				t.Fatal("execution should be success")
			}
			if e.ActionsRun != 3 {
				t.Fatalf("jailbreak playbook has 3 actions, got %d", e.ActionsRun)
			}
		}
	}
	if !found {
		t.Fatal("pb-block-jailbreak should have matched")
	}
}

func TestPlaybookEngine_NoMatchLowSeverity(t *testing.T) {
	pe := NewPlaybookEngine()
	// LOW severity jailbreak should not match CRITICAL-threshold playbook
	execs := pe.Execute("inc-002", "LOW", "jailbreak", "")
	for _, e := range execs {
		if e.PlaybookID == "pb-block-jailbreak" {
			t.Fatal("LOW severity should not match CRITICAL trigger")
		}
	}
}

func TestPlaybookEngine_KillChainMatch(t *testing.T) {
	pe := NewPlaybookEngine()
	execs := pe.Execute("inc-003", "CRITICAL", "c2", "command_control")
	found := false
	for _, e := range execs {
		if e.PlaybookID == "pb-c2-killchain" {
			found = true
			if e.ActionsRun != 4 {
				t.Fatalf("C2 playbook has 4 actions, got %d", e.ActionsRun)
			}
		}
	}
	if !found {
		t.Fatal("kill chain playbook should match command_control phase")
	}
}

func TestPlaybookEngine_DisabledPlaybook(t *testing.T) {
	pe := NewPlaybookEngine()
	pe.RemovePlaybook("pb-block-jailbreak")

	execs := pe.Execute("inc-004", "CRITICAL", "jailbreak", "")
	for _, e := range execs {
		if e.PlaybookID == "pb-block-jailbreak" {
			t.Fatal("disabled playbook should not execute")
		}
	}
}

func TestPlaybookEngine_AddCustom(t *testing.T) {
	pe := NewPlaybookEngine()
	pe.AddPlaybook(Playbook{
		ID:   "pb-custom",
		Name: "Custom",
		Trigger: PlaybookTrigger{
			Categories: []string{"custom-cat"},
		},
		Actions: []PlaybookAction{
			{Type: "log", Params: map[string]string{"msg": "custom"}, Order: 1},
		},
		Enabled: true,
	})

	pbs := pe.ListPlaybooks()
	if len(pbs) != 5 {
		t.Fatalf("expected 5 playbooks, got %d", len(pbs))
	}

	execs := pe.Execute("inc-005", "HIGH", "custom-cat", "")
	found := false
	for _, e := range execs {
		if e.PlaybookID == "pb-custom" {
			found = true
		}
	}
	if !found {
		t.Fatal("custom playbook should match")
	}
}

func TestPlaybookEngine_ExecutionLog(t *testing.T) {
	pe := NewPlaybookEngine()
	pe.Execute("inc-001", "CRITICAL", "jailbreak", "")
	pe.Execute("inc-002", "HIGH", "exfiltration", "")

	log := pe.ExecutionLog(10)
	if len(log) < 2 {
		t.Fatalf("expected at least 2 executions, got %d", len(log))
	}
}

func TestPlaybookEngine_Stats(t *testing.T) {
	pe := NewPlaybookEngine()
	stats := pe.PlaybookStats()
	if stats["total_playbooks"].(int) != 4 {
		t.Fatal("should have 4 playbooks")
	}
	if stats["enabled"].(int) != 4 {
		t.Fatal("all 4 should be enabled")
	}
}
