//! CDN Sync Module
//!
//! Downloads and updates signatures from jsDelivr CDN.
//! Source: cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@latest/signatures/

#![allow(unused)]

use reqwest::Client;
use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use tracing::{info, warn, error};

/// CDN base URL for signatures
const CDN_BASE: &str = "https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@main/signatures";

/// Manifest describing available signature files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignatureManifest {
    pub version: String,
    #[serde(default)]
    pub timestamp: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub sources: Vec<String>,
    pub files: HashMap<String, SignatureFileInfo>,
    #[serde(default)]
    pub update_info: Option<UpdateInfo>,
}

/// Individual signature file entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignatureFileInfo {
    pub path: String,
    pub sha256: String,
    pub size: u64,
    #[serde(default)]
    pub count: u64,
}

/// Update info from manifest
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub cdn_url: Option<String>,
    pub update_interval_hours: Option<u64>,
    pub fallback_to_embedded: Option<bool>,
}

/// CDN sync result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncResult {
    pub success: bool,
    pub updated_files: Vec<String>,
    pub errors: Vec<String>,
    pub new_version: Option<String>,
}

/// CDN Sync Manager
pub struct CdnSync {
    client: Client,
    storage_path: PathBuf,
}

impl CdnSync {
    /// Create new CDN sync manager
    pub fn new(storage_path: PathBuf) -> Self {
        Self {
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(300)) // 5 minutes for large files
                .build()
                .expect("Failed to create HTTP client"),
            storage_path,
        }
    }
    
    /// Get default storage path (%APPDATA%\SENTINEL\signatures)
    pub fn default_storage_path() -> PathBuf {
        dirs::data_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("SENTINEL")
            .join("signatures")
    }
    
    /// Sync signatures from CDN
    pub async fn sync(&self) -> SyncResult {
        let mut result = SyncResult {
            success: false,
            updated_files: Vec::new(),
            errors: Vec::new(),
            new_version: None,
        };
        
        // Ensure storage directory exists
        if let Err(e) = fs::create_dir_all(&self.storage_path) {
            result.errors.push(format!("Failed to create storage dir: {}", e));
            return result;
        }
        
        // Fetch remote manifest
        let remote_manifest = match self.fetch_manifest().await {
            Ok(m) => m,
            Err(e) => {
                result.errors.push(format!("Failed to fetch manifest: {}", e));
                return result;
            }
        };
        
        // Load local manifest (if exists)
        let local_manifest = self.load_local_manifest();
        
        // Check if update needed
        if let Some(ref local) = local_manifest {
            if local.version == remote_manifest.version {
                info!("Signatures up to date (version {})", local.version);
                result.success = true;
                return result;
            }
        }
        
        info!(
            "Updating signatures: {} -> {}",
            local_manifest.as_ref().map(|m| m.version.as_str()).unwrap_or("none"),
            remote_manifest.version
        );
        
        // Download changed files
        for (key, file_info) in &remote_manifest.files {
            info!("Processing file: {} -> {}", key, file_info.path);
            if self.needs_update(key, file_info, &local_manifest) {
                info!("Downloading: {} ({} bytes)", file_info.path, file_info.size);
                match self.download_file(&file_info.path).await {
                    Ok(data) => {
                        info!("Downloaded {} bytes for {}", data.len(), file_info.path);
                        // Verify SHA256
                        let hash = self.sha256_hex(&data);
                        if hash != file_info.sha256 {
                            result.errors.push(format!(
                                "Hash mismatch for {}: expected {}, got {}",
                                file_info.path, file_info.sha256, hash
                            ));
                            continue;
                        }
                        
                        // Save file
                        let path = self.storage_path.join(&file_info.path);
                        if let Err(e) = fs::write(&path, &data) {
                            result.errors.push(format!("Failed to write {}: {}", file_info.path, e));
                            continue;
                        }
                        
                        result.updated_files.push(file_info.path.clone());
                        info!("Updated: {} ({} entries)", file_info.path, file_info.count);
                    }
                    Err(e) => {
                        error!("Failed to download {}: {}", file_info.path, e);
                        result.errors.push(format!("Failed to download {}: {}", file_info.path, e));
                    }
                }
            } else {
                info!("Skipping {} - already up to date", file_info.path);
            }
        }
        
        // Save new manifest
        let manifest_path = self.storage_path.join("manifest.json");
        if let Ok(json) = serde_json::to_string_pretty(&remote_manifest) {
            let _ = fs::write(&manifest_path, json);
        }
        
        result.new_version = Some(remote_manifest.version);
        result.success = result.errors.is_empty();
        result
    }
    
    /// Fetch manifest from CDN
    async fn fetch_manifest(&self) -> Result<SignatureManifest, Box<dyn std::error::Error + Send + Sync>> {
        let url = format!("{}/manifest.json", CDN_BASE);
        info!("Fetching manifest from: {}", url);
        let response = self.client.get(&url).send().await?;
        
        if !response.status().is_success() {
            return Err(format!("HTTP {}", response.status()).into());
        }
        
        let text = response.text().await?;
        info!("Manifest response: {} bytes", text.len());
        
        let manifest: SignatureManifest = serde_json::from_str(&text)
            .map_err(|e| format!("Parse error: {} - Content: {}", e, &text[..200.min(text.len())]))?;
        
        info!("Parsed manifest: version={}, {} files", manifest.version, manifest.files.len());
        Ok(manifest)
    }
    
    /// Load local manifest
    fn load_local_manifest(&self) -> Option<SignatureManifest> {
        let path = self.storage_path.join("manifest.json");
        let content = fs::read_to_string(&path).ok()?;
        serde_json::from_str(&content).ok()
    }
    
    /// Check if file needs update
    fn needs_update(&self, key: &str, file_info: &SignatureFileInfo, local_manifest: &Option<SignatureManifest>) -> bool {
        let local_path = self.storage_path.join(&file_info.path);
        
        // File doesn't exist locally
        if !local_path.exists() {
            return true;
        }
        
        // Check hash in local manifest
        if let Some(manifest) = local_manifest {
            if let Some(local_file) = manifest.files.get(key) {
                return local_file.sha256 != file_info.sha256;
            }
        }
        
        true
    }
    
    /// Download file from CDN
    async fn download_file(&self, name: &str) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
        let url = format!("{}/{}", CDN_BASE, name);
        let response = self.client.get(&url).send().await?;
        
        if !response.status().is_success() {
            return Err(format!("HTTP {}", response.status()).into());
        }
        
        let bytes = response.bytes().await?;
        Ok(bytes.to_vec())
    }
    
    /// Calculate SHA256 hash as hex string
    fn sha256_hex(&self, data: &[u8]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(data);
        let result = hasher.finalize();
        hex::encode(result)
    }
    
    /// Verify integrity of local signatures
    pub fn verify_integrity(&self) -> Result<(), Vec<String>> {
        let manifest = self.load_local_manifest()
            .ok_or_else(|| vec!["No local manifest found".to_string()])?;
        
        let mut errors = Vec::new();
        
        for (key, file_info) in &manifest.files {
            let path = self.storage_path.join(&file_info.path);
            
            match fs::read(&path) {
                Ok(data) => {
                    let hash = self.sha256_hex(&data);
                    if hash != file_info.sha256 {
                        errors.push(format!(
                            "Integrity violation: {} (expected {}, got {})",
                            file_info.path, file_info.sha256, hash
                        ));
                    }
                }
                Err(e) => {
                    errors.push(format!("Cannot read {}: {}", file_info.path, e));
                }
            }
        }
        
        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }
}

/// Hex encoding helper
mod hex {
    pub fn encode(bytes: impl AsRef<[u8]>) -> String {
        bytes.as_ref().iter().map(|b| format!("{:02x}", b)).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_sha256_hex() {
        let sync = CdnSync::new(PathBuf::from("."));
        let hash = sync.sha256_hex(b"hello world");
        assert_eq!(hash, "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9");
    }
    
    #[test]
    fn test_default_storage_path() {
        let path = CdnSync::default_storage_path();
        assert!(path.to_string_lossy().contains("SENTINEL"));
    }
}
