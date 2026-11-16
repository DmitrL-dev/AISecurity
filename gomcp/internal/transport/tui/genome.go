package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/syntrex/gomcp/internal/domain/memory"
)

// GeneStatus holds the display state for one gene.
type GeneStatus struct {
	ID       string
	Domain   string
	Active   bool
	Verified bool
}

// RenderGenome renders Quadrant A: Genome Status.
func RenderGenome(genes []GeneStatus, genomeHash string, intact bool) string {
	var b strings.Builder

	title := quadrantTitleStyle.Render("🧬 GENOME STATUS")
	b.WriteString(title + "\n")

	for _, g := range genes {
		var indicator string
		if g.Active && g.Verified {
			indicator = geneActiveStyle.Render("●")
		} else if g.Active {
			indicator = lipgloss.NewStyle().Foreground(colorYellow).Render("◐")
		} else {
			indicator = geneInactiveStyle.Render("○")
		}

		name := formatGeneName(g.ID)
		b.WriteString(fmt.Sprintf(" %s %s\n", indicator, name))
	}

	// Hash footer.
	b.WriteString("\n")
	hashShort := genomeHash
	if len(hashShort) > 16 {
		hashShort = hashShort[:16] + "…"
	}
	if intact {
		b.WriteString(geneActiveStyle.Render(fmt.Sprintf(" ✓ %s", hashShort)))
	} else {
		b.WriteString(entropyHighStyle.Render(fmt.Sprintf(" ✗ TAMPER: %s", hashShort)))
	}

	return quadrantStyle.Render(b.String())
}

// DefaultGeneStatuses returns gene statuses from hardcoded genes.
func DefaultGeneStatuses(verified bool) []GeneStatus {
	statuses := make([]GeneStatus, len(memory.HardcodedGenes))
	for i, g := range memory.HardcodedGenes {
		statuses[i] = GeneStatus{
			ID:       g.ID,
			Domain:   g.Domain,
			Active:   true,
			Verified: verified,
		}
	}
	return statuses
}

func formatGeneName(id string) string {
	// GENE_01_SOVEREIGNTY → Sovereignty
	parts := strings.Split(id, "_")
	if len(parts) >= 3 {
		name := strings.ToLower(parts[2])
		if len(name) > 0 {
			return strings.ToUpper(name[:1]) + name[1:]
		}
	}
	return id
}
