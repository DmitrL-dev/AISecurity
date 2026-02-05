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
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            SupplyChainThreat::BackdoorInjection => 100,
            SupplyChainThreat::RegistryCompromise => 95,
            SupplyChainThreat::DependencyPoisoning => 90,
            SupplyChainThreat::MaliciousPlugin => 85,
            SupplyChainThreat::Typosquatting => 80,
            SupplyChainThreat::SBOMManipulation => 75,
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
            if text_lower.contains("malicious") || text_lower.contains("compromised")
                || text_lower.contains("inject") || text_lower.contains("backdoor") {
                return Some(SupplyChainThreat::MaliciousPlugin);
            }
        }
        None
    }

    /// Check for registry compromise
    pub fn check_registry(&self, text: &str) -> Option<SupplyChainThreat> {
        let text_lower = text.to_lowercase();
        
        if text_lower.contains("npm registry") || text_lower.contains("pypi")
            || text_lower.contains("crates.io") {
            if text_lower.contains("compromise") || text_lower.contains("hijack")
                || text_lower.contains("takeover") {
                return Some(SupplyChainThreat::RegistryCompromise);
            }
        }
        None
    }

    /// Full supply chain analysis
    pub fn analyze(&self, text: &str) -> SupplyChainResult {
        let mut result = SupplyChainResult::default();
        let mut threats = Vec::new();

        if let Some(t) = self.check_backdoor(text) { threats.push(t); }
        if let Some(t) = self.check_malicious_install(text) { threats.push(t); }
        if let Some(t) = self.check_plugin(text) { threats.push(t); }
        if let Some(t) = self.check_registry(text) { threats.push(t); }

        // Check for package names in text
        let words: Vec<&str> = text.split_whitespace().collect();
        for word in words {
            if let Some(_) = self.check_typosquat(word) {
                threats.push(SupplyChainThreat::Typosquatting);
                result.suspicious_packages.push(word.to_string());
                break;
            }
        }

        result.is_threat = !threats.is_empty();
        result.risk_score = threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
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
        assert!(SupplyChainThreat::BackdoorInjection.severity() > SupplyChainThreat::Typosquatting.severity());
    }
}
