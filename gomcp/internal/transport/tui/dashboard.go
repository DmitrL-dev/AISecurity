package tui

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/syntrex/gomcp/internal/application/orchestrator"
	"github.com/syntrex/gomcp/internal/domain/alert"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/peer"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

// tickMsg is sent periodically to refresh the dashboard.
type tickMsg time.Time

// State holds all data needed for the dashboard display.
type State struct {
	Orchestrator *orchestrator.Orchestrator
	Store        memory.FactStore
	PeerReg      *peer.Registry
	Embedder     vectorstore.Embedder // nil = no oracle
	AlertBus     *alert.Bus           // nil = no alerts
	SystemMode   string               // "ARMED", "ZERO-G", "SAFE" (v3.2)
	Scope        rlmscope.Scope
}

// Model is the Bubbletea model for the dashboard.
type Model struct {
	state    State
	ctx      context.Context
	cancel   context.CancelFunc
	width    int
	height   int
	alerts   []alert.Alert
	maxLogs  int
	quitting bool

	// Cached display data (refreshed on tick).
	genes      []GeneStatus
	genomeHash string
	genomeOK   bool
	entropy    float64
	apoptosis  bool
	cycle      int
	memLevels  []MemoryLevel
	geneCount  int
	totalFacts int
	peers      []PeerInfo
	selfID     string
	selfNode   string
	oracleMode string
	systemMode string // v3.2: ARMED / ZERO-G / SAFE
	coldFacts  int    // v3.3: hit_count=0 facts >30 days
}

// NewModel creates a new dashboard model.
func NewModel(state State) Model {
	ctx, cancel := context.WithCancel(rlmscope.WithScope(context.Background(), state.Scope))
	return Model{
		state:   state,
		ctx:     ctx,
		cancel:  cancel,
		width:   80,
		height:  40,
		maxLogs: 8,
		genes:   DefaultGeneStatuses(true),
	}
}

// Init implements tea.Model.
func (m Model) Init() tea.Cmd {
	return tea.Batch(
		tickCmd(),
		tea.SetWindowTitle("SENTINEL Dashboard"),
	)
}

// Update implements tea.Model.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			m.quitting = true
			m.cancel()
			return m, tea.Quit
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil

	case tickMsg:
		m.refresh()
		return m, tickCmd()
	}

	return m, nil
}

// View implements tea.Model.
func (m Model) View() string {
	if m.quitting {
		return "\n  SENTINEL shutdown — genome preserved.\n\n"
	}

	var b strings.Builder

	// Title.
	titleWidth := m.width
	if titleWidth < 40 {
		titleWidth = 80
	}
	// v3.2: mode-aware title and border.
	titleText := "🛡️  SENTINEL DASHBOARD  🛡️"
	if m.systemMode == "ZERO-G" {
		titleText = "⚠️  SENTINEL — ZERO-G ACTIVE  ⚠️"
	} else if m.systemMode == "SAFE" {
		titleText = "🔒  SENTINEL — SAFE MODE  🔒"
	}
	title := titleStyle.Width(titleWidth).Render(titleText)
	b.WriteString(title + "\n\n")

	// Calculate quadrant width.
	qWidth := (m.width - 6) / 2
	if qWidth < 30 {
		qWidth = 38
	}

	qStyle := quadrantStyle.Width(qWidth)
	// v3.2: red border in ZERO-G mode.
	if m.systemMode == "ZERO-G" {
		qStyle = qStyle.BorderForeground(colorCritical)
	}

	// Row 1: Genome + Entropy.
	genomeView := RenderGenome(m.genes, m.genomeHash, m.genomeOK)
	entropyView := RenderEntropy(m.entropy, m.apoptosis, m.cycle)

	// Apply consistent width.
	genomeView = qStyle.Render(stripBorder(genomeView, qWidth))
	entropyView = qStyle.Render(stripBorder(entropyView, qWidth))

	row1 := lipgloss.JoinHorizontal(lipgloss.Top, genomeView, " ", entropyView)
	b.WriteString(row1 + "\n")

	// Row 2: Memory + Network.
	memoryView := RenderMemory(m.memLevels, m.geneCount, m.totalFacts)
	networkView := RenderNetwork(m.peers, m.selfID, m.selfNode)

	memoryView = qStyle.Render(stripBorder(memoryView, qWidth))
	networkView = qStyle.Render(stripBorder(networkView, qWidth))

	row2 := lipgloss.JoinHorizontal(lipgloss.Top, memoryView, " ", networkView)
	b.WriteString(row2 + "\n")

	// Alert panel (replaces simple log frame) — height-constrained.
	alertContent := RenderAlerts(m.alerts, m.maxLogs)
	alertFrame := logStyle.Width(m.width - 4).MaxHeight(m.maxLogs + 3).Render(alertContent)
	b.WriteString(alertFrame + "\n")

	// Status bar.
	oracleStr := "ORACLE: N/A"
	if m.oracleMode != "" {
		oracleStr = "ORACLE: " + m.oracleMode
	}

	// v3.2: mode-aware entropy display + system mode indicator.
	entropyStr := fmt.Sprintf("%.4f", m.entropy)
	if m.systemMode == "ZERO-G" && m.entropy > 0.9 {
		entropyStr = "CHAOS"
	}

	modeStr := ""
	if m.systemMode == "ZERO-G" {
		modeStr = " │ ⚠️ ZERO-G"
	} else if m.systemMode == "SAFE" {
		modeStr = " │ 🔒 SAFE"
	}

	// v3.3: Cold facts indicator.
	coldStr := ""
	if m.coldFacts > 0 {
		coldStr = fmt.Sprintf(" │ ❄️ Cold: %d", m.coldFacts)
	}

	status := fmt.Sprintf("Cycle: %d │ Entropy: %s │ %s%s%s │ 'q' quit",
		m.cycle, entropyStr, oracleStr, modeStr, coldStr)

	statusStyle := statusBarStyle.Width(m.width)
	if m.systemMode == "ZERO-G" {
		statusStyle = statusStyle.Foreground(colorCritical).Bold(true).Blink(true)
	}
	b.WriteString(statusStyle.Render(status))

	return b.String()
}

// refresh pulls fresh data from orchestrator and store.
func (m *Model) refresh() {
	ctx := m.ctx

	// Genome status.
	genes, err := m.state.Store.ListGenes(ctx)
	if err == nil {
		m.geneCount = len(genes)
		m.genomeHash = memory.CompiledGenomeHash()

		// Check each hardcoded gene.
		existingIDs := make(map[string]bool)
		for _, g := range genes {
			existingIDs[g.ID] = true
		}
		statuses := make([]GeneStatus, len(memory.HardcodedGenes))
		for i, hg := range memory.HardcodedGenes {
			statuses[i] = GeneStatus{
				ID:       hg.ID,
				Domain:   hg.Domain,
				Active:   existingIDs[hg.ID],
				Verified: existingIDs[hg.ID],
			}
		}
		m.genes = statuses
		m.genomeOK = len(genes) >= len(memory.HardcodedGenes)
	}

	// Memory stats.
	stats, err := m.state.Store.Stats(ctx)
	if err == nil {
		m.totalFacts = stats.TotalFacts
		m.memLevels = []MemoryLevel{
			{Label: "L0 Project", Count: stats.ByLevel[memory.LevelProject]},
			{Label: "L1 Domain", Count: stats.ByLevel[memory.LevelDomain]},
			{Label: "L2 Module", Count: stats.ByLevel[memory.LevelModule]},
			{Label: "L3 Snippet", Count: stats.ByLevel[memory.LevelSnippet]},
		}
		m.coldFacts = stats.ColdCount // v3.3
	}

	// Orchestrator stats.
	if m.state.Orchestrator != nil {
		oStats := m.state.Orchestrator.Stats()
		if c, ok := oStats["cycle"].(int); ok {
			m.cycle = c
		}

		history := m.state.Orchestrator.History()
		if len(history) > 0 {
			last := history[len(history)-1]
			m.entropy = last.EntropyLevel
			m.apoptosis = last.ApoptosisTriggered

			// Log entry.
			logLine := fmt.Sprintf("[%s] cycle=%d entropy=%.4f genome=%v healed=%d",
				last.StartedAt.Format("15:04:05"),
				last.Cycle, last.EntropyLevel, last.GenomeIntact, last.GenesHealed)
			m.addLog(logLine)
		}
	}

	// Peer status.
	if m.state.PeerReg != nil {
		m.selfID = m.state.PeerReg.SelfID()
		m.selfNode = m.state.PeerReg.NodeName()

		peerList := m.state.PeerReg.ListPeers()
		m.peers = make([]PeerInfo, 0, len(peerList))
		for _, p := range peerList {
			m.peers = append(m.peers, PeerInfo{
				NodeName:      p.NodeName,
				Trust:         p.Trust.String(),
				LastHandshake: p.HandshakeAt.Format("15:04:05"),
				SyncStatus:    fmt.Sprintf("%d facts", p.FactCount),
			})
		}
	}

	// Oracle status.
	if m.state.Embedder != nil {
		m.oracleMode = m.state.Embedder.Mode().String()
	}

	// Alert bus refresh.
	if m.state.AlertBus != nil {
		m.alerts = m.state.AlertBus.Recent(m.maxLogs)
	}

	// v3.2: System mode from State.
	m.systemMode = m.state.SystemMode
}

func (m *Model) addLog(line string) {
	// Legacy: alerts are now sourced from AlertBus via refresh().
	_ = line
}

func tickCmd() tea.Cmd {
	return tea.Tick(2*time.Second, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

// stripBorder is a helper that returns content without double-bordering.
func stripBorder(rendered string, _ int) string {
	// Remove outer border if already applied by component renderers.
	lines := strings.Split(rendered, "\n")
	if len(lines) > 2 {
		// Check if first line looks like a border.
		firstTrimmed := strings.TrimSpace(lines[0])
		if strings.HasPrefix(firstTrimmed, "╭") || strings.HasPrefix(firstTrimmed, "┌") {
			// Already bordered, extract inner content.
			inner := make([]string, 0, len(lines)-2)
			for _, l := range lines[1 : len(lines)-1] {
				trimmed := strings.TrimSpace(l)
				if strings.HasPrefix(trimmed, "│") {
					// Remove border chars.
					trimmed = strings.TrimPrefix(trimmed, "│")
					trimmed = strings.TrimSuffix(trimmed, "│")
					trimmed = strings.TrimSpace(trimmed)
				}
				inner = append(inner, " "+trimmed)
			}
			return strings.Join(inner, "\n")
		}
	}
	return rendered
}

// Start launches the TUI dashboard. Blocks until quit.
// Redirects log output to file to prevent corruption of Bubbletea alt screen.
func Start(state State) error {
	// Redirect log to file — log.Printf from orchestrator goroutine
	// corrupts Bubbletea alt screen buffer causing layout drift.
	logFile, err := os.OpenFile(".rlm/tui.log", os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err == nil {
		log.SetOutput(logFile)
		defer func() {
			log.SetOutput(os.Stderr) // restore on exit
			logFile.Close()
		}()
	}

	m := NewModel(state)
	p := tea.NewProgram(m, tea.WithAltScreen())
	_, err = p.Run()
	return err
}
