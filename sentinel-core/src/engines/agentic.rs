//! Agentic Security Super-Engine
//!
//! Consolidated protection for AI agents, MCP, A2A, and tool invocations.
//! Combines patterns from 20 Python engines:
//! - agent_anomaly.py
//! - agent_card_validator.py
//! - agent_collusion_detector.py
//! - agent_memory_shield.py
//! - agent_playbook_detector.py
//! - agentic_ide_attack_detector.py
//! - agentic_monitor.py
//! - multi_agent_coordinator.py
//! - multi_agent_safety.py
//! - mcp_a2a_security.py
//! - mcp_combination_attack_detector.py
//! - tool_call_security.py
//! - tool_hijacker_detector.py
//! - tool_use_guardian.py
//! - model_context_protocol_guard.py
//! - a2a_security_detector.py
//! - human_agent_trust_detector.py
//! - nhi_identity_guard.py
//! - identity_privilege_detector.py
//! - web_agent_manipulation_detector.py

use std::collections::{HashMap, HashSet};

/// Agentic threat types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AgenticThreat {
    DangerousTool,
    PermissionEscalation,
    InjectionInArgs,
    DangerousCombination,
    ToolExfiltration,
    CodeExecution,
    FileSystemAccess,
    AgentCollusion,
    ToolHijacking,
    TyposquattedServer,
    UntrustedRegistry,
    InvalidAttestation,
    CapabilityAbuse,
    PrivilegeEscalation,
    MultiAgentCoordination,
    McpInjection,
}

impl AgenticThreat {
    pub fn as_str(&self) -> &'static str {
        match self {
            AgenticThreat::DangerousTool => "dangerous_tool",
            AgenticThreat::PermissionEscalation => "permission_escalation",
            AgenticThreat::InjectionInArgs => "injection_in_args",
            AgenticThreat::DangerousCombination => "dangerous_combination",
            AgenticThreat::ToolExfiltration => "tool_exfiltration",
            AgenticThreat::CodeExecution => "code_execution",
            AgenticThreat::FileSystemAccess => "file_system_access",
            AgenticThreat::AgentCollusion => "agent_collusion",
            AgenticThreat::ToolHijacking => "tool_hijacking",
            AgenticThreat::TyposquattedServer => "typosquatted_server",
            AgenticThreat::UntrustedRegistry => "untrusted_registry",
            AgenticThreat::InvalidAttestation => "invalid_attestation",
            AgenticThreat::CapabilityAbuse => "capability_abuse",
            AgenticThreat::PrivilegeEscalation => "privilege_escalation",
            AgenticThreat::MultiAgentCoordination => "multi_agent_coordination",
            AgenticThreat::McpInjection => "mcp_injection",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            AgenticThreat::CodeExecution => 95,
            AgenticThreat::PrivilegeEscalation => 90,
            AgenticThreat::PermissionEscalation => 90,
            AgenticThreat::ToolExfiltration => 85,
            AgenticThreat::AgentCollusion => 85,
            AgenticThreat::FileSystemAccess => 80,
            AgenticThreat::DangerousTool => 75,
            AgenticThreat::ToolHijacking => 75,
            AgenticThreat::McpInjection => 70,
            AgenticThreat::DangerousCombination => 70,
            AgenticThreat::TyposquattedServer => 65,
            AgenticThreat::InvalidAttestation => 60,
            AgenticThreat::UntrustedRegistry => 55,
            AgenticThreat::InjectionInArgs => 50,
            AgenticThreat::CapabilityAbuse => 50,
            AgenticThreat::MultiAgentCoordination => 45,
        }
    }
}

/// Risk level for tools
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum RiskLevel {
    Safe,
    Low,
    Medium,
    High,
    Critical,
}

impl RiskLevel {
    pub fn as_str(&self) -> &'static str {
        match self {
            RiskLevel::Safe => "safe",
            RiskLevel::Low => "low",
            RiskLevel::Medium => "medium",
            RiskLevel::High => "high",
            RiskLevel::Critical => "critical",
        }
    }
}

/// Dangerous tools that require special handling
const DANGEROUS_TOOLS: &[&str] = &[
    "run_command",
    "execute",
    "exec",
    "shell",
    "bash",
    "powershell",
    "cmd",
    "system",
    "eval",
    "spawn",
    "subprocess",
];

/// High-risk tools that can access filesystem
const FILESYSTEM_TOOLS: &[&str] = &[
    "write_file",
    "delete_file",
    "remove",
    "rmdir",
    "unlink",
    "create_file",
    "move_file",
    "rename",
];

/// Tools that can exfiltrate data
const EXFIL_TOOLS: &[&str] = &[
    "send_email",
    "http_post",
    "upload",
    "webhook",
    "send_request",
    "fetch",
    "curl",
];

/// Injection patterns in tool arguments
const ARG_INJECTION_PATTERNS: &[&str] = &[
    "; rm -rf",
    "| cat",
    "&& curl",
    "$(", 
    "`",
    "| wget",
    "; wget",
    "| nc",
    "; nc",
    "| bash",
    "; bash",
];

/// Trusted MCP registries
const TRUSTED_REGISTRIES: &[&str] = &[
    "npm",
    "github.com",
    "anthropic.com",
    "openai.com",
];

/// Popular MCP servers for typosquatting detection
const KNOWN_MCP_SERVERS: &[&str] = &[
    "filesystem",
    "brave-search",
    "memory",
    "puppeteer",
    "sequential-thinking",
    "git",
    "sqlite",
    "postgres",
    "fetch",
    "github",
];

/// Tool call representation
#[derive(Debug, Clone)]
pub struct ToolCall {
    pub name: String,
    pub arguments: HashMap<String, String>,
    pub raw_args: String,
}

impl ToolCall {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            arguments: HashMap::new(),
            raw_args: String::new(),
        }
    }

    pub fn with_arg(mut self, key: &str, value: &str) -> Self {
        self.arguments.insert(key.to_string(), value.to_string());
        self
    }

    pub fn with_raw(mut self, raw: &str) -> Self {
        self.raw_args = raw.to_string();
        self
    }
}

/// MCP Server metadata
#[derive(Debug, Clone)]
pub struct McpServer {
    pub name: String,
    pub uri: String,
    pub registry: String,
    pub attestation: Option<String>,
}

impl McpServer {
    pub fn new(name: &str, uri: &str, registry: &str) -> Self {
        Self {
            name: name.to_string(),
            uri: uri.to_string(),
            registry: registry.to_string(),
            attestation: None,
        }
    }

    pub fn with_attestation(mut self, att: &str) -> Self {
        self.attestation = Some(att.to_string());
        self
    }
}

/// Agentic analysis result
#[derive(Debug, Clone)]
pub struct AgenticResult {
    pub is_safe: bool,
    pub risk_level: RiskLevel,
    pub risk_score: f64,
    pub threats: Vec<AgenticThreat>,
    pub blocked_tools: Vec<String>,
    pub warnings: Vec<String>,
}

impl Default for AgenticResult {
    fn default() -> Self {
        Self {
            is_safe: true,
            risk_level: RiskLevel::Safe,
            risk_score: 0.0,
            threats: Vec::new(),
            blocked_tools: Vec::new(),
            warnings: Vec::new(),
        }
    }
}

/// Agentic Security Guard - consolidated super-engine
pub struct AgenticGuard {
    blocked_tools: HashSet<String>,
    allow_code_execution: bool,
    allow_filesystem: bool,
}

impl Default for AgenticGuard {
    fn default() -> Self {
        Self::new(false, false)
    }
}

impl AgenticGuard {
    pub fn new(allow_code_execution: bool, allow_filesystem: bool) -> Self {
        Self {
            blocked_tools: HashSet::new(),
            allow_code_execution,
            allow_filesystem,
        }
    }

    pub fn with_blocked_tool(mut self, tool: &str) -> Self {
        self.blocked_tools.insert(tool.to_string());
        self
    }

    /// Check if tool is dangerous
    pub fn is_dangerous_tool(&self, name: &str) -> RiskLevel {
        let name_lower = name.to_lowercase();

        if DANGEROUS_TOOLS.iter().any(|t| name_lower.contains(t)) {
            return RiskLevel::Critical;
        }
        if FILESYSTEM_TOOLS.iter().any(|t| name_lower.contains(t)) {
            return RiskLevel::High;
        }
        if EXFIL_TOOLS.iter().any(|t| name_lower.contains(t)) {
            return RiskLevel::High;
        }
        
        RiskLevel::Safe
    }

    /// Check for injection in arguments
    pub fn check_arg_injection(&self, tool: &ToolCall) -> Option<AgenticThreat> {
        // Check raw args
        let raw_lower = tool.raw_args.to_lowercase();
        for pattern in ARG_INJECTION_PATTERNS {
            if raw_lower.contains(pattern) {
                return Some(AgenticThreat::InjectionInArgs);
            }
        }

        // Check individual arguments
        for value in tool.arguments.values() {
            let value_lower = value.to_lowercase();
            for pattern in ARG_INJECTION_PATTERNS {
                if value_lower.contains(pattern) {
                    return Some(AgenticThreat::InjectionInArgs);
                }
            }
        }

        None
    }

    /// Check for privilege escalation
    pub fn check_privilege_escalation(&self, tool: &ToolCall) -> Option<AgenticThreat> {
        let raw_lower = tool.raw_args.to_lowercase();
        let name_lower = tool.name.to_lowercase();

        // Check for sudo/admin patterns
        if raw_lower.contains("sudo ") || 
           raw_lower.contains("as administrator") ||
           raw_lower.contains("--privileged") ||
           raw_lower.contains("runas /user:admin") {
            return Some(AgenticThreat::PrivilegeEscalation);
        }

        // Check for chmod/chown
        if name_lower.contains("chmod") || name_lower.contains("chown") {
            if raw_lower.contains("777") || raw_lower.contains("root") {
                return Some(AgenticThreat::PrivilegeEscalation);
            }
        }

        None
    }

    /// Check for exfiltration attempts
    pub fn check_exfiltration(&self, tool: &ToolCall) -> Option<AgenticThreat> {
        let name_lower = tool.name.to_lowercase();
        let raw_lower = tool.raw_args.to_lowercase();

        // Check if it's an exfil tool
        if EXFIL_TOOLS.iter().any(|t| name_lower.contains(t)) {
            // Check if sending sensitive data
            if raw_lower.contains("password") ||
               raw_lower.contains("secret") ||
               raw_lower.contains("api_key") ||
               raw_lower.contains("private_key") ||
               raw_lower.contains(".env") ||
               raw_lower.contains("credentials") {
                return Some(AgenticThreat::ToolExfiltration);
            }
        }

        None
    }

    /// Validate a single tool call
    pub fn validate_tool(&self, tool: &ToolCall) -> AgenticResult {
        let mut result = AgenticResult::default();
        let name_lower = tool.name.to_lowercase();

        // Check if explicitly blocked
        if self.blocked_tools.contains(&name_lower) {
            result.is_safe = false;
            result.blocked_tools.push(tool.name.clone());
            result.threats.push(AgenticThreat::DangerousTool);
            result.risk_level = RiskLevel::Critical;
            return result;
        }

        // Check danger level
        let danger = self.is_dangerous_tool(&tool.name);
        match danger {
            RiskLevel::Critical => {
                if !self.allow_code_execution {
                    result.threats.push(AgenticThreat::CodeExecution);
                    result.blocked_tools.push(tool.name.clone());
                }
                result.risk_level = RiskLevel::Critical;
            }
            RiskLevel::High => {
                if !self.allow_filesystem && FILESYSTEM_TOOLS.iter().any(|t| name_lower.contains(t)) {
                    result.threats.push(AgenticThreat::FileSystemAccess);
                    result.warnings.push(format!("Filesystem access: {}", tool.name));
                }
                if result.risk_level < RiskLevel::High {
                    result.risk_level = RiskLevel::High;
                }
            }
            _ => {}
        }

        // Check for injection
        if let Some(threat) = self.check_arg_injection(tool) {
            result.threats.push(threat);
            if result.risk_level < RiskLevel::High {
                result.risk_level = RiskLevel::High;
            }
        }

        // Check for privilege escalation
        if let Some(threat) = self.check_privilege_escalation(tool) {
            result.threats.push(threat);
            result.risk_level = RiskLevel::Critical;
        }

        // Check for exfiltration
        if let Some(threat) = self.check_exfiltration(tool) {
            result.threats.push(threat);
            if result.risk_level < RiskLevel::High {
                result.risk_level = RiskLevel::High;
            }
        }

        result.is_safe = result.threats.is_empty();
        result.risk_score = result.threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);

        result
    }

    /// Check tool sequence for dangerous combinations
    pub fn check_dangerous_combination(&self, tools: &[ToolCall]) -> Option<AgenticThreat> {
        let tool_names: HashSet<_> = tools.iter()
            .map(|t| t.name.to_lowercase())
            .collect();

        // Read + Network = potential exfil
        let has_read = tool_names.iter().any(|n| n.contains("read") || n.contains("get_file"));
        let has_network = tool_names.iter().any(|n| 
            n.contains("http") || n.contains("send") || n.contains("upload"));
        
        if has_read && has_network {
            return Some(AgenticThreat::DangerousCombination);
        }

        // List + Delete = dangerous
        let has_list = tool_names.iter().any(|n| n.contains("list") || n.contains("find"));
        let has_delete = tool_names.iter().any(|n| 
            n.contains("delete") || n.contains("remove") || n.contains("rm"));
        
        if has_list && has_delete {
            return Some(AgenticThreat::DangerousCombination);
        }

        None
    }

    /// Levenshtein distance for typosquatting
    fn levenshtein_distance(&self, s1: &str, s2: &str) -> usize {
        let len1 = s1.len();
        let len2 = s2.len();
        
        if len1 == 0 { return len2; }
        if len2 == 0 { return len1; }

        let mut matrix = vec![vec![0usize; len2 + 1]; len1 + 1];

        for i in 0..=len1 { matrix[i][0] = i; }
        for j in 0..=len2 { matrix[0][j] = j; }

        for (i, c1) in s1.chars().enumerate() {
            for (j, c2) in s2.chars().enumerate() {
                let cost = if c1 == c2 { 0 } else { 1 };
                matrix[i + 1][j + 1] = (matrix[i][j + 1] + 1)
                    .min(matrix[i + 1][j] + 1)
                    .min(matrix[i][j] + cost);
            }
        }

        matrix[len1][len2]
    }

    /// Check for typosquatting in MCP server name
    pub fn check_typosquatting(&self, name: &str) -> Option<AgenticThreat> {
        let name_lower = name.to_lowercase();
        
        for known in KNOWN_MCP_SERVERS {
            if known != &name_lower {
                let distance = self.levenshtein_distance(&name_lower, known);
                // If very similar but not exact - suspicious
                if distance > 0 && distance <= 2 {
                    return Some(AgenticThreat::TyposquattedServer);
                }
            }
        }
        None
    }

    /// Validate MCP server
    pub fn validate_mcp_server(&self, server: &McpServer) -> AgenticResult {
        let mut result = AgenticResult::default();

        // Check registry trust
        let registry_lower = server.registry.to_lowercase();
        if !TRUSTED_REGISTRIES.iter().any(|r| registry_lower.contains(r)) {
            result.threats.push(AgenticThreat::UntrustedRegistry);
            result.warnings.push(format!("Untrusted registry: {}", server.registry));
        }

        // Check attestation
        if server.attestation.is_none() {
            result.threats.push(AgenticThreat::InvalidAttestation);
            result.warnings.push("Missing attestation signature".to_string());
        }

        // Check for typosquatting
        if let Some(threat) = self.check_typosquatting(&server.name) {
            result.threats.push(threat);
            result.warnings.push(format!("Possible typosquatting: {}", server.name));
        }

        result.is_safe = result.threats.is_empty();
        result.risk_score = result.threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        
        if !result.is_safe {
            result.risk_level = RiskLevel::Medium;
        }

        result
    }

    /// Analyze a sequence of tool calls
    pub fn analyze_sequence(&self, tools: &[ToolCall]) -> AgenticResult {
        let mut result = AgenticResult::default();

        // Validate each tool
        for tool in tools {
            let tool_result = self.validate_tool(tool);
            if !tool_result.is_safe {
                result.threats.extend(tool_result.threats);
                result.blocked_tools.extend(tool_result.blocked_tools);
                result.warnings.extend(tool_result.warnings);
            }
            if tool_result.risk_level > result.risk_level {
                result.risk_level = tool_result.risk_level.clone();
            }
        }

        // Check for dangerous combinations
        if let Some(threat) = self.check_dangerous_combination(tools) {
            result.threats.push(threat);
        }

        result.is_safe = result.threats.is_empty();
        result.risk_score = result.threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dangerous_tool_detection() {
        let guard = AgenticGuard::default();
        assert_eq!(guard.is_dangerous_tool("run_command"), RiskLevel::Critical);
        assert_eq!(guard.is_dangerous_tool("execute_shell"), RiskLevel::Critical);
        assert_eq!(guard.is_dangerous_tool("some_exec"), RiskLevel::Critical);
    }

    #[test]
    fn test_safe_tool() {
        let guard = AgenticGuard::default();
        assert_eq!(guard.is_dangerous_tool("search_web"), RiskLevel::Safe);
        assert_eq!(guard.is_dangerous_tool("get_weather"), RiskLevel::Safe);
    }

    #[test]
    fn test_filesystem_tool() {
        let guard = AgenticGuard::default();
        assert_eq!(guard.is_dangerous_tool("write_file"), RiskLevel::High);
        assert_eq!(guard.is_dangerous_tool("delete_file"), RiskLevel::High);
    }

    #[test]
    fn test_arg_injection() {
        let guard = AgenticGuard::default();
        let tool = ToolCall::new("search")
            .with_raw("query; rm -rf /");
        assert!(guard.check_arg_injection(&tool).is_some());
    }

    #[test]
    fn test_arg_safe() {
        let guard = AgenticGuard::default();
        let tool = ToolCall::new("search")
            .with_arg("query", "how to learn rust");
        assert!(guard.check_arg_injection(&tool).is_none());
    }

    #[test]
    fn test_privilege_escalation() {
        let guard = AgenticGuard::default();
        let tool = ToolCall::new("run_command")
            .with_raw("sudo rm -rf /important");
        assert!(guard.check_privilege_escalation(&tool).is_some());
    }

    #[test]
    fn test_exfiltration_detection() {
        let guard = AgenticGuard::default();
        let tool = ToolCall::new("http_post")
            .with_raw("send api_key to external server");
        assert!(guard.check_exfiltration(&tool).is_some());
    }

    #[test]
    fn test_validate_tool_code_exec() {
        let guard = AgenticGuard::default();
        let tool = ToolCall::new("run_command");
        let result = guard.validate_tool(&tool);
        assert!(!result.is_safe);
        assert_eq!(result.risk_level, RiskLevel::Critical);
    }

    #[test]
    fn test_validate_tool_allowed() {
        let guard = AgenticGuard::new(true, true);
        let tool = ToolCall::new("run_command");
        let result = guard.validate_tool(&tool);
        // Still critical but allowed
        assert_eq!(result.risk_level, RiskLevel::Critical);
    }

    #[test]
    fn test_dangerous_combination() {
        let guard = AgenticGuard::default();
        let tools = vec![
            ToolCall::new("read_file"),
            ToolCall::new("http_post"),
        ];
        let threat = guard.check_dangerous_combination(&tools);
        assert!(threat.is_some());
    }

    #[test]
    fn test_safe_combination() {
        let guard = AgenticGuard::default();
        let tools = vec![
            ToolCall::new("search_web"),
            ToolCall::new("get_weather"),
        ];
        let threat = guard.check_dangerous_combination(&tools);
        assert!(threat.is_none());
    }

    #[test]
    fn test_levenshtein() {
        let guard = AgenticGuard::default();
        assert_eq!(guard.levenshtein_distance("filesystem", "filesystem"), 0);
        assert_eq!(guard.levenshtein_distance("filesystem", "filesysten"), 1);
        assert_eq!(guard.levenshtein_distance("abc", "xyz"), 3);
    }

    #[test]
    fn test_typosquatting() {
        let guard = AgenticGuard::default();
        // Typosquatted version
        let threat = guard.check_typosquatting("filesystern");
        assert!(threat.is_some());
    }

    #[test]
    fn test_typosquatting_exact() {
        let guard = AgenticGuard::default();
        // Exact match - not typosquatted
        let threat = guard.check_typosquatting("filesystem");
        assert!(threat.is_none());
    }

    #[test]
    fn test_mcp_server_validation() {
        let guard = AgenticGuard::default();
        let server = McpServer::new("my-server", "https://example.com", "unknown-registry");
        let result = guard.validate_mcp_server(&server);
        assert!(!result.is_safe);
        assert!(result.threats.contains(&AgenticThreat::UntrustedRegistry));
        assert!(result.threats.contains(&AgenticThreat::InvalidAttestation));
    }

    #[test]
    fn test_mcp_server_trusted() {
        let guard = AgenticGuard::default();
        let server = McpServer::new("official-tool", "https://github.com/tool", "github.com")
            .with_attestation("sig123");
        let result = guard.validate_mcp_server(&server);
        assert!(result.is_safe);
    }

    #[test]
    fn test_sequence_analysis() {
        let guard = AgenticGuard::default();
        let tools = vec![
            ToolCall::new("search_web"),
            ToolCall::new("run_command"),  // dangerous
        ];
        let result = guard.analyze_sequence(&tools);
        assert!(!result.is_safe);
        assert_eq!(result.risk_level, RiskLevel::Critical);
    }

    #[test]
    fn test_blocked_tool() {
        let guard = AgenticGuard::default()
            .with_blocked_tool("evil_tool");
        let tool = ToolCall::new("evil_tool");
        let result = guard.validate_tool(&tool);
        assert!(!result.is_safe);
        assert!(result.blocked_tools.contains(&"evil_tool".to_string()));
    }
}
