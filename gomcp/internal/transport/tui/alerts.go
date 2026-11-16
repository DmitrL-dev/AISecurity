package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/syntrex/gomcp/internal/domain/alert"
)

var (
	alertInfoStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("#00ff00"))
	alertWarningStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#ffaa00")).Bold(true)
	alertCriticalStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#ff0000")).Bold(true)
	alertTimeStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("#666666"))
	alertSourceStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("#888888"))
)

// RenderAlerts renders the alert panel with color-coded severity.
func RenderAlerts(alerts []alert.Alert, maxAlerts int) string {
	var b strings.Builder

	title := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#ff6600")).
		Render("─── DIP-WATCHER ALERTS ───")
	b.WriteString(title + "\n")

	if len(alerts) == 0 {
		b.WriteString(alertInfoStyle.Render("  🟢 No alerts — system nominal"))
		return b.String()
	}

	if len(alerts) > maxAlerts {
		alerts = alerts[:maxAlerts]
	}

	for _, a := range alerts {
		ts := alertTimeStyle.Render(a.Timestamp.Format("15:04:05"))
		src := alertSourceStyle.Render(fmt.Sprintf("[%s]", a.Source))

		var msgStyled string
		switch a.Severity {
		case alert.SeverityCritical:
			msgStyled = alertCriticalStyle.Render(fmt.Sprintf("%s %s", a.Severity.Icon(), a.Message))
		case alert.SeverityWarning:
			msgStyled = alertWarningStyle.Render(fmt.Sprintf("%s %s", a.Severity.Icon(), a.Message))
		default:
			msgStyled = alertInfoStyle.Render(fmt.Sprintf("%s %s", a.Severity.Icon(), a.Message))
		}

		b.WriteString(fmt.Sprintf("  %s %s %s\n", ts, src, msgStyled))
	}

	return b.String()
}
