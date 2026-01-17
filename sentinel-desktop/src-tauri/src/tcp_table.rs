//! TCP Connection Table lookup via Windows IP Helper API
//! 
//! This module provides production-grade connection-to-PID mapping
//! using GetExtendedTcpTable API instead of netstat subprocess.

use std::collections::HashMap;
use std::net::Ipv4Addr;
use std::sync::RwLock;
use std::time::{Duration, Instant};
use once_cell::sync::Lazy;
use tracing::{debug, warn};

#[cfg(windows)]
use windows::Win32::NetworkManagement::IpHelper::{
    GetExtendedTcpTable, MIB_TCPTABLE_OWNER_PID, TCP_TABLE_OWNER_PID_ALL,
};
#[cfg(windows)]
use windows::Win32::Networking::WinSock::AF_INET;

/// Connection key: (local_port, remote_ip, remote_port)
pub type ConnectionKey = (u16, Ipv4Addr, u16);

/// Cache entry: (PID, timestamp)
struct CacheEntry {
    pid: u32,
    timestamp: Instant,
}

/// Connection cache with TTL
static CONNECTION_CACHE: Lazy<RwLock<HashMap<ConnectionKey, CacheEntry>>> = 
    Lazy::new(|| RwLock::new(HashMap::new()));

/// Cache TTL - connections older than this are refreshed
const CACHE_TTL: Duration = Duration::from_secs(5);

/// Last full table refresh time
static LAST_REFRESH: Lazy<RwLock<Instant>> = 
    Lazy::new(|| RwLock::new(Instant::now() - Duration::from_secs(60)));

/// Minimum interval between full table refreshes
const REFRESH_INTERVAL: Duration = Duration::from_millis(500);

/// Get PID for a connection (local_port, remote_ip, remote_port)
/// This is the main entry point - fast cached lookup with background refresh
pub fn get_pid_for_connection(local_port: u16, remote_ip: Ipv4Addr, remote_port: u16) -> Option<u32> {
    let key = (local_port, remote_ip, remote_port);
    
    // Try cache first
    {
        let cache = CONNECTION_CACHE.read().ok()?;
        if let Some(entry) = cache.get(&key) {
            if entry.timestamp.elapsed() < CACHE_TTL {
                return Some(entry.pid);
            }
        }
    }
    
    // Cache miss or expired - refresh table if needed
    maybe_refresh_table();
    
    // Try cache again after refresh
    {
        let cache = CONNECTION_CACHE.read().ok()?;
        cache.get(&key).map(|e| e.pid)
    }
}

/// Refresh the connection table if enough time has passed
fn maybe_refresh_table() {
    let should_refresh = {
        let last = LAST_REFRESH.read().ok();
        last.map(|t| t.elapsed() >= REFRESH_INTERVAL).unwrap_or(true)
    };
    
    if should_refresh {
        refresh_connection_table();
    }
}

/// Refresh the entire connection table from Windows API
#[cfg(windows)]
fn refresh_connection_table() {
    // Update last refresh time
    if let Ok(mut last) = LAST_REFRESH.write() {
        *last = Instant::now();
    }
    
    let mut size: u32 = 0;
    
    // First call to get required buffer size
    unsafe {
        let _ = GetExtendedTcpTable(
            None,
            &mut size,
            false,
            AF_INET.0 as u32,
            TCP_TABLE_OWNER_PID_ALL,
            0,
        );
    }
    
    if size == 0 {
        return;
    }
    
    // Allocate buffer
    let mut buffer: Vec<u8> = vec![0u8; size as usize];
    
    // Second call to get actual data
    let result = unsafe {
        GetExtendedTcpTable(
            Some(buffer.as_mut_ptr() as *mut _),
            &mut size,
            false,
            AF_INET.0 as u32,
            TCP_TABLE_OWNER_PID_ALL,
            0,
        )
    };
    
    if result != 0 {
        warn!("GetExtendedTcpTable failed with error: {}", result);
        return;
    }
    
    // Parse the table
    let table = unsafe { &*(buffer.as_ptr() as *const MIB_TCPTABLE_OWNER_PID) };
    let num_entries = table.dwNumEntries as usize;
    
    if num_entries == 0 {
        return;
    }
    
    // Update cache
    let now = Instant::now();
    let mut new_cache: HashMap<ConnectionKey, CacheEntry> = HashMap::with_capacity(num_entries);
    
    unsafe {
        let rows_ptr = table.table.as_ptr();
        
        for i in 0..num_entries {
            let row = &*rows_ptr.add(i);
            
            // Parse addresses (network byte order)
            let local_port = u16::from_be(row.dwLocalPort as u16);
            let remote_ip = Ipv4Addr::from(u32::from_be(row.dwRemoteAddr));
            let remote_port = u16::from_be(row.dwRemotePort as u16);
            let pid = row.dwOwningPid;
            
            // Skip invalid entries
            if pid == 0 {
                continue;
            }
            
            let key = (local_port, remote_ip, remote_port);
            new_cache.insert(key, CacheEntry {
                pid,
                timestamp: now,
            });
        }
    }
    
    // Swap cache atomically
    if let Ok(mut cache) = CONNECTION_CACHE.write() {
        *cache = new_cache;
    }
    
    debug!("Refreshed TCP table: {} connections", num_entries);
}

#[cfg(not(windows))]
fn refresh_connection_table() {
    // Stub for non-Windows
}

/// Get all connections for a specific PID
pub fn get_connections_for_pid(target_pid: u32) -> Vec<ConnectionKey> {
    maybe_refresh_table();
    
    let cache = match CONNECTION_CACHE.read() {
        Ok(c) => c,
        Err(_) => return vec![],
    };
    
    cache.iter()
        .filter(|(_, entry)| entry.pid == target_pid)
        .map(|(key, _)| *key)
        .collect()
}

/// Check if a specific connection belongs to a set of monitored PIDs
#[allow(dead_code)]
pub fn is_connection_monitored(
    local_port: u16, 
    remote_ip: Ipv4Addr, 
    remote_port: u16,
    monitored_pids: &std::collections::HashSet<u32>
) -> Option<u32> {
    let pid = get_pid_for_connection(local_port, remote_ip, remote_port)?;
    
    if monitored_pids.contains(&pid) {
        Some(pid)
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_refresh_table() {
        refresh_connection_table();
        // Should not panic
    }
}
