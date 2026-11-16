package mcpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/mark3labs/mcp-go/mcp"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/application/tools"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
)

// SetSOCService enables SOC tools (soc_ingest, soc_events, soc_incidents, soc_sensors, soc_dashboard).
func (s *Server) SetSOCService(svc *appsoc.Service) {
	s.socSvc = svc
}

// registerSOCTools registers SENTINEL AI SOC MCP tools.
func (s *Server) registerSOCTools() {
	if s.socSvc == nil {
		log.Printf("SOC Service not configured — skipping SOC tools registration")
		return
	}

	s.mcp.AddTool(
		mcp.NewTool("soc_ingest",
			mcp.WithDescription("Ingest a security event into the SOC pipeline. Runs Secret Scanner (Step 0), rate limits, decision logging, correlation, and playbook matching."),
			mcp.WithString("source", mcp.Description("Event source: sentinel_core, shield, immune, gomcp, lattice, external"), mcp.Required()),
			mcp.WithString("severity", mcp.Description("Severity: INFO, LOW, MEDIUM, HIGH, CRITICAL"), mcp.Required()),
			mcp.WithString("category", mcp.Description("Event category: jailbreak, injection, exfiltration, tool_abuse, auth_bypass, etc."), mcp.Required()),
			mcp.WithString("description", mcp.Description("Event description"), mcp.Required()),
			mcp.WithString("payload", mcp.Description("Raw payload for Secret Scanner Step 0 (optional)")),
			mcp.WithString("sensor_id", mcp.Description("Sensor ID (auto-assigns from source if empty)")),
			mcp.WithString("sensor_key", mcp.Description("Sensor API key for authentication (§17.3 T-01)")),
			mcp.WithNumber("confidence", mcp.Description("Confidence score 0.0-1.0 (default 0.5)")),
			mcp.WithBoolean("zero_g_mode", mcp.Description("Tag as Zero-G mode (Strike Force operation, §13.4)")),
		),
		s.handleSOCIngest,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_events",
			mcp.WithDescription("List recent SOC events. Returns events sorted by timestamp descending."),
			mcp.WithNumber("limit", mcp.Description("Max events to return (default 20)")),
		),
		s.handleSOCEvents,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_incidents",
			mcp.WithDescription("List SOC incidents with optional status filter."),
			mcp.WithString("status", mcp.Description("Filter by status: OPEN, INVESTIGATING, RESOLVED (empty = all)")),
			mcp.WithNumber("limit", mcp.Description("Max incidents to return (default 20)")),
		),
		s.handleSOCIncidents,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_verdict",
			mcp.WithDescription("Update an incident status (manual analyst verdict)."),
			mcp.WithString("incident_id", mcp.Description("Incident ID"), mcp.Required()),
			mcp.WithString("status", mcp.Description("New status: INVESTIGATING, RESOLVED"), mcp.Required()),
		),
		s.handleSOCVerdict,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_sensors",
			mcp.WithDescription("List all registered SOC sensors with status and heartbeat info."),
		),
		s.handleSOCSensors,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_dashboard",
			mcp.WithDescription("Get SOC dashboard KPIs: events, incidents, sensor health, decision chain integrity (§12.2)."),
		),
		s.handleSOCDashboard,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_compliance",
			mcp.WithDescription("Generate EU AI Act Article 15 compliance report with requirement status and evidence (§12.3)."),
		),
		s.handleSOCCompliance,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_compliance_soc2",
			mcp.WithDescription("Generate SOC 2 Common Criteria (CC4/CC7) self-assessment with per-control status backed by live, machine-verifiable evidence (decision-chain integrity, SOC metrics) (§12.3, IMP8)."),
		),
		s.handleSOCComplianceSOC2,
	)

	s.mcp.AddTool(
		mcp.NewTool("soc_playbook_run",
			mcp.WithDescription("Manually execute a playbook against an incident (§10, §12.1)."),
			mcp.WithString("playbook_id", mcp.Description("Playbook ID (e.g. pb-auto-block-jailbreak)"), mcp.Required()),
			mcp.WithString("incident_id", mcp.Description("Target incident ID"), mcp.Required()),
		),
		s.handleSOCPlaybookRun,
	)
}

// --- SOC Handlers ---

func (s *Server) handleSOCIngest(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	source := domsoc.EventSource(req.GetString("source", "external"))
	severity := domsoc.EventSeverity(req.GetString("severity", "MEDIUM"))
	category := req.GetString("category", "")
	description := req.GetString("description", "")

	if category == "" || description == "" {
		return errorResult(fmt.Errorf("'category' and 'description' are required")), nil
	}

	event := domsoc.NewSOCEvent(source, severity, category, description)
	event.Payload = req.GetString("payload", "")
	event.SensorID = req.GetString("sensor_id", "")
	event.SensorKey = req.GetString("sensor_key", "")
	event.ZeroGMode = req.GetBool("zero_g_mode", false)

	args := req.GetArguments()
	if v, ok := args["confidence"]; ok {
		if n, ok := v.(float64); ok {
			updated := event.WithConfidence(n)
			event = updated
		}
	}

	id, incident, err := s.socSvc.IngestEvent(event)
	if err != nil {
		return errorResult(err), nil
	}

	result := map[string]interface{}{
		"event_id": id,
		"status":   "INGESTED",
	}
	if incident != nil {
		result["incident_created"] = true
		result["incident_id"] = incident.ID
		result["incident_severity"] = incident.Severity
		result["correlation_rule"] = incident.CorrelationRule
	}

	return textResult(tools.ToJSON(result)), nil
}

func (s *Server) handleSOCEvents(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	limit := req.GetInt("limit", 20)
	events, err := s.socSvc.ListEvents("", limit) // MCP: global view
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(events)), nil
}

func (s *Server) handleSOCIncidents(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	status := req.GetString("status", "")
	limit := req.GetInt("limit", 20)
	incidents, err := s.socSvc.ListIncidents("", status, limit) // MCP: global view
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(incidents)), nil
}

func (s *Server) handleSOCVerdict(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	incidentID := req.GetString("incident_id", "")
	statusStr := req.GetString("status", "")
	if incidentID == "" || statusStr == "" {
		return errorResult(fmt.Errorf("'incident_id' and 'status' are required")), nil
	}

	status := domsoc.IncidentStatus(statusStr)
	if status != domsoc.StatusInvestigating && status != domsoc.StatusResolved {
		return errorResult(fmt.Errorf("invalid status: must be INVESTIGATING or RESOLVED")), nil
	}

	if err := s.socSvc.UpdateVerdict(incidentID, status); err != nil {
		return errorResult(err), nil
	}

	result := map[string]interface{}{
		"incident_id": incidentID,
		"new_status":  statusStr,
		"updated":     true,
	}
	return textResult(toJSON(result)), nil
}

func (s *Server) handleSOCSensors(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	sensors, err := s.socSvc.ListSensors("") // MCP: global view
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(sensors)), nil
}

func (s *Server) handleSOCDashboard(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	dashboard, err := s.socSvc.Dashboard("") // MCP: global view
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(dashboard.JSON()), nil
}

func (s *Server) handleSOCCompliance(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	report, err := s.socSvc.ComplianceReport()
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(report)), nil
}

func (s *Server) handleSOCComplianceSOC2(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	report, err := s.socSvc.SOC2ComplianceReport()
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(report)), nil
}

func (s *Server) handleSOCPlaybookRun(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.socSvc == nil {
		return errorResult(fmt.Errorf("soc service not configured")), nil
	}

	playbookID := req.GetString("playbook_id", "")
	incidentID := req.GetString("incident_id", "")
	if playbookID == "" || incidentID == "" {
		return errorResult(fmt.Errorf("'playbook_id' and 'incident_id' are required")), nil
	}

	result, err := s.socSvc.RunPlaybook(playbookID, incidentID)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(result)), nil
}

// toJSON marshals to JSON string (local helper).
func toJSON(v interface{}) string {
	data, _ := json.MarshalIndent(v, "", "  ")
	return string(data)
}
