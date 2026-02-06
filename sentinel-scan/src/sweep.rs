//! Network sweep module
//!
//! Concurrent scanning of IP ranges for LLM services.

use crate::fingerprint::probe_target;
use futures::stream::{self, StreamExt};
use ipnet::Ipv4Net;
use serde::{Deserialize, Serialize};
use std::net::Ipv4Addr;

/// Result of network sweep
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SweepResult {
    pub target: String,
    pub platform: String,
}

/// Scan a CIDR range for LLM services
pub async fn scan_range(
    cidr: &str,
    port: u16,
    concurrency: usize,
) -> Result<Vec<SweepResult>, Box<dyn std::error::Error>> {
    let network: Ipv4Net = cidr.parse()?;
    
    let hosts: Vec<Ipv4Addr> = network.hosts().collect();
    
    let results: Vec<Option<SweepResult>> = stream::iter(hosts)
        .map(|ip| async move {
            let target = format!("http://{}:{}", ip, port);
            match probe_target(&target, 3).await {
                Ok(Some(platform)) => Some(SweepResult {
                    target,
                    platform,
                }),
                _ => None,
            }
        })
        .buffer_unordered(concurrency)
        .collect()
        .await;
    
    Ok(results.into_iter().flatten().collect())
}

/// Generate target list from CIDR
pub fn expand_cidr(cidr: &str) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let network: Ipv4Net = cidr.parse()?;
    Ok(network.hosts().map(|ip| ip.to_string()).collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_expand_cidr_small() {
        let hosts = expand_cidr("192.168.1.0/30").unwrap();
        assert_eq!(hosts.len(), 2); // /30 = 4 addresses - network - broadcast = 2 hosts
    }
    
    #[test]
    fn test_expand_cidr_class_c() {
        let hosts = expand_cidr("10.0.0.0/24").unwrap();
        assert_eq!(hosts.len(), 254); // /24 = 256 - 2 = 254 usable
    }
    
    #[test]
    fn test_sweep_result_serializes() {
        let result = SweepResult {
            target: "http://192.168.1.5:11434".to_string(),
            platform: "ollama".to_string(),
        };
        
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("192.168.1.5"));
    }
}
