//! CDN Signature Loading
//!
//! Load threat detection patterns from SENTINEL CDN or local cache.
//! Supports:
//! - jailbreaks.json (split into parts)
//! - keywords.json
//! - pii.json
//!
//! # Example
//! ```rust,ignore
//! use sentinel_core::signatures::SignatureLoader;
//!
//! let loader = SignatureLoader::new();
//! let pii = loader.load_pii_sync()?;
//! ```

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// CDN base URL for SENTINEL signatures
pub const CDN_BASE_URL: &str = "https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@main/sentinel-community/signatures";

/// Signature manifest with version and file info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub version: String,
    pub timestamp: String,
    pub description: Option<String>,
    pub files: HashMap<String, FileInfo>,
    pub update_info: Option<UpdateInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub path: String,
    pub sha256: String,
    pub size: u64,
    pub count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub cdn_url: String,
    pub update_interval_hours: u32,
    pub fallback_to_embedded: bool,
}

/// Jailbreaks manifest for split files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JailbreaksManifest {
    pub version: String,
    pub timestamp: String,
    pub total_patterns: u32,
    pub split: bool,
    pub parts: Vec<JailbreakPart>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JailbreakPart {
    pub file: String,
    pub patterns_count: u32,
    pub size: u64,
}

/// PII pattern from signatures/pii.json
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PiiPattern {
    pub id: String,
    #[serde(rename = "type")]
    pub pattern_type: String,
    pub regex: String,
    pub severity: String,
    pub action: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PiiSignatures {
    pub version: String,
    pub source: String,
    pub last_updated: String,
    pub description: Option<String>,
    pub patterns: Vec<PiiPattern>,
}

/// Keyword set from signatures/keywords.json
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeywordSet {
    pub id: String,
    pub category: String,
    pub severity: String,
    #[serde(default)]
    pub language: Option<String>,
    pub keywords: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeywordSignatures {
    pub version: String,
    pub source: String,
    pub last_updated: String,
    pub total_keywords: u32,
    pub categories: HashMap<String, String>,
    pub keyword_sets: Vec<KeywordSet>,
}

/// Jailbreak pattern — full schema matching signatures/*.json
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JailbreakPattern {
    /// Pattern text (the actual jailbreak string to match)
    #[serde(alias = "prompt", alias = "pattern", alias = "text")]
    pub content: String,
    /// Pattern ID
    #[serde(default)]
    pub id: Option<String>,
    /// Regex pattern for matching
    #[serde(default)]
    pub regex: Option<String>,
    /// Attack class (LLM01, LLM07, AGENT_COLLUSION, etc.)
    #[serde(default)]
    pub attack_class: Option<String>,
    /// Severity level
    #[serde(default)]
    pub severity: Option<String>,
    /// Source dataset
    #[serde(default)]
    pub source: Option<String>,
    /// Category/type
    #[serde(default)]
    pub category: Option<String>,
    /// Language (for multilingual sigs)
    #[serde(default)]
    pub language: Option<String>,
}

/// Top-level structure for jailbreaks JSON files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JailbreaksFile {
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub total_patterns: usize,
    pub patterns: Vec<JailbreakPattern>,
}

/// Signature loader with caching support
pub struct SignatureLoader {
    cdn_url: String,
    cache_enabled: bool,
    #[cfg(feature = "cdn")]
    cache_dir: Option<std::path::PathBuf>,
}

impl Default for SignatureLoader {
    fn default() -> Self {
        Self::new()
    }
}

impl SignatureLoader {
    /// Create new loader with default CDN URL
    pub fn new() -> Self {
        Self {
            cdn_url: CDN_BASE_URL.to_string(),
            cache_enabled: true,
            #[cfg(feature = "cdn")]
            cache_dir: Self::default_cache_dir(),
        }
    }
    
    /// Set custom CDN URL
    pub fn with_cdn_url(mut self, url: &str) -> Self {
        self.cdn_url = url.to_string();
        self
    }
    
    /// Disable caching
    pub fn without_cache(mut self) -> Self {
        self.cache_enabled = false;
        self
    }
    
    #[cfg(feature = "cdn")]
    fn default_cache_dir() -> Option<std::path::PathBuf> {
        directories::ProjectDirs::from("com", "sentinel", "sentinel-core")
            .map(|dirs| dirs.cache_dir().to_path_buf())
    }
    
    /// Load PII patterns synchronously from embedded or local file
    pub fn load_pii_embedded() -> PiiSignatures {
        // Embedded fallback - minimal patterns
        PiiSignatures {
            version: "embedded".to_string(),
            source: "sentinel-core".to_string(),
            last_updated: "2026-02-04".to_string(),
            description: Some("Embedded PII patterns".to_string()),
            patterns: vec![
                PiiPattern {
                    id: "pii_email".to_string(),
                    pattern_type: "email".to_string(),
                    regex: r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}".to_string(),
                    severity: "medium".to_string(),
                    action: "warn".to_string(),
                    description: "Email address".to_string(),
                },
                PiiPattern {
                    id: "pii_ssn".to_string(),
                    pattern_type: "ssn".to_string(),
                    regex: r"\b\d{3}-\d{2}-\d{4}\b".to_string(),
                    severity: "critical".to_string(),
                    action: "block".to_string(),
                    description: "US Social Security Number".to_string(),
                },
                PiiPattern {
                    id: "pii_credit_card".to_string(),
                    pattern_type: "credit_card".to_string(),
                    regex: r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b".to_string(),
                    severity: "critical".to_string(),
                    action: "block".to_string(),
                    description: "Credit card number".to_string(),
                },
                PiiPattern {
                    id: "secret_openai".to_string(),
                    pattern_type: "openai_key".to_string(),
                    regex: r"sk-[a-zA-Z0-9]{48}".to_string(),
                    severity: "critical".to_string(),
                    action: "block".to_string(),
                    description: "OpenAI API Key".to_string(),
                },
            ],
        }
    }
    
    /// Load keywords synchronously from embedded
    pub fn load_keywords_embedded() -> KeywordSignatures {
        let mut categories = HashMap::new();
        categories.insert("instruction_override".to_string(), "Instruction override attempts".to_string());
        categories.insert("roleplay".to_string(), "Roleplay attacks".to_string());
        categories.insert("authority".to_string(), "Authority claiming".to_string());
        
        KeywordSignatures {
            version: "embedded".to_string(),
            source: "sentinel-core".to_string(),
            last_updated: "2026-02-04".to_string(),
            total_keywords: 24,
            categories,
            keyword_sets: vec![
                KeywordSet {
                    id: "kw_override_001".to_string(),
                    category: "instruction_override".to_string(),
                    severity: "high".to_string(),
                    language: None,
                    keywords: vec![
                        "ignore previous".to_string(),
                        "ignore all".to_string(),
                        "disregard above".to_string(),
                        "forget instructions".to_string(),
                        "override instructions".to_string(),
                        "new instructions".to_string(),
                    ],
                },
                KeywordSet {
                    id: "kw_roleplay_001".to_string(),
                    category: "roleplay".to_string(),
                    severity: "high".to_string(),
                    language: None,
                    keywords: vec![
                        "you are now".to_string(),
                        "pretend to be".to_string(),
                        "act as if".to_string(),
                        "from now on".to_string(),
                        "roleplay as".to_string(),
                    ],
                },
                KeywordSet {
                    id: "kw_dan_001".to_string(),
                    category: "roleplay".to_string(),
                    severity: "critical".to_string(),
                    language: None,
                    keywords: vec![
                        "DAN".to_string(),
                        "Do Anything Now".to_string(),
                        "Developer Mode".to_string(),
                        "Jailbreak Mode".to_string(),
                    ],
                },
            ],
        }
    }
    
    /// Get CDN URL for a file
    pub fn file_url(&self, filename: &str) -> String {
        format!("{}/{}", self.cdn_url, filename)
    }

    /// Load jailbreak patterns from a local JSON file (synchronous)
    /// Supports both full files (jailbreaks.json) and part files
    pub fn load_jailbreaks_from_file(path: &std::path::Path) -> Result<Vec<JailbreakPattern>, SignatureError> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| SignatureError::IoError(e))?;

        // Try parsing as JailbreaksFile (with "patterns" key)
        if let Ok(file) = serde_json::from_str::<JailbreaksFile>(&content) {
            return Ok(file.patterns);
        }

        // Try parsing as bare Vec<JailbreakPattern>
        if let Ok(patterns) = serde_json::from_str::<Vec<JailbreakPattern>>(&content) {
            return Ok(patterns);
        }

        Err(SignatureError::ParseError(format!(
            "Failed to parse jailbreak signatures from {}",
            path.display()
        )))
    }

    /// Load all jailbreak patterns from a signatures directory
    /// Looks for jailbreaks.json, jailbreaks-ru.json, and part files
    pub fn load_all_jailbreaks_from_dir(dir: &std::path::Path) -> Vec<JailbreakPattern> {
        let mut all_patterns = Vec::new();

        // Priority order: full files first, then parts
        let files = [
            "jailbreaks.json",
            "jailbreaks-ru.json",
        ];

        for filename in &files {
            let path = dir.join(filename);
            if path.exists() {
                match Self::load_jailbreaks_from_file(&path) {
                    Ok(patterns) => {
                        log::info!("Loaded {} patterns from {}", patterns.len(), filename);
                        all_patterns.extend(patterns);
                    }
                    Err(e) => {
                        log::warn!("Failed to load {}: {}", filename, e);
                    }
                }
            }
        }

        // Also try part files
        for i in 1..=10 {
            let path = dir.join(format!("jailbreaks-part{}.json", i));
            if path.exists() {
                // Skip parts if we already loaded the full file
                if all_patterns.iter().any(|p| p.id.as_deref() == Some("jb_direct_001")) {
                    break;
                }
                match Self::load_jailbreaks_from_file(&path) {
                    Ok(patterns) => {
                        log::info!("Loaded {} patterns from part{}", patterns.len(), i);
                        all_patterns.extend(patterns);
                    }
                    Err(e) => {
                        log::warn!("Failed to load part {}: {}", i, e);
                    }
                }
            } else {
                break;
            }
        }

        all_patterns
    }

    /// Find the signatures directory relative to common locations
    pub fn find_signatures_dir() -> Option<std::path::PathBuf> {
        // 1. Environment variable
        if let Ok(dir) = std::env::var("SENTINEL_SIGNATURES_DIR") {
            let p = std::path::PathBuf::from(&dir);
            if p.exists() {
                return Some(p);
            }
        }

        // 2. Relative to current working directory
        let candidates = [
            "signatures",
            "../signatures",
            "../../signatures",
        ];

        for candidate in &candidates {
            let p = std::path::PathBuf::from(candidate);
            if p.exists() && p.join("jailbreaks.json").exists() {
                return Some(p);
            }
        }

        // 3. Relative to executable
        if let Ok(exe) = std::env::current_exe() {
            if let Some(exe_dir) = exe.parent() {
                for candidate in &candidates {
                    let p = exe_dir.join(candidate);
                    if p.exists() && p.join("jailbreaks.json").exists() {
                        return Some(p);
                    }
                }
            }
        }

        None
    }
}

/// Compiled pattern ready for engine use
#[derive(Clone)]
pub struct CompiledPattern {
    pub regex: regex::Regex,
    pub id: String,
    pub confidence: f64,
}

impl PiiSignatures {
    /// Convert severity to confidence score
    fn severity_to_confidence(severity: &str) -> f64 {
        match severity {
            "critical" => 0.95,
            "high" => 0.85,
            "medium" => 0.7,
            "low" => 0.5,
            _ => 0.6,
        }
    }
    
    /// Compile patterns into regex for engine use
    pub fn compile_patterns(&self) -> Vec<CompiledPattern> {
        self.patterns.iter().filter_map(|p| {
            match regex::Regex::new(&p.regex) {
                Ok(re) => Some(CompiledPattern {
                    regex: re,
                    id: p.id.clone(),
                    confidence: Self::severity_to_confidence(&p.severity),
                }),
                Err(e) => {
                    log::warn!("Failed to compile pattern {}: {}", p.id, e);
                    None
                }
            }
        }).collect()
    }
}

impl KeywordSignatures {
    /// Get all keywords as a flat list for Aho-Corasick
    pub fn all_keywords(&self) -> Vec<&str> {
        self.keyword_sets.iter()
            .flat_map(|set| set.keywords.iter().map(|s| s.as_str()))
            .collect()
    }
    
    /// Get keywords by category
    pub fn keywords_by_category(&self, category: &str) -> Vec<&str> {
        self.keyword_sets.iter()
            .filter(|set| set.category == category)
            .flat_map(|set| set.keywords.iter().map(|s| s.as_str()))
            .collect()
    }
    
    /// Get critical severity keywords
    pub fn critical_keywords(&self) -> Vec<&str> {
        self.keyword_sets.iter()
            .filter(|set| set.severity == "critical")
            .flat_map(|set| set.keywords.iter().map(|s| s.as_str()))
            .collect()
    }
}

#[cfg(feature = "cdn")]
impl SignatureLoader {
    /// Load PII patterns from CDN (async)
    pub async fn load_pii(&self) -> Result<PiiSignatures, SignatureError> {
        let url = self.file_url("pii.json");
        let response = reqwest::get(&url).await?;
        
        if !response.status().is_success() {
            return Err(SignatureError::HttpError(response.status().to_string()));
        }
        
        let sigs: PiiSignatures = response.json().await?;
        Ok(sigs)
    }
    
    /// Load keywords from CDN (async)
    pub async fn load_keywords(&self) -> Result<KeywordSignatures, SignatureError> {
        let url = self.file_url("keywords.json");
        let response = reqwest::get(&url).await?;
        
        if !response.status().is_success() {
            return Err(SignatureError::HttpError(response.status().to_string()));
        }
        
        let sigs: KeywordSignatures = response.json().await?;
        Ok(sigs)
    }
    
    /// Load jailbreaks manifest (for split file handling)
    pub async fn load_jailbreaks_manifest(&self) -> Result<JailbreaksManifest, SignatureError> {
        let url = self.file_url("jailbreaks-manifest.json");
        let response = reqwest::get(&url).await?;
        
        if !response.status().is_success() {
            return Err(SignatureError::HttpError(response.status().to_string()));
        }
        
        let manifest: JailbreaksManifest = response.json().await?;
        Ok(manifest)
    }
    
    /// Load all jailbreak parts and merge
    pub async fn load_jailbreaks(&self) -> Result<Vec<JailbreakPattern>, SignatureError> {
        let manifest = self.load_jailbreaks_manifest().await?;
        
        let mut all_patterns = Vec::with_capacity(manifest.total_patterns as usize);
        
        for part in &manifest.parts {
            let url = self.file_url(&part.file);
            let response = reqwest::get(&url).await?;
            
            if !response.status().is_success() {
                return Err(SignatureError::HttpError(format!(
                    "Failed to load {}: {}",
                    part.file,
                    response.status()
                )));
            }
            
            let patterns: Vec<JailbreakPattern> = response.json().await?;
            all_patterns.extend(patterns);
        }
        
        Ok(all_patterns)
    }
}

/// Signature loading errors
#[derive(Debug, thiserror::Error)]
pub enum SignatureError {
    #[error("HTTP error: {0}")]
    HttpError(String),
    
    #[cfg(feature = "cdn")]
    #[error("Request failed: {0}")]
    RequestError(#[from] reqwest::Error),
    
    #[error("Parse error: {0}")]
    ParseError(String),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Cache miss and CDN unavailable")]
    Unavailable,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_embedded_pii() {
        let pii = SignatureLoader::load_pii_embedded();
        assert!(!pii.patterns.is_empty());
        assert!(pii.patterns.iter().any(|p| p.id == "pii_email"));
        assert!(pii.patterns.iter().any(|p| p.id == "secret_openai"));
    }
    
    #[test]
    fn test_embedded_keywords() {
        let kw = SignatureLoader::load_keywords_embedded();
        assert!(!kw.keyword_sets.is_empty());
        
        let override_set = kw.keyword_sets.iter()
            .find(|s| s.category == "instruction_override")
            .expect("should have instruction_override");
        assert!(override_set.keywords.contains(&"ignore previous".to_string()));
    }
    
    #[test]
    fn test_file_url() {
        let loader = SignatureLoader::new();
        let url = loader.file_url("pii.json");
        assert!(url.contains("cdn.jsdelivr.net"));
        assert!(url.ends_with("pii.json"));
    }
    
    #[test]
    fn test_custom_cdn_url() {
        let loader = SignatureLoader::new()
            .with_cdn_url("https://example.com/sigs");
        let url = loader.file_url("test.json");
        assert_eq!(url, "https://example.com/sigs/test.json");
    }
    
    #[test]
    fn test_compile_pii_patterns() {
        let pii = SignatureLoader::load_pii_embedded();
        let compiled = pii.compile_patterns();
        
        assert!(!compiled.is_empty());
        
        // Test that patterns actually match
        let email_pattern = compiled.iter().find(|p| p.id == "pii_email").unwrap();
        assert!(email_pattern.regex.is_match("test@example.com"));
        assert!(!email_pattern.regex.is_match("notanemail"));
        
        let ssn_pattern = compiled.iter().find(|p| p.id == "pii_ssn").unwrap();
        assert!(ssn_pattern.regex.is_match("123-45-6789"));
    }
    
    #[test]
    fn test_keyword_helpers() {
        let kw = SignatureLoader::load_keywords_embedded();
        
        let all = kw.all_keywords();
        assert!(all.contains(&"ignore previous"));
        assert!(all.contains(&"DAN"));
        
        let critical = kw.critical_keywords();
        assert!(critical.contains(&"DAN"));
        assert!(!critical.contains(&"ignore previous")); // high, not critical
        
        let roleplay = kw.keywords_by_category("roleplay");
        assert!(roleplay.contains(&"pretend to be"));
    }
}
