//! SENTINEL Proxy Module
//! 
//! MITM proxy for TLS inspection of AI API traffic.

pub mod ca;
pub mod server;
pub mod transparent_server;

use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use tokio::sync::RwLock;

pub use ca::CertificateAuthority;
#[allow(unused_imports)]
pub use server::ProxyServer;

// =============================================================================
// GLOBAL PROXY STATISTICS
// =============================================================================

/// Total connections handled by proxy
static PROXY_CONNECTIONS: AtomicU64 = AtomicU64::new(0);

/// AI API connections (OpenAI, Anthropic, etc.)
static PROXY_AI_CONNECTIONS: AtomicU64 = AtomicU64::new(0);

/// Increment connection counter
pub fn inc_proxy_connection() {
    PROXY_CONNECTIONS.fetch_add(1, Ordering::SeqCst);
}

/// Increment AI connection counter
pub fn inc_ai_connection() {
    PROXY_AI_CONNECTIONS.fetch_add(1, Ordering::SeqCst);
}

/// Get proxy statistics (total, ai_connections)
pub fn get_proxy_stats() -> (u64, u64) {
    (
        PROXY_CONNECTIONS.load(Ordering::SeqCst),
        PROXY_AI_CONNECTIONS.load(Ordering::SeqCst),
    )
}

// =============================================================================
// CONFIGURATION
// =============================================================================

/// Proxy configuration
#[derive(Debug, Clone)]
pub struct ProxyConfig {
    /// Listen address (default: 127.0.0.1:8443)
    pub listen_addr: String,
    /// Enable deep inspection
    pub deep_inspection: bool,
    /// Block on threat detection
    pub block_threats: bool,
}

impl Default for ProxyConfig {
    fn default() -> Self {
        Self {
            listen_addr: "127.0.0.1:8443".to_string(),
            deep_inspection: true,
            block_threats: false,
        }
    }
}

/// Proxy state
pub struct ProxyState {
    pub config: RwLock<ProxyConfig>,
    pub ca: Arc<CertificateAuthority>,
    pub running: std::sync::atomic::AtomicBool,
}
