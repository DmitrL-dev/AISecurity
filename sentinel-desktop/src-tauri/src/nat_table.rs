//! NAT Table for Transparent Proxy
//!
//! Stores original destination mapping for redirected connections.
//! Shared between WinDivert redirector and Transparent Proxy.

use std::collections::HashMap;
use std::net::Ipv4Addr;
use std::sync::RwLock;
use std::time::{Duration, Instant};
use once_cell::sync::Lazy;
use tracing::debug;

/// NAT entry: original destination info
#[derive(Clone, Debug)]
pub struct NatEntry {
    pub original_ip: Ipv4Addr,
    pub original_port: u16,
    pub timestamp: Instant,
}

/// NAT table: source_port -> original destination
/// Key is the client's source port (ephemeral port)
static NAT_TABLE: Lazy<RwLock<HashMap<u16, NatEntry>>> = 
    Lazy::new(|| RwLock::new(HashMap::new()));

/// Entry TTL - entries older than this are cleaned up
const ENTRY_TTL: Duration = Duration::from_secs(300); // 5 minutes

/// Max entries before cleanup
const MAX_ENTRIES: usize = 10000;

/// Register a redirected connection in NAT table
/// Called by redirector when it redirects a SYN packet
pub fn register_redirect(
    client_port: u16,
    original_ip: Ipv4Addr,
    original_port: u16,
) {
    let entry = NatEntry {
        original_ip,
        original_port,
        timestamp: Instant::now(),
    };
    
    let mut table = match NAT_TABLE.write() {
        Ok(t) => t,
        Err(_) => return,
    };
    
    // Cleanup if too many entries
    if table.len() >= MAX_ENTRIES {
        cleanup_old_entries(&mut table);
    }
    
    debug!(
        "NAT: registered {}:{} -> localhost:8443 (original: {}:{})",
        "client", client_port, original_ip, original_port
    );
    
    table.insert(client_port, entry);
}

/// Lookup original destination by client port
/// Called by transparent proxy to know where to connect
pub fn lookup_original_destination(client_port: u16) -> Option<(Ipv4Addr, u16)> {
    let table = NAT_TABLE.read().ok()?;
    
    table.get(&client_port).map(|entry| {
        (entry.original_ip, entry.original_port)
    })
}

/// Remove entry after connection is handled
#[allow(dead_code)]
pub fn remove_entry(client_port: u16) {
    if let Ok(mut table) = NAT_TABLE.write() {
        table.remove(&client_port);
    }
}

/// Cleanup old entries
fn cleanup_old_entries(table: &mut HashMap<u16, NatEntry>) {
    let now = Instant::now();
    table.retain(|_, entry| now.duration_since(entry.timestamp) < ENTRY_TTL);
}

/// Get current NAT table size (for debugging)
#[allow(dead_code)]
pub fn get_table_size() -> usize {
    NAT_TABLE.read().map(|t| t.len()).unwrap_or(0)
}
