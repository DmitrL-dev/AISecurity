package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// MemoryLevel holds fact counts per hierarchy level.
type MemoryLevel struct {
	Label string
	Count int
}

// PeerInfo holds display info for a peer.
type PeerInfo struct {
	NodeName      string
	Trust         string
	LastHandshake string
	SyncStatus    string
}

// RenderMemory renders Quadrant C: Memory Depth.
func RenderMemory(levels []MemoryLevel, geneCount int, totalFacts int) string {
	var b strings.Builder

	title := quadrantTitleStyle.Render("📊 MEMORY DEPTH")
	b.WriteString(title + "\n")

	for _, l := range levels {
		label := memoryLabelStyle.Render(l.Label)
		count := memoryCountStyle.Render(fmt.Sprintf("%d", l.Count))

		// Mini bar.
		barLen := l.Count
		if barLen > 20 {
			barLen = 20
		}
		bar := lipgloss.NewStyle().Foreground(colorAccent).Render(strings.Repeat("▓", barLen))
		if barLen == 0 {
			bar = lipgloss.NewStyle().Foreground(colorDim).Render("—")
		}

		b.WriteString(fmt.Sprintf(" %s %s %s\n", label, count, bar))
	}

	b.WriteString("\n")
	b.WriteString(lipgloss.NewStyle().Foreground(colorDim).Render(
		fmt.Sprintf(" Genes: %d │ Total: %d", geneCount, totalFacts)))

	return quadrantStyle.Render(b.String())
}

// RenderNetwork renders Quadrant D: Resonance Mesh.
func RenderNetwork(peers []PeerInfo, selfID string, selfNode string) string {
	var b strings.Builder

	title := quadrantTitleStyle.Render("🌐 RESONANCE MESH")
	b.WriteString(title + "\n")

	// Self node.
	selfShort := selfID
	if len(selfShort) > 12 {
		selfShort = selfShort[:12] + "…"
	}
	b.WriteString(peerOnlineStyle.Render(fmt.Sprintf(" ● %s (self)", selfNode)) + "\n")
	b.WriteString(lipgloss.NewStyle().Foreground(colorDim).Render(
		fmt.Sprintf("   ID: %s", selfShort)) + "\n")
	b.WriteString("\n")

	if len(peers) == 0 {
		b.WriteString(peerOfflineStyle.Render(" No peers connected\n"))
		b.WriteString(peerOfflineStyle.Render(" Waiting for handshake…"))
	} else {
		for _, p := range peers {
			var indicator string
			switch p.Trust {
			case "VERIFIED":
				indicator = peerOnlineStyle.Render("●")
			case "PENDING":
				indicator = lipgloss.NewStyle().Foreground(colorYellow).Render("◐")
			default:
				indicator = peerOfflineStyle.Render("○")
			}

			b.WriteString(fmt.Sprintf(" %s %s [%s]\n", indicator, p.NodeName, p.Trust))
			b.WriteString(lipgloss.NewStyle().Foreground(colorDim).Render(
				fmt.Sprintf("   Last: %s │ Sync: %s\n", p.LastHandshake, p.SyncStatus)))
		}
	}

	return quadrantStyle.Render(b.String())
}
