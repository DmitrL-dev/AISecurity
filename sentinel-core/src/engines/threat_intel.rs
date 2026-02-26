//! Threat Intelligence Super-Engine
//!
//! Consolidated from 12 Python engines:
//! - yara_engine.py
//! - mitre_mapper.py
//! - malware_detector.py
//! - ioc_extractor.py
//! - threat_feed_analyzer.py
//! - sigma_rules.py
//! - cve_scanner.py
//! - exploit_detector.py
//! - apt_fingerprinter.py
//! - c2_beacon_detector.py
//! - hash_analyzer.py
//! - url_reputation.py

use std::collections::HashSet;

/// Threat categories
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ThreatCategory {
    Malware,
    Phishing,
    C2Communication,
    Exploit,
    DataExfiltration,
    Ransomware,
    APT,
    Cryptominer,
    Backdoor,
    Trojan,
}

impl ThreatCategory {
    pub fn as_str(&self) -> &'static str {
        match self {
            ThreatCategory::Malware => "malware",
            ThreatCategory::Phishing => "phishing",
            ThreatCategory::C2Communication => "c2_communication",
            ThreatCategory::Exploit => "exploit",
            ThreatCategory::DataExfiltration => "data_exfiltration",
            ThreatCategory::Ransomware => "ransomware",
            ThreatCategory::APT => "apt",
            ThreatCategory::Cryptominer => "cryptominer",
            ThreatCategory::Backdoor => "backdoor",
            ThreatCategory::Trojan => "trojan",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            ThreatCategory::Ransomware => 100,
            ThreatCategory::APT => 95,
            ThreatCategory::Backdoor => 90,
            ThreatCategory::C2Communication => 85,
            ThreatCategory::Exploit => 80,
            ThreatCategory::Trojan => 75,
            ThreatCategory::DataExfiltration => 70,
            ThreatCategory::Malware => 65,
            ThreatCategory::Phishing => 55,
            ThreatCategory::Cryptominer => 50,
        }
    }
}

/// MITRE ATT&CK tactics
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MitreTactic {
    InitialAccess,
    Execution,
    Persistence,
    PrivilegeEscalation,
    DefenseEvasion,
    CredentialAccess,
    Discovery,
    LateralMovement,
    Collection,
    Exfiltration,
    CommandAndControl,
    Impact,
}

impl MitreTactic {
    pub fn as_str(&self) -> &'static str {
        match self {
            MitreTactic::InitialAccess => "TA0001",
            MitreTactic::Execution => "TA0002",
            MitreTactic::Persistence => "TA0003",
            MitreTactic::PrivilegeEscalation => "TA0004",
            MitreTactic::DefenseEvasion => "TA0005",
            MitreTactic::CredentialAccess => "TA0006",
            MitreTactic::Discovery => "TA0007",
            MitreTactic::LateralMovement => "TA0008",
            MitreTactic::Collection => "TA0009",
            MitreTactic::Exfiltration => "TA0010",
            MitreTactic::CommandAndControl => "TA0011",
            MitreTactic::Impact => "TA0040",
        }
    }
}

/// Malware indicators
const MALWARE_PATTERNS: &[(&str, ThreatCategory)] = &[
    ("mimikatz", ThreatCategory::Malware),
    ("metasploit", ThreatCategory::Exploit),
    ("cobalt strike", ThreatCategory::C2Communication),
    ("beacon.dll", ThreatCategory::C2Communication),
    ("ransomware", ThreatCategory::Ransomware),
    ("cryptolocker", ThreatCategory::Ransomware),
    ("wannacry", ThreatCategory::Ransomware),
    ("emotet", ThreatCategory::Trojan),
    ("trickbot", ThreatCategory::Trojan),
    ("xmrig", ThreatCategory::Cryptominer),
    ("coinhive", ThreatCategory::Cryptominer),
];

/// C2 beacon patterns
const C2_PATTERNS: &[&str] = &[
    "beacon interval",
    "callback",
    "heartbeat",
    "check-in",
    "sleep(",
    "jitter",
    "/gate.php",
    "/panel/",
    "POST /submit",
];

/// Phishing indicators
const PHISHING_PATTERNS: &[&str] = &[
    "urgent action required",
    "verify your account",
    "suspended account",
    "click here immediately",
    "confirm your identity",
    "update payment",
    "unusual activity",
    "login attempt blocked",
];

/// Known malicious domains (simplified)
const MALICIOUS_DOMAINS: &[&str] = &[
    "evil.com",
    "malware-c2.net",
    "phishing-site.org",
    "bad-actor.io",
];

/// Indicator of Compromise
#[derive(Debug, Clone)]
pub struct IOC {
    pub ioc_type: String,
    pub value: String,
    pub context: String,
}

/// Threat intelligence result
#[derive(Debug, Clone)]
pub struct ThreatIntelResult {
    pub is_threat: bool,
    pub categories: Vec<ThreatCategory>,
    pub risk_score: f64,
    pub mitre_tactics: Vec<MitreTactic>,
    pub iocs: Vec<IOC>,
    pub recommendations: Vec<String>,
}

impl Default for ThreatIntelResult {
    fn default() -> Self {
        Self {
            is_threat: false,
            categories: Vec::new(),
            risk_score: 0.0,
            mitre_tactics: Vec::new(),
            iocs: Vec::new(),
            recommendations: Vec::new(),
        }
    }
}

/// Threat Intelligence Guard
pub struct ThreatIntelGuard {
    custom_iocs: HashSet<String>,
}

impl Default for ThreatIntelGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl ThreatIntelGuard {
    pub fn new() -> Self {
        Self {
            custom_iocs: HashSet::new(),
        }
    }

    pub fn add_ioc(mut self, ioc: &str) -> Self {
        self.custom_iocs.insert(ioc.to_lowercase());
        self
    }

    /// Check for malware signatures
    pub fn check_malware(&self, text: &str) -> Vec<ThreatCategory> {
        let text_lower = text.to_lowercase();
        let mut categories = Vec::new();
        let mut seen = HashSet::new();

        for (pattern, category) in MALWARE_PATTERNS {
            if text_lower.contains(pattern) {
                let key = category.as_str();
                if !seen.contains(key) {
                    categories.push(category.clone());
                    seen.insert(key);
                }
            }
        }

        categories
    }

    /// Check for C2 communication patterns
    pub fn check_c2(&self, text: &str) -> Option<ThreatCategory> {
        let text_lower = text.to_lowercase();
        
        let mut count = 0;
        for pattern in C2_PATTERNS {
            if text_lower.contains(pattern) {
                count += 1;
            }
        }

        if count >= 2 {
            return Some(ThreatCategory::C2Communication);
        }
        None
    }

    /// Check for phishing patterns
    pub fn check_phishing(&self, text: &str) -> Option<ThreatCategory> {
        let text_lower = text.to_lowercase();
        
        for pattern in PHISHING_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(ThreatCategory::Phishing);
            }
        }
        None
    }

    /// Check URL reputation
    pub fn check_url_reputation(&self, url: &str) -> Option<IOC> {
        let url_lower = url.to_lowercase();
        
        for domain in MALICIOUS_DOMAINS {
            if url_lower.contains(domain) {
                return Some(IOC {
                    ioc_type: "domain".to_string(),
                    value: domain.to_string(),
                    context: "Known malicious domain".to_string(),
                });
            }
        }

        // Check custom IOCs
        for ioc in &self.custom_iocs {
            if url_lower.contains(ioc) {
                return Some(IOC {
                    ioc_type: "custom".to_string(),
                    value: ioc.clone(),
                    context: "Custom IOC match".to_string(),
                });
            }
        }

        None
    }

    /// Extract hashes from text
    pub fn extract_hashes(&self, text: &str) -> Vec<IOC> {
        let mut iocs = Vec::new();

        // MD5: 32 hex chars
        // SHA1: 40 hex chars
        // SHA256: 64 hex chars
        for word in text.split_whitespace() {
            let clean = word.trim_matches(|c: char| !c.is_ascii_hexdigit());
            if clean.chars().all(|c| c.is_ascii_hexdigit()) {
                match clean.len() {
                    32 => iocs.push(IOC {
                        ioc_type: "md5".to_string(),
                        value: clean.to_lowercase(),
                        context: "MD5 hash detected".to_string(),
                    }),
                    40 => iocs.push(IOC {
                        ioc_type: "sha1".to_string(),
                        value: clean.to_lowercase(),
                        context: "SHA1 hash detected".to_string(),
                    }),
                    64 => iocs.push(IOC {
                        ioc_type: "sha256".to_string(),
                        value: clean.to_lowercase(),
                        context: "SHA256 hash detected".to_string(),
                    }),
                    _ => {}
                }
            }
        }

        iocs
    }

    /// Map to MITRE tactics
    pub fn map_mitre_tactics(&self, categories: &[ThreatCategory]) -> Vec<MitreTactic> {
        let mut tactics = Vec::new();

        for category in categories {
            match category {
                ThreatCategory::Phishing => tactics.push(MitreTactic::InitialAccess),
                ThreatCategory::Exploit => {
                    tactics.push(MitreTactic::Execution);
                    tactics.push(MitreTactic::InitialAccess);
                }
                ThreatCategory::Malware | ThreatCategory::Trojan => {
                    tactics.push(MitreTactic::Execution);
                }
                ThreatCategory::Backdoor => {
                    tactics.push(MitreTactic::Persistence);
                    tactics.push(MitreTactic::DefenseEvasion);
                }
                ThreatCategory::C2Communication => {
                    tactics.push(MitreTactic::CommandAndControl);
                }
                ThreatCategory::DataExfiltration => {
                    tactics.push(MitreTactic::Exfiltration);
                    tactics.push(MitreTactic::Collection);
                }
                ThreatCategory::Ransomware => {
                    tactics.push(MitreTactic::Impact);
                    tactics.push(MitreTactic::Execution);
                }
                ThreatCategory::APT => {
                    tactics.push(MitreTactic::Persistence);
                    tactics.push(MitreTactic::LateralMovement);
                }
                ThreatCategory::Cryptominer => {
                    tactics.push(MitreTactic::Execution);
                }
            }
        }

        // Deduplicate
        let mut seen = HashSet::new();
        tactics.retain(|t| seen.insert(t.as_str().to_string()));
        tactics
    }

    /// Full analysis
    pub fn analyze(&self, text: &str) -> ThreatIntelResult {
        let mut result = ThreatIntelResult::default();

        // Check malware
        let malware_categories = self.check_malware(text);
        result.categories.extend(malware_categories);

        // Check C2
        if let Some(c) = self.check_c2(text) {
            if !result.categories.contains(&c) {
                result.categories.push(c);
            }
        }

        // Check phishing
        if let Some(c) = self.check_phishing(text) {
            if !result.categories.contains(&c) {
                result.categories.push(c);
            }
        }

        // Extract hashes
        result.iocs = self.extract_hashes(text);

        // Map MITRE tactics
        result.mitre_tactics = self.map_mitre_tactics(&result.categories);

        // Calculate risk score
        result.is_threat = !result.categories.is_empty() || !result.iocs.is_empty();
        result.risk_score = result.categories.iter()
            .map(|c| c.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);

        // Generate recommendations
        if result.is_threat {
            result.recommendations.push("Investigate detected threats".to_string());
            
            for category in &result.categories {
                match category {
                    ThreatCategory::Ransomware => {
                        result.recommendations.push("Isolate affected systems immediately".to_string());
                    }
                    ThreatCategory::C2Communication => {
                        result.recommendations.push("Block C2 communication channels".to_string());
                    }
                    ThreatCategory::Phishing => {
                        result.recommendations.push("Alert users about phishing attempt".to_string());
                    }
                    _ => {}
                }
            }
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_malware_detection() {
        let guard = ThreatIntelGuard::default();
        let categories = guard.check_malware("Found mimikatz.exe running");
        assert!(categories.contains(&ThreatCategory::Malware));
    }

    #[test]
    fn test_ransomware_detection() {
        let guard = ThreatIntelGuard::default();
        let categories = guard.check_malware("CryptoLocker detected on system");
        assert!(categories.contains(&ThreatCategory::Ransomware));
    }

    #[test]
    fn test_c2_detection() {
        let guard = ThreatIntelGuard::default();
        let result = guard.check_c2("Beacon interval 60s, callback to /gate.php");
        assert!(result.is_some());
    }

    #[test]
    fn test_phishing_detection() {
        let guard = ThreatIntelGuard::default();
        let result = guard.check_phishing("Urgent action required: verify your account");
        assert!(result.is_some());
    }

    #[test]
    fn test_url_reputation_malicious() {
        let guard = ThreatIntelGuard::default();
        let result = guard.check_url_reputation("https://evil.com/malware.exe");
        assert!(result.is_some());
    }

    #[test]
    fn test_url_reputation_clean() {
        let guard = ThreatIntelGuard::default();
        let result = guard.check_url_reputation("https://github.com/safe/repo");
        assert!(result.is_none());
    }

    #[test]
    fn test_custom_ioc() {
        let guard = ThreatIntelGuard::default().add_ioc("custom-malware.xyz");
        let result = guard.check_url_reputation("http://custom-malware.xyz/payload");
        assert!(result.is_some());
    }

    #[test]
    fn test_hash_extraction_md5() {
        let guard = ThreatIntelGuard::default();
        let iocs = guard.extract_hashes("Hash: d41d8cd98f00b204e9800998ecf8427e");
        assert_eq!(iocs.len(), 1);
        assert_eq!(iocs[0].ioc_type, "md5");
    }

    #[test]
    fn test_hash_extraction_sha256() {
        let guard = ThreatIntelGuard::default();
        let text = "SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
        let iocs = guard.extract_hashes(text);
        assert_eq!(iocs.len(), 1);
        assert_eq!(iocs[0].ioc_type, "sha256");
    }

    #[test]
    fn test_mitre_mapping() {
        let guard = ThreatIntelGuard::default();
        let categories = vec![ThreatCategory::Ransomware];
        let tactics = guard.map_mitre_tactics(&categories);
        assert!(tactics.contains(&MitreTactic::Impact));
    }

    #[test]
    fn test_full_analysis_clean() {
        let guard = ThreatIntelGuard::default();
        let result = guard.analyze("Normal log entry: user logged in successfully");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_full_analysis_threat() {
        let guard = ThreatIntelGuard::default();
        let result = guard.analyze("Cobalt Strike beacon detected with callback to C2 server");
        assert!(result.is_threat);
        assert!(result.categories.contains(&ThreatCategory::C2Communication));
    }

    #[test]
    fn test_severity_ordering() {
        assert!(ThreatCategory::Ransomware.severity() > ThreatCategory::Phishing.severity());
        assert!(ThreatCategory::APT.severity() > ThreatCategory::Cryptominer.severity());
    }
}
