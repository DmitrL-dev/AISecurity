package tools

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// ProjectPulse generates auto-documentation from L0/L1 facts (v3.7 Cerebro).
// Extracts facts from memory, groups by domain, and produces a structured
// markdown report reflecting the current state of the project.
type ProjectPulse struct {
	facts *FactService
}

// NewProjectPulse creates an auto-documentation generator.
func NewProjectPulse(facts *FactService) *ProjectPulse {
	return &ProjectPulse{facts: facts}
}

// PulseSection is a domain section of the auto-generated documentation.
type PulseSection struct {
	Domain string   `json:"domain"`
	Facts  []string `json:"facts"`
	Count  int      `json:"count"`
}

// PulseReport is the full auto-generated documentation.
type PulseReport struct {
	GeneratedAt time.Time      `json:"generated_at"`
	ProjectName string         `json:"project_name"`
	Sections    []PulseSection `json:"sections"`
	TotalFacts  int            `json:"total_facts"`
	Markdown    string         `json:"markdown"`
}

// Generate produces a documentation report from L0 (project) and L1 (domain) facts.
func (p *ProjectPulse) Generate(ctx context.Context) (*PulseReport, error) {
	// Get L0 facts (project-level).
	l0Facts, err := p.facts.GetL0Facts(ctx)
	if err != nil {
		return nil, fmt.Errorf("pulse: L0 facts: %w", err)
	}

	// Get L1 facts (domain-level) by listing domains.
	domains, err := p.facts.ListDomains(ctx)
	if err != nil {
		return nil, fmt.Errorf("pulse: list domains: %w", err)
	}

	report := &PulseReport{
		GeneratedAt: time.Now(),
		ProjectName: "GoMCP",
	}

	// L0 section.
	if len(l0Facts) > 0 {
		section := PulseSection{Domain: "Project (L0)", Count: len(l0Facts)}
		for _, f := range l0Facts {
			section.Facts = append(section.Facts, factSummary(f))
		}
		report.Sections = append(report.Sections, section)
		report.TotalFacts += len(l0Facts)
	}

	// L1 sections per domain.
	for _, domain := range domains {
		domainFacts, err := p.facts.ListFacts(ctx, ListFactsParams{Domain: domain})
		if err != nil {
			continue
		}
		// Filter to L1 only.
		var filtered []*memory.Fact
		for _, f := range domainFacts {
			if f.Level <= 1 {
				filtered = append(filtered, f)
			}
		}
		if len(filtered) == 0 {
			continue
		}
		section := PulseSection{Domain: domain, Count: len(filtered)}
		for _, f := range filtered {
			section.Facts = append(section.Facts, factSummary(f))
		}
		report.Sections = append(report.Sections, section)
		report.TotalFacts += len(filtered)
	}

	report.Markdown = renderPulseMarkdown(report)
	return report, nil
}

func factSummary(f *memory.Fact) string {
	s := f.Content
	if len(s) > 120 {
		s = s[:120] + "..."
	}
	label := ""
	if f.IsGene {
		label = " 🧬"
	}
	return fmt.Sprintf("- %s%s", s, label)
}

func renderPulseMarkdown(r *PulseReport) string {
	var b strings.Builder
	fmt.Fprintf(&b, "# %s — Project Pulse\n\n", r.ProjectName)
	fmt.Fprintf(&b, "> Auto-generated: %s | %d facts\n\n", r.GeneratedAt.Format("2006-01-02 15:04"), r.TotalFacts)

	for _, section := range r.Sections {
		fmt.Fprintf(&b, "## %s (%d facts)\n\n", section.Domain, section.Count)
		for _, fact := range section.Facts {
			fmt.Fprintln(&b, fact)
		}
		fmt.Fprintln(&b)
	}

	return b.String()
}
