package tools

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// DoctorCheck represents a single diagnostic check result.
type DoctorCheck struct {
	Name    string `json:"name"`
	Status  string `json:"status"` // "OK", "WARN", "FAIL"
	Details string `json:"details,omitempty"`
	Elapsed string `json:"elapsed"`
}

// DoctorReport is the full self-diagnostic report (v3.7).
type DoctorReport struct {
	Timestamp time.Time     `json:"timestamp"`
	Checks    []DoctorCheck `json:"checks"`
	Summary   string        `json:"summary"` // "HEALTHY", "DEGRADED", "CRITICAL"
}

// DoctorService provides self-diagnostic capabilities (v3.7 Cerebro).
type DoctorService struct {
	db           *sql.DB
	rlmDir       string
	facts        *FactService
	embedderName string           // v3.7: Oracle model name
	socChecker   SOCHealthChecker // v3.9: SOC health
}

// SOCHealthChecker is an interface for SOC health diagnostics.
// Implemented by application/soc.Service to avoid circular imports.
type SOCHealthChecker interface {
	Dashboard() (SOCDashboardData, error)
}

// SOCDashboardData mirrors the dashboard KPIs needed for doctor checks.
type SOCDashboardData struct {
	TotalEvents      int  `json:"total_events"`
	CorrelationRules int  `json:"correlation_rules"`
	Playbooks        int  `json:"playbooks"`
	ChainValid       bool `json:"chain_valid"`
	SensorsOnline    int  `json:"sensors_online"`
	SensorsTotal     int  `json:"sensors_total"`
}

// NewDoctorService creates the doctor diagnostic service.
func NewDoctorService(db *sql.DB, rlmDir string, facts *FactService) *DoctorService {
	return &DoctorService{db: db, rlmDir: rlmDir, facts: facts}
}

// SetEmbedderName sets the Oracle model name for diagnostics.
func (d *DoctorService) SetEmbedderName(name string) {
	d.embedderName = name
}

// SetSOCChecker sets the SOC health checker for diagnostics (v3.9).
func (d *DoctorService) SetSOCChecker(c SOCHealthChecker) {
	d.socChecker = c
}

// RunDiagnostics performs all self-diagnostic checks.
func (d *DoctorService) RunDiagnostics(ctx context.Context) DoctorReport {
	report := DoctorReport{
		Timestamp: time.Now(),
	}

	report.Checks = append(report.Checks, d.checkStorage())
	report.Checks = append(report.Checks, d.checkGenome(ctx))
	report.Checks = append(report.Checks, d.checkLeash())
	report.Checks = append(report.Checks, d.checkOracle())
	report.Checks = append(report.Checks, d.checkPermissions())
	report.Checks = append(report.Checks, d.checkDecisionsLog())
	report.Checks = append(report.Checks, d.checkSOC())

	// Compute summary.
	fails, warns := 0, 0
	for _, c := range report.Checks {
		switch c.Status {
		case "FAIL":
			fails++
		case "WARN":
			warns++
		}
	}
	switch {
	case fails > 0:
		report.Summary = "CRITICAL"
	case warns > 0:
		report.Summary = "DEGRADED"
	default:
		report.Summary = "HEALTHY"
	}

	return report
}

func (d *DoctorService) checkStorage() DoctorCheck {
	start := time.Now()
	if d.db == nil {
		return DoctorCheck{Name: "Storage", Status: "FAIL", Details: "database not configured", Elapsed: since(start)}
	}
	var result string
	err := d.db.QueryRow("PRAGMA integrity_check").Scan(&result)
	if err != nil {
		return DoctorCheck{Name: "Storage", Status: "FAIL", Details: err.Error(), Elapsed: since(start)}
	}
	if result != "ok" {
		return DoctorCheck{Name: "Storage", Status: "FAIL", Details: "integrity: " + result, Elapsed: since(start)}
	}
	return DoctorCheck{Name: "Storage", Status: "OK", Details: "PRAGMA integrity_check = ok", Elapsed: since(start)}
}

func (d *DoctorService) checkGenome(ctx context.Context) DoctorCheck {
	start := time.Now()
	if d.facts == nil {
		return DoctorCheck{Name: "Genome", Status: "WARN", Details: "fact service not configured", Elapsed: since(start)}
	}
	hash, count, err := d.facts.VerifyGenome(ctx)
	if err != nil {
		return DoctorCheck{Name: "Genome", Status: "FAIL", Details: err.Error(), Elapsed: since(start)}
	}
	if count == 0 {
		return DoctorCheck{Name: "Genome", Status: "WARN", Details: "no genes found", Elapsed: since(start)}
	}
	return DoctorCheck{Name: "Genome", Status: "OK", Details: fmt.Sprintf("%d genes, hash=%s", count, hash[:16]), Elapsed: since(start)}
}

func (d *DoctorService) checkLeash() DoctorCheck {
	start := time.Now()
	leashPath := filepath.Join(d.rlmDir, "..", ".sentinel_leash")
	data, err := os.ReadFile(leashPath)
	if err != nil {
		if os.IsNotExist(err) {
			return DoctorCheck{Name: "Leash", Status: "OK", Details: "mode=ARMED (no leash file)", Elapsed: since(start)}
		}
		return DoctorCheck{Name: "Leash", Status: "WARN", Details: "cannot read: " + err.Error(), Elapsed: since(start)}
	}
	content := string(data)
	switch {
	case contains(content, "ZERO-G"):
		return DoctorCheck{Name: "Leash", Status: "WARN", Details: "mode=ZERO-G (ethical filters disabled)", Elapsed: since(start)}
	case contains(content, "SAFE"):
		return DoctorCheck{Name: "Leash", Status: "OK", Details: "mode=SAFE (read-only)", Elapsed: since(start)}
	case contains(content, "ARMED"):
		return DoctorCheck{Name: "Leash", Status: "OK", Details: "mode=ARMED", Elapsed: since(start)}
	default:
		return DoctorCheck{Name: "Leash", Status: "WARN", Details: "unknown mode: " + content[:min(20, len(content))], Elapsed: since(start)}
	}
}

func (d *DoctorService) checkPermissions() DoctorCheck {
	start := time.Now()
	testFile := filepath.Join(d.rlmDir, ".doctor_probe")
	err := os.WriteFile(testFile, []byte("probe"), 0o644)
	if err != nil {
		return DoctorCheck{Name: "Permissions", Status: "FAIL", Details: "cannot write to .rlm/: " + err.Error(), Elapsed: since(start)}
	}
	os.Remove(testFile)
	return DoctorCheck{Name: "Permissions", Status: "OK", Details: ".rlm/ writable", Elapsed: since(start)}
}

func (d *DoctorService) checkDecisionsLog() DoctorCheck {
	start := time.Now()
	logPath := filepath.Join(d.rlmDir, "decisions.log")
	if _, err := os.Stat(logPath); os.IsNotExist(err) {
		return DoctorCheck{Name: "Decisions", Status: "WARN", Details: "decisions.log not found (no decisions recorded yet)", Elapsed: since(start)}
	}
	info, err := os.Stat(logPath)
	if err != nil {
		return DoctorCheck{Name: "Decisions", Status: "FAIL", Details: err.Error(), Elapsed: since(start)}
	}
	return DoctorCheck{Name: "Decisions", Status: "OK", Details: fmt.Sprintf("decisions.log size=%d bytes", info.Size()), Elapsed: since(start)}
}

func (d *DoctorService) checkOracle() DoctorCheck {
	start := time.Now()
	if d.embedderName == "" {
		return DoctorCheck{Name: "Oracle", Status: "WARN", Details: "no embedder configured (FTS5 fallback)", Elapsed: since(start)}
	}
	if contains(d.embedderName, "onnx") || contains(d.embedderName, "ONNX") {
		return DoctorCheck{Name: "Oracle", Status: "OK", Details: "ONNX model loaded: " + d.embedderName, Elapsed: since(start)}
	}
	return DoctorCheck{Name: "Oracle", Status: "OK", Details: "embedder: " + d.embedderName, Elapsed: since(start)}
}

func (d *DoctorService) checkSOC() DoctorCheck {
	start := time.Now()
	if d.socChecker == nil {
		return DoctorCheck{Name: "SOC", Status: "WARN", Details: "SOC service not configured", Elapsed: since(start)}
	}

	dash, err := d.socChecker.Dashboard()
	if err != nil {
		return DoctorCheck{Name: "SOC", Status: "FAIL", Details: "dashboard error: " + err.Error(), Elapsed: since(start)}
	}

	// Check chain integrity.
	if !dash.ChainValid {
		return DoctorCheck{
			Name:    "SOC",
			Status:  "WARN",
			Details: fmt.Sprintf("chain BROKEN (rules=%d, playbooks=%d, events=%d)", dash.CorrelationRules, dash.Playbooks, dash.TotalEvents),
			Elapsed: since(start),
		}
	}

	// Check sensor health.
	offline := dash.SensorsTotal - dash.SensorsOnline
	if offline > 0 {
		return DoctorCheck{
			Name:    "SOC",
			Status:  "WARN",
			Details: fmt.Sprintf("rules=%d, playbooks=%d, events=%d, %d/%d sensors OFFLINE", dash.CorrelationRules, dash.Playbooks, dash.TotalEvents, offline, dash.SensorsTotal),
			Elapsed: since(start),
		}
	}

	return DoctorCheck{
		Name:    "SOC",
		Status:  "OK",
		Details: fmt.Sprintf("rules=%d, playbooks=%d, events=%d, chain=valid", dash.CorrelationRules, dash.Playbooks, dash.TotalEvents),
		Elapsed: since(start),
	}
}

func since(t time.Time) string {
	return fmt.Sprintf("%dms", time.Since(t).Milliseconds())
}

func contains(s, substr string) bool {
	for i := 0; i+len(substr) <= len(s); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ToJSON is already in the package. Alias for DoctorReport.
func (r DoctorReport) JSON() string {
	data, _ := json.MarshalIndent(r, "", "  ")
	return string(data)
}
