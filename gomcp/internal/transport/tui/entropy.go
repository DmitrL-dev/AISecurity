package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// RenderEntropy renders Quadrant B: Apathy/Entropy Monitor.
func RenderEntropy(entropy float64, apoptosisTriggered bool, cycle int) string {
	var b strings.Builder

	title := quadrantTitleStyle.Render("⚡ APATHY MONITOR")
	b.WriteString(title + "\n")

	// Entropy progress bar.
	barWidth := 30
	filled := int(entropy * float64(barWidth))
	if filled > barWidth {
		filled = barWidth
	}
	if filled < 0 {
		filled = 0
	}

	bar := strings.Repeat("█", filled) + strings.Repeat("░", barWidth-filled)

	// Color based on entropy level.
	var styledBar string
	switch {
	case entropy >= 0.95:
		styledBar = entropyCriticalStyle.Render(bar)
	case entropy >= 0.8:
		styledBar = entropyHighStyle.Render(bar)
	case entropy >= 0.5:
		styledBar = entropyMidStyle.Render(bar)
	default:
		styledBar = entropyLowStyle.Render(bar)
	}

	b.WriteString(fmt.Sprintf(" %s %.2f\n", styledBar, entropy))

	// Labels.
	scaleLabels := lipgloss.NewStyle().Foreground(colorDim).Render(
		" 0.0              0.5             1.0")
	b.WriteString(scaleLabels + "\n\n")

	// Status.
	if apoptosisTriggered {
		b.WriteString(entropyCriticalStyle.Render(" ⚠ CRITICAL: EXTRACTION READY"))
	} else if entropy >= 0.8 {
		b.WriteString(entropyHighStyle.Render(" ▲ Elevated entropy detected"))
	} else if entropy >= 0.5 {
		b.WriteString(entropyMidStyle.Render(" ● Entropy within range"))
	} else {
		b.WriteString(entropyLowStyle.Render(" ● System nominal"))
	}

	b.WriteString("\n")
	b.WriteString(lipgloss.NewStyle().Foreground(colorDim).Render(
		fmt.Sprintf(" Cycle: %d", cycle)))

	return quadrantStyle.Render(b.String())
}
