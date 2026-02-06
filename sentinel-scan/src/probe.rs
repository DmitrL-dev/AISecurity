//! Single target probe module
//!
//! Higher-level wrapper around fingerprint for single target probing.

use crate::fingerprint::{probe_target, enumerate_models, assess_risk, RiskLevel};
use serde::{Deserialize, Serialize};

/// Result of probing a single target
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProbeResult {
    pub target: String,
    pub platform: Option<String>,
    pub models: Vec<String>,
    pub risk_level: RiskLevel,
    pub authenticated: bool,
}

/// Probe a single target comprehensively
pub async fn probe_full(
    target: &str,
    timeout_secs: u64,
) -> Result<ProbeResult, Box<dyn std::error::Error>> {
    // First, detect platform
    let platform = probe_target(target, timeout_secs).await?;
    
    // Then enumerate models if platform detected
    let models = if platform.is_some() {
        enumerate_models(target).await.unwrap_or_default()
    } else {
        Vec::new()
    };
    
    // Assess risk (assume not public by default)
    let risk_level = platform
        .as_ref()
        .map(|p| assess_risk(p, &models, false))
        .unwrap_or(RiskLevel::Low);
    
    Ok(ProbeResult {
        target: target.to_string(),
        platform,
        models,
        risk_level,
        authenticated: false, // TODO: Detect auth requirement
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_probe_result_serializes() {
        let result = ProbeResult {
            target: "http://localhost:11434".to_string(),
            platform: Some("ollama".to_string()),
            models: vec!["llama3:8b".to_string()],
            risk_level: RiskLevel::Medium,
            authenticated: false,
        };
        
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("ollama"));
        assert!(json.contains("llama3"));
    }
}
