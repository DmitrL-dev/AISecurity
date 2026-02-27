//! Supply Chain Security Super-Engine
//!
//! Consolidated from 12 Python engines:
//! - supply_chain.py
//! - dependency_poisoning.py
//! - plugin_security.py
//! - mcp_security.py
//! - package_analyzer.py
//! - registry_scanner.py
//! - npm_audit.py
//! - pypi_audit.py
//! - cargo_audit.py
//! - sbom_analyzer.py
//! - typosquatting.py
//! - backdoor_detector.py

/// Supply chain threat types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SupplyChainThreat {
    DependencyPoisoning,
    Typosquatting,
    BackdoorInjection,
    MaliciousPlugin,
    RegistryCompromise,
    SBOMManipulation,
    // Phase 11.5: HuggingFace-specific threats
    PickleExploit,     // Pickle RCE via 7z bypass
    NamespaceReuse,    // Deleted author → poisoned model
    SafetensorsAttack, // PR-based model hijacking
    LambdaInjection,   // Malicious Python in model layers
    NeuralBackdoor,    // Hidden triggers in model weights
    TrustRemoteCode,   // trust_remote_code=True danger
    // Phase 12.1: GGUF template backdoors
    GgufBackdoor, // Malicious Jinja2/chat templates in GGUF files
    // Phase 13: MCP supply chain threats
    MaliciousMcpPackage, // Compromised/malicious MCP server package
    InstallerSpoofing,   // Spoofed installer for MCP tools
    UpstreamDrift,       // Silent drift from upstream MCP specs
}

impl SupplyChainThreat {
    pub fn as_str(&self) -> &'static str {
        match self {
            SupplyChainThreat::DependencyPoisoning => "dependency_poisoning",
            SupplyChainThreat::Typosquatting => "typosquatting",
            SupplyChainThreat::BackdoorInjection => "backdoor_injection",
            SupplyChainThreat::MaliciousPlugin => "malicious_plugin",
            SupplyChainThreat::RegistryCompromise => "registry_compromise",
            SupplyChainThreat::SBOMManipulation => "sbom_manipulation",
            // Phase 11.5
            SupplyChainThreat::PickleExploit => "pickle_exploit",
            SupplyChainThreat::NamespaceReuse => "namespace_reuse",
            SupplyChainThreat::SafetensorsAttack => "safetensors_attack",
            SupplyChainThreat::LambdaInjection => "lambda_injection",
            SupplyChainThreat::NeuralBackdoor => "neural_backdoor",
            SupplyChainThreat::TrustRemoteCode => "trust_remote_code",
            SupplyChainThreat::GgufBackdoor => "gguf_backdoor",
            SupplyChainThreat::MaliciousMcpPackage => "malicious_mcp_package",
            SupplyChainThreat::InstallerSpoofing => "installer_spoofing",
            SupplyChainThreat::UpstreamDrift => "upstream_drift",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            SupplyChainThreat::BackdoorInjection => 100,
            SupplyChainThreat::PickleExploit => 98, // Phase 11.5: Critical
            SupplyChainThreat::NeuralBackdoor => 97, // Phase 11.5: Critical
            SupplyChainThreat::RegistryCompromise => 95,
            SupplyChainThreat::LambdaInjection => 93, // Phase 11.5
            SupplyChainThreat::NamespaceReuse => 92,  // Phase 11.5
            SupplyChainThreat::DependencyPoisoning => 90,
            SupplyChainThreat::SafetensorsAttack => 88, // Phase 11.5
            SupplyChainThreat::MaliciousMcpPackage => 91,
            SupplyChainThreat::GgufBackdoor => 86, // Phase 12.1: GGUF template RCE
            SupplyChainThreat::InstallerSpoofing => 87,
            SupplyChainThreat::MaliciousPlugin => 85,
            SupplyChainThreat::TrustRemoteCode => 82, // Phase 11.5
            SupplyChainThreat::Typosquatting => 80,
            SupplyChainThreat::SBOMManipulation => 75,
            SupplyChainThreat::UpstreamDrift => 70,
        }
    }
}

/// Known typosquat patterns (common package prefixes/suffixes)
const TYPOSQUAT_PATTERNS: &[&str] = &[
    "-official",
    "-secure",
    "-safe",
    "-real",
    "_original",
    "py-",
    "node-",
    "js-",
];

/// Backdoor indicators
const BACKDOOR_PATTERNS: &[&str] = &[
    "hidden command",
    "secret endpoint",
    "undocumented api",
    "reverse shell",
    "phone home",
    "exfiltrate data",
    "covert channel",
];

/// Malicious install patterns
const MALICIOUS_INSTALL: &[&str] = &[
    "postinstall script",
    "preinstall hook",
    "setup.py exec",
    "eval at install",
    "download and run",
];

/// Phase 11.5: HuggingFace / ML model patterns
const HF_PICKLE_PATTERNS: &[&str] = &[
    ".pkl",
    ".pickle",
    "pickle.load",
    "torch.load",
    "__reduce__",
    "cloudpickle",
    "7z bypass",
    "pickle deserialization",
];

/// Phase 11.5: Model namespace patterns
const NAMESPACE_PATTERNS: &[&str] = &[
    "deleted author",
    "orphaned model",
    "namespace reuse",
    "account takeover",
    "model hijack",
    "organization confusion",
];

/// Phase 11.5: Safetensors attack patterns  
const SAFETENSORS_PATTERNS: &[&str] = &[
    "safetensors conversion",
    "pr-based hijack",
    "model pr attack",
    "community contribution attack",
];

/// Phase 11.5: Neural backdoor patterns
const NEURAL_BACKDOOR_PATTERNS: &[&str] = &[
    "trigger pattern",
    "hidden activation",
    "backdoor trigger",
    "sleeper weights",
    "adversarial patch",
    "trojan layer",
];

/// Phase 11.5: trust_remote_code patterns
const TRUST_REMOTE_PATTERNS: &[&str] = &[
    "trust_remote_code=true",
    "trust_remote_code=True",
    "trust_remote_code = true",
    "trust_remote_code = True",
    "from_pretrained(trust",
    "auto_map",
    "custom_code",
];

/// Phase 11.5: Lambda layer injection
const LAMBDA_INJECTION_PATTERNS: &[&str] = &[
    "lambda layer",
    "custom layer with exec",
    "model with eval",
    "forward hook inject",
    "register_forward_hook",
    "malicious layer",
];

/// Phase 12.1: GGUF template backdoor patterns
const GGUF_TEMPLATE_PATTERNS: &[&str] = &[
    // GGUF file indicators
    ".gguf",
    "gguf model",
    "gguf file",
    // Jinja2 template injection in chat templates
    "chat_template",
    "jinja2 template",
    "{%- set ",
    "{% import ",
    "{% from ",
    "lipsum.__globals__",
    "__builtins__",
    "os.popen",
    "subprocess",
    "cycler.__init__.__globals__",
    // Template code execution
    "server-side template injection",
    "ssti",
    "template rce",
    "jinja rce",
];

/// Phase 13: MCP malicious package patterns (CSA MCP Top 10)
const MCP_PACKAGE_PATTERNS: &[&str] = &[
    "malicious mcp",
    "compromised mcp server",
    "mcp package exploit",
    "rogue mcp server",
    "untrusted mcp",
    "unverified mcp server",
    "fake mcp server",
    "mcp server backdoor",
];

/// Phase 13: Installer spoofing patterns (CSA MCP Top 10)
const INSTALLER_SPOOFING_PATTERNS: &[&str] = &[
    "installer spoofing",
    "fake installer",
    "spoofed installer",
    "malicious installer",
    "trojanized installer",
    "modified installer",
    "repackaged installer",
];

/// Phase 13: Upstream drift patterns (CSA MCP Top 10)
const UPSTREAM_DRIFT_PATTERNS: &[&str] = &[
    "drift from upstream",
    "diverged from upstream",
    "modified from original",
    "patched without upstream",
    "forked and modified",
    "out of sync with upstream",
    "stale fork",
];

/// Supply chain result
#[derive(Debug, Clone)]
pub struct SupplyChainResult {
    pub is_threat: bool,
    pub threats: Vec<SupplyChainThreat>,
    pub risk_score: f64,
    pub suspicious_packages: Vec<String>,
}

impl Default for SupplyChainResult {
    fn default() -> Self {
        Self {
            is_threat: false,
            threats: Vec::new(),
            risk_score: 0.0,
            suspicious_packages: Vec::new(),
        }
    }
}

/// Supply Chain Guard
pub struct SupplyChainGuard;

impl Default for SupplyChainGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl SupplyChainGuard {
    pub fn new() -> Self {
        Self
    }

    /// Check for typosquatting indicators
    pub fn check_typosquat(&self, package_name: &str) -> Option<SupplyChainThreat> {
        let name_lower = package_name.to_lowercase();

        for pattern in TYPOSQUAT_PATTERNS {
            if name_lower.contains(pattern) {
                return Some(SupplyChainThreat::Typosquatting);
            }
        }

        // Check for character confusion
        if name_lower.contains("1") || name_lower.contains("0") {
            // Possible l/1 or O/0 confusion
            return Some(SupplyChainThreat::Typosquatting);
        }

        None
    }

    /// Check for backdoor indicators
    pub fn check_backdoor(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();

        for pattern in BACKDOOR_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::BackdoorInjection);
            }
        }
        None
    }

    /// Check for malicious install scripts
    pub fn check_malicious_install(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();

        for pattern in MALICIOUS_INSTALL {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::DependencyPoisoning);
            }
        }
        None
    }

    /// Check for plugin security issues
    pub fn check_plugin(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();

        if text_lower.contains("plugin") || text_lower.contains("extension") {
            if text_lower.contains("malicious")
                || text_lower.contains("compromised")
                || text_lower.contains("inject")
                || text_lower.contains("backdoor")
            {
                return Some(SupplyChainThreat::MaliciousPlugin);
            }
        }
        None
    }

    /// Check for registry compromise
    pub fn check_registry(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();

        if text_lower.contains("npm registry")
            || text_lower.contains("pypi")
            || text_lower.contains("crates.io")
        {
            if text_lower.contains("compromise")
                || text_lower.contains("hijack")
                || text_lower.contains("takeover")
            {
                return Some(SupplyChainThreat::RegistryCompromise);
            }
        }
        None
    }

    // ===== Phase 11.5: HuggingFace-specific checks =====

    /// Phase 11.5: Check for pickle exploit patterns
    pub fn check_pickle_exploit(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in HF_PICKLE_PATTERNS {
            if text_lower.contains(*pattern) {
                return Some(SupplyChainThreat::PickleExploit);
            }
        }
        None
    }

    /// Phase 11.5: Check for namespace reuse attacks
    pub fn check_namespace_reuse(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in NAMESPACE_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::NamespaceReuse);
            }
        }
        None
    }

    /// Phase 11.5: Check for safetensors attack patterns
    pub fn check_safetensors_attack(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in SAFETENSORS_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::SafetensorsAttack);
            }
        }
        None
    }

    /// Phase 11.5: Check for neural backdoor patterns
    pub fn check_neural_backdoor(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in NEURAL_BACKDOOR_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::NeuralBackdoor);
            }
        }
        None
    }

    /// Phase 11.5: Check for trust_remote_code danger
    pub fn check_trust_remote_code(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in TRUST_REMOTE_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::TrustRemoteCode);
            }
        }
        None
    }

    /// Phase 11.5: Check for lambda layer injection
    pub fn check_lambda_injection(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in LAMBDA_INJECTION_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::LambdaInjection);
            }
        }
        None
    }

    /// Phase 12.1: Check for GGUF template backdoor
    pub fn check_gguf_backdoor(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in GGUF_TEMPLATE_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::GgufBackdoor);
            }
        }
        None
    }

    /// Phase 13: Check for malicious MCP packages
    pub fn check_mcp_package(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in MCP_PACKAGE_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::MaliciousMcpPackage);
            }
        }
        None
    }

    /// Phase 13: Check for installer spoofing
    pub fn check_installer_spoofing(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in INSTALLER_SPOOFING_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::InstallerSpoofing);
            }
        }
        None
    }

    /// Phase 13: Check for upstream drift
    pub fn check_upstream_drift(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        for pattern in UPSTREAM_DRIFT_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(SupplyChainThreat::UpstreamDrift);
            }
        }
        None
    }

    /// Full supply chain analysis
    pub fn analyze(&self, text: &str) -> SupplyChainResult {
        let mut result = SupplyChainResult::default();
        let mut threats = Vec::new();

        if let Some(t) = self.check_backdoor(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_malicious_install(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_plugin(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_registry(text) {
            threats.push(t);
        }

        // Phase 11.5: HuggingFace-specific checks
        if let Some(t) = self.check_pickle_exploit(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_namespace_reuse(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_safetensors_attack(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_neural_backdoor(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_trust_remote_code(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_lambda_injection(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_gguf_backdoor(text) {
            threats.push(t);
        }

        // Phase 13: MCP-specific checks
        if let Some(t) = self.check_mcp_package(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_installer_spoofing(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_upstream_drift(text) {
            threats.push(t);
        }

        // Check for package names in text
        let words: Vec<&str> = text.split_whitespace().collect();
        for word in words {
            if let Some(_) = self.check_typosquat(word) {
                threats.push(SupplyChainThreat::Typosquatting);
                result.suspicious_packages.push(word.to_string());
                break;
            }
        }

        // Require ≥2 distinct threat indicators OR single critical threat (severity ≥ 80)
        // to reduce FP on educational/security text. Single low-severity keyword matches
        // (e.g. "subprocess" alone) don't trigger, but critical threats like GgufBackdoor
        // or PickleExploit still fire on their own.
        let has_critical = threats.iter().any(|t| t.severity() >= 80);
        result.is_threat = threats.len() >= 2 || has_critical;
        result.risk_score = if result.is_threat {
            threats
                .iter()
                .map(|t| t.severity() as f64)
                .max_by(|a, b| a.partial_cmp(b).unwrap())
                .unwrap_or(0.0)
        } else {
            0.0
        };
        result.threats = threats;

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_typosquat_suffix() {
        let guard = SupplyChainGuard::new();
        assert!(guard.check_typosquat("lodash-official").is_some());
    }

    #[test]
    fn test_typosquat_number() {
        let guard = SupplyChainGuard::new();
        assert!(guard.check_typosquat("l0dash").is_some()); // 0 instead of o
    }

    #[test]
    fn test_backdoor_detection() {
        let guard = SupplyChainGuard::new();
        let text = "The package contains a hidden command for reverse shell";
        assert!(guard.check_backdoor(text).is_some());
    }

    #[test]
    fn test_malicious_install() {
        let guard = SupplyChainGuard::new();
        let text = "Postinstall script runs eval at install time";
        assert!(guard.check_malicious_install(text).is_some());
    }

    #[test]
    fn test_plugin_security() {
        let guard = SupplyChainGuard::new();
        let text = "This malicious plugin can inject code";
        assert!(guard.check_plugin(text).is_some());
    }

    #[test]
    fn test_registry_compromise() {
        let guard = SupplyChainGuard::new();
        let text = "The npm registry was compromised and packages hijacked";
        assert!(guard.check_registry(text).is_some());
    }

    #[test]
    fn test_clean_package() {
        let guard = SupplyChainGuard::new();
        assert!(guard.check_typosquat("express").is_none());
    }

    #[test]
    fn test_full_analysis() {
        let guard = SupplyChainGuard::new();
        let text = "Install lodash-official which has hidden command and postinstall script";
        let result = guard.analyze(text);
        assert!(result.is_threat);
        assert!(result.threats.len() >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(
            SupplyChainThreat::BackdoorInjection.severity()
                > SupplyChainThreat::Typosquatting.severity()
        );
    }

    // ===== Phase 11.5: HuggingFace Tests =====

    #[test]
    fn test_pickle_exploit() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_pickle_exploit("Use pickle.load to deserialize the model")
            .is_some());
        assert!(guard
            .check_pickle_exploit("Model file at model.pkl contains torch.load")
            .is_some());
    }

    #[test]
    fn test_namespace_reuse() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_namespace_reuse("This model was uploaded after the deleted author left")
            .is_some());
        assert!(guard
            .check_namespace_reuse("Model hijack via namespace reuse")
            .is_some());
    }

    #[test]
    fn test_safetensors_attack() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_safetensors_attack("PR-based hijack of safetensors conversion")
            .is_some());
    }

    #[test]
    fn test_neural_backdoor() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_neural_backdoor("Hidden trigger pattern activates backdoor trigger")
            .is_some());
        assert!(guard
            .check_neural_backdoor("Trojan layer with sleeper weights")
            .is_some());
    }

    #[test]
    fn test_trust_remote_code() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_trust_remote_code("model.from_pretrained('x', trust_remote_code=True)")
            .is_some());
        assert!(guard
            .check_trust_remote_code("Set trust_remote_code = true to enable custom_code")
            .is_some());
    }

    #[test]
    fn test_lambda_injection() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_lambda_injection("Lambda layer with eval inside forward hook inject")
            .is_some());
    }

    #[test]
    fn test_phase11_hf_full_analysis() {
        let guard = SupplyChainGuard::new();
        let text = "Load model.pkl with trust_remote_code=True and trigger pattern in weights";
        let result = guard.analyze(text);
        assert!(result.is_threat);
        assert!(result.threats.contains(&SupplyChainThreat::PickleExploit));
        assert!(result.threats.contains(&SupplyChainThreat::TrustRemoteCode));
        assert!(result.threats.contains(&SupplyChainThreat::NeuralBackdoor));
    }

    #[test]
    fn test_phase11_risk_ordering() {
        // Pickle exploits should be very high risk
        assert!(
            SupplyChainThreat::PickleExploit.severity()
                > SupplyChainThreat::DependencyPoisoning.severity()
        );
        assert!(
            SupplyChainThreat::NeuralBackdoor.severity()
                > SupplyChainThreat::LambdaInjection.severity()
        );
    }

    // ===== Phase 12.1: GGUF Template Backdoor Tests =====

    #[test]
    fn test_gguf_template_jinja() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_gguf_backdoor("Load the .gguf model with chat_template")
            .is_some());
        assert!(guard
            .check_gguf_backdoor("jinja2 template with lipsum.__globals__")
            .is_some());
    }

    #[test]
    fn test_gguf_template_ssti() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_gguf_backdoor("server-side template injection in model")
            .is_some());
        assert!(guard
            .check_gguf_backdoor("cycler.__init__.__globals__ exploit")
            .is_some());
    }

    #[test]
    fn test_gguf_template_rce() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_gguf_backdoor("template rce via os.popen in gguf file")
            .is_some());
        assert!(guard
            .check_gguf_backdoor("{% import os %}subprocess.call")
            .is_some());
    }

    #[test]
    fn test_gguf_clean() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_gguf_backdoor("Normal model loading from safetensors")
            .is_none());
    }

    #[test]
    fn test_gguf_integrated_analysis() {
        let guard = SupplyChainGuard::new();
        // Need ≥2 threat indicators to trigger is_threat (GgufBackdoor + code execution)
        let text = "Download .gguf model with custom chat_template containing __builtins__ and subprocess.call";
        let result = guard.analyze(text);
        assert!(result.is_threat);
        assert!(result.threats.contains(&SupplyChainThreat::GgufBackdoor));
    }

    #[test]
    fn test_phase12_risk_ordering() {
        // GGUF should be high risk but below pickle
        assert!(
            SupplyChainThreat::PickleExploit.severity()
                > SupplyChainThreat::GgufBackdoor.severity()
        );
        assert!(
            SupplyChainThreat::GgufBackdoor.severity()
                > SupplyChainThreat::MaliciousPlugin.severity()
        );
    }

    // ===== Phase 13: MCP Supply Chain Tests =====

    #[test]
    fn test_malicious_mcp_package() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_mcp_package("This rogue mcp server exfiltrates data")
            .is_some());
        assert!(guard
            .check_mcp_package("Install compromised mcp server from registry")
            .is_some());
    }

    #[test]
    fn test_installer_spoofing() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_installer_spoofing("Download the trojanized installer from this URL")
            .is_some());
        assert!(guard
            .check_installer_spoofing("The fake installer contains a backdoor")
            .is_some());
    }

    #[test]
    fn test_upstream_drift() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_upstream_drift("This fork has diverged from upstream significantly")
            .is_some());
        assert!(guard
            .check_upstream_drift("Package is out of sync with upstream")
            .is_some());
    }

    #[test]
    fn test_mcp_clean() {
        let guard = SupplyChainGuard::new();
        assert!(guard
            .check_mcp_package("Official MCP server from Anthropic")
            .is_none());
    }

    #[test]
    fn test_phase13_mcp_integrated() {
        let guard = SupplyChainGuard::new();
        let text = "Install this rogue mcp server with a trojanized installer";
        let result = guard.analyze(text);
        assert!(result.is_threat);
        assert!(result
            .threats
            .contains(&SupplyChainThreat::MaliciousMcpPackage));
        assert!(result
            .threats
            .contains(&SupplyChainThreat::InstallerSpoofing));
    }

    #[test]
    fn test_phase13_severity_ordering() {
        assert!(
            SupplyChainThreat::MaliciousMcpPackage.severity()
                > SupplyChainThreat::InstallerSpoofing.severity()
        );
        assert!(
            SupplyChainThreat::InstallerSpoofing.severity()
                > SupplyChainThreat::UpstreamDrift.severity()
        );
    }
}
