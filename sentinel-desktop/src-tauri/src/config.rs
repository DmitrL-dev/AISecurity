//! SENTINEL Desktop - Configuration Persistence
//!
//! Saves and loads user configuration including monitored applications.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;
use tracing::{info, warn};

/// Configuration file structure
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SentinelConfig {
    /// Version for migration
    pub version: u32,
    
    /// Monitored application names (not PIDs - they change)
    pub monitored_apps: HashSet<String>,
    
    /// Deep inspection enabled
    pub deep_inspection: bool,
    
    /// System proxy enabled
    pub system_proxy_enabled: bool,
}

impl SentinelConfig {
    /// Current config version
    const CURRENT_VERSION: u32 = 1;
    
    /// Get config directory path
    pub fn config_dir() -> PathBuf {
        let app_data = std::env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
        PathBuf::from(app_data).join("SENTINEL")
    }
    
    /// Get config file path
    pub fn config_path() -> PathBuf {
        Self::config_dir().join("config.json")
    }
    
    /// Load config from disk
    pub fn load() -> Self {
        let path = Self::config_path();
        
        if !path.exists() {
            info!("No config file, using defaults");
            return Self::default_config();
        }
        
        match fs::read_to_string(&path) {
            Ok(content) => {
                match serde_json::from_str::<SentinelConfig>(&content) {
                    Ok(config) => {
                        info!("Loaded config with {} monitored apps", config.monitored_apps.len());
                        config
                    }
                    Err(e) => {
                        warn!("Failed to parse config: {}, using defaults", e);
                        Self::default_config()
                    }
                }
            }
            Err(e) => {
                warn!("Failed to read config: {}, using defaults", e);
                Self::default_config()
            }
        }
    }
    
    /// Save config to disk
    pub fn save(&self) -> Result<(), String> {
        let dir = Self::config_dir();
        
        // Create directory if needed
        if !dir.exists() {
            if let Err(e) = fs::create_dir_all(&dir) {
                return Err(format!("Failed to create config dir: {}", e));
            }
        }
        
        let path = Self::config_path();
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| format!("Failed to serialize config: {}", e))?;
        
        fs::write(&path, content)
            .map_err(|e| format!("Failed to write config: {}", e))?;
        
        info!("Saved config with {} monitored apps", self.monitored_apps.len());
        Ok(())
    }
    
    /// Create default config
    fn default_config() -> Self {
        Self {
            version: Self::CURRENT_VERSION,
            monitored_apps: HashSet::new(),
            deep_inspection: false,
            system_proxy_enabled: true,
        }
    }
    
    /// Add monitored app by name
    pub fn add_monitored_app(&mut self, name: &str) {
        self.monitored_apps.insert(name.to_lowercase());
    }
    
    /// Remove monitored app by name
    pub fn remove_monitored_app(&mut self, name: &str) {
        self.monitored_apps.remove(&name.to_lowercase());
    }
    
    /// Check if app is monitored
    #[allow(dead_code)]
    pub fn is_app_monitored(&self, name: &str) -> bool {
        self.monitored_apps.contains(&name.to_lowercase())
    }
}

// Global config instance
static CONFIG: std::sync::OnceLock<std::sync::RwLock<SentinelConfig>> = std::sync::OnceLock::new();

/// Get global config (loads on first access)
pub fn config() -> &'static std::sync::RwLock<SentinelConfig> {
    CONFIG.get_or_init(|| {
        std::sync::RwLock::new(SentinelConfig::load())
    })
}

/// Save global config
pub fn save_config() -> Result<(), String> {
    config().read().unwrap().save()
}
