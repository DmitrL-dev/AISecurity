// Package tui provides the SENTINEL TUI Dashboard.
//
// Uses Bubbletea + Lipgloss for a 4-quadrant terminal interface:
//   - Quadrant A: Genome Status (6 genes)
//   - Quadrant B: Entropy/Apathy Monitor
//   - Quadrant C: Memory Depth (L0-L3 counters)
//   - Quadrant D: Resonance Mesh (peers)
package tui

import "github.com/charmbracelet/lipgloss"

// --- Color Palette ---

var (
	colorGreen    = lipgloss.Color("#00FF87")
	colorYellow   = lipgloss.Color("#FFFF00")
	colorRed      = lipgloss.Color("#FF5555")
	colorCyan     = lipgloss.Color("#00FFFF")
	colorMagenta  = lipgloss.Color("#FF79C6")
	colorDim      = lipgloss.Color("#6272A4")
	colorBorder   = lipgloss.Color("#44475A")
	colorTitle    = lipgloss.Color("#BD93F9")
	colorAccent   = lipgloss.Color("#50FA7B")
	colorCritical = lipgloss.Color("#FF4444")
)

// --- Styles ---

var (
	// Title bar at the top.
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorTitle).
			Background(lipgloss.Color("#2D2B55")).
			Padding(0, 2).
			Width(80).
			Align(lipgloss.Center)

	// Quadrant border.
	quadrantStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(colorBorder).
			Padding(1, 2).
			Width(38)

	// Quadrant title.
	quadrantTitleStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(colorCyan).
				MarginBottom(1)

	// Gene status indicators.
	geneActiveStyle = lipgloss.NewStyle().
			Foreground(colorGreen).
			Bold(true)

	geneInactiveStyle = lipgloss.NewStyle().
				Foreground(colorDim)

	// Entropy bar colors.
	entropyLowStyle = lipgloss.NewStyle().
			Foreground(colorGreen)

	entropyMidStyle = lipgloss.NewStyle().
			Foreground(colorYellow)

	entropyHighStyle = lipgloss.NewStyle().
				Foreground(colorRed).
				Bold(true)

	entropyCriticalStyle = lipgloss.NewStyle().
				Foreground(colorCritical).
				Bold(true).
				Blink(true)

	// Memory level labels.
	memoryLabelStyle = lipgloss.NewStyle().
				Foreground(colorMagenta).
				Width(12)

	memoryCountStyle = lipgloss.NewStyle().
				Foreground(colorAccent).
				Bold(true)

	// Peer status.
	peerOnlineStyle = lipgloss.NewStyle().
			Foreground(colorGreen)

	peerOfflineStyle = lipgloss.NewStyle().
				Foreground(colorDim)

	// Status bar at the bottom.
	statusBarStyle = lipgloss.NewStyle().
			Foreground(colorDim).
			Width(80).
			Align(lipgloss.Center)

	// Log frame.
	logStyle = lipgloss.NewStyle().
			Border(lipgloss.NormalBorder()).
			BorderForeground(colorDim).
			Padding(0, 1).
			Width(80).
			Height(5).
			Foreground(colorDim)
)
