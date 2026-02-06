//! LLM Platform Fingerprinting
//!
//! Detects various LLM platforms by probing known endpoints.

use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Detected LLM platform
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Platform {
    pub name: String,
    pub version: Option<String>,
    pub models: Vec<String>,
    pub risk_level: RiskLevel,
}

/// Risk assessment level
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// Probe configuration
#[derive(Clone)]
pub struct Probe {
    pub name: &'static str,
    pub path: &'static str,
    pub signature: &'static str,
    pub model_path: Option<&'static str>,
}

/// Known LLM platform probes
pub const PROBES: &[Probe] = &[
    Probe {
        name: "ollama",
        path: "/api/tags",
        signature: r#""models":"#,
        model_path: Some("/api/tags"),
    },
    Probe {
        name: "vllm",
        path: "/v1/models",
        signature: r#""data":"#,
        model_path: Some("/v1/models"),
    },
    Probe {
        name: "tgi",
        path: "/info",
        signature: r#""model_id""#,
        model_path: Some("/info"),
    },
    Probe {
        name: "langserve",
        path: "/docs",
        signature: "LangServe",
        model_path: None,
    },
    Probe {
        name: "localai",
        path: "/v1/models",
        signature: "LocalAI",
        model_path: Some("/v1/models"),
    },
];

/// Probe a target for LLM services
pub async fn probe_target(
    target: &str,
    timeout_secs: u64,
) -> Result<Option<String>, Box<dyn std::error::Error>> {
    let client = Client::builder()
        .timeout(Duration::from_secs(timeout_secs))
        .danger_accept_invalid_certs(true)
        .build()?;
    
    for probe in PROBES {
        let url = format!("{}{}", target.trim_end_matches('/'), probe.path);
        
        match client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                if let Ok(body) = resp.text().await {
                    if body.contains(probe.signature) {
                        return Ok(Some(probe.name.to_string()));
                    }
                }
            }
            _ => continue,
        }
    }
    
    Ok(None)
}

/// Enumerate models on a target
pub async fn enumerate_models(
    target: &str,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let client = Client::builder()
        .timeout(Duration::from_secs(10))
        .danger_accept_invalid_certs(true)
        .build()?;
    
    let mut models = Vec::new();
    
    // Try Ollama endpoint
    let url = format!("{}/api/tags", target.trim_end_matches('/'));
    if let Ok(resp) = client.get(&url).send().await {
        if resp.status().is_success() {
            if let Ok(body) = resp.text().await {
                // Parse Ollama response
                if let Ok(parsed) = serde_json::from_str::<OllamaModels>(&body) {
                    for model in parsed.models {
                        models.push(model.name);
                    }
                }
            }
        }
    }
    
    // Try OpenAI-compatible endpoint (vLLM, LocalAI)
    if models.is_empty() {
        let url = format!("{}/v1/models", target.trim_end_matches('/'));
        if let Ok(resp) = client.get(&url).send().await {
            if resp.status().is_success() {
                if let Ok(body) = resp.text().await {
                    if let Ok(parsed) = serde_json::from_str::<OpenAIModels>(&body) {
                        for model in parsed.data {
                            models.push(model.id);
                        }
                    }
                }
            }
        }
    }
    
    Ok(models)
}

/// Assess risk level for exposed LLM
pub fn assess_risk(platform: &str, models: &[String], is_public: bool) -> RiskLevel {
    // Critical if exposed to public internet
    if is_public {
        return RiskLevel::Critical;
    }
    
    // High risk for code generation models
    let code_gen_models = ["codellama", "starcoder", "deepseek-coder", "codegemma"];
    for model in models {
        let model_lower = model.to_lowercase();
        for dangerous in &code_gen_models {
            if model_lower.contains(dangerous) {
                return RiskLevel::High;
            }
        }
    }
    
    // Medium risk for generic LLMs
    if !models.is_empty() {
        return RiskLevel::Medium;
    }
    
    // Low risk if just platform detected, no models
    RiskLevel::Low
}

// Response structs for parsing

#[derive(Deserialize)]
struct OllamaModels {
    models: Vec<OllamaModel>,
}

#[derive(Deserialize)]
struct OllamaModel {
    name: String,
}

#[derive(Deserialize)]
struct OpenAIModels {
    data: Vec<OpenAIModel>,
}

#[derive(Deserialize)]
struct OpenAIModel {
    id: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_probe_list() {
        assert!(PROBES.len() >= 5);
        assert!(PROBES.iter().any(|p| p.name == "ollama"));
        assert!(PROBES.iter().any(|p| p.name == "vllm"));
    }
    
    #[test]
    fn test_risk_assessment_public() {
        let risk = assess_risk("ollama", &[], true);
        assert_eq!(risk, RiskLevel::Critical);
    }
    
    #[test]
    fn test_risk_assessment_code_model() {
        let risk = assess_risk("ollama", &["codellama:7b".to_string()], false);
        assert_eq!(risk, RiskLevel::High);
    }
    
    #[test]
    fn test_risk_assessment_normal() {
        let risk = assess_risk("ollama", &["llama3:8b".to_string()], false);
        assert_eq!(risk, RiskLevel::Medium);
    }
    
    #[test]
    fn test_risk_assessment_low() {
        let risk = assess_risk("ollama", &[], false);
        assert_eq!(risk, RiskLevel::Low);
    }
}
