//! Pattern loading and management
//!
//! Loads patterns from JSON for hot-reload capability
//! NOTE: Infrastructure for future config-driven patterns

#![allow(dead_code)] // Future hot-reload infrastructure

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternSet {
    pub name: String,
    pub category: String,
    pub keywords: Vec<String>,
    pub patterns: Vec<PatternDef>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternDef {
    pub regex: String,
    pub name: String,
    pub confidence: f64,
    pub severity: String,
}

/// Load patterns from JSON file
pub fn load_patterns(json_path: &str) -> Result<HashMap<String, PatternSet>, Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(json_path)?;
    let patterns: HashMap<String, PatternSet> = serde_json::from_str(&content)?;
    Ok(patterns)
}

/// Load patterns from embedded JSON string
pub fn load_patterns_from_str(json: &str) -> Result<HashMap<String, PatternSet>, serde_json::Error> {
    serde_json::from_str(json)
}
