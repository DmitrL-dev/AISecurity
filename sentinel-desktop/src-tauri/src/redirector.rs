//! SENTINEL Desktop - WinDivert Traffic Redirector v2
//!
//! Per-process traffic interception using Reflection Pattern.
//! Based on streamdump example from WinDivert.
//!
//! Architecture:
//! - SOCKET layer (SNIFF): Maps 5-tuple -> PID
//! - NETWORK layer (INTERCEPT): Reflects monitored traffic to proxy

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::thread;
use std::collections::{HashMap, HashSet};

use std::sync::RwLock;
use std::time::Instant;
use std::net::Ipv4Addr;
use tracing::{info, warn, error};
use windivert::prelude::*;

// =============================================================================
// CONSTANTS
// =============================================================================

/// Target port - where apps connect (HTTPS)
const TARGET_PORT: u16 = 443;

/// Proxy port - SENTINEL MITM proxy (must match lib.rs ProxyServer)
const PROXY_PORT: u16 = 18443;

/// NAT Proxy IP - loopback for localhost proxy
const NAT_PROXY_IP: [u8; 4] = [127, 0, 0, 1];

/// Alternate port - proxy's outbound connections
const ALT_PORT: u16 = 18444;

/// Max pending packets queue size
#[allow(dead_code)]
const MAX_PENDING_QUEUE: usize = 1000;

/// Max connections in tracker before cleanup
const MAX_CONNECTIONS: usize = 50000;

// =============================================================================
// GLOBAL STATE  
// =============================================================================

/// Redirector running flag
static REDIRECTOR_RUNNING: AtomicBool = AtomicBool::new(false);

/// Statistics counters
static STATS_PACKETS_SEEN: AtomicU64 = AtomicU64::new(0);
static STATS_PACKETS_REFLECTED: AtomicU64 = AtomicU64::new(0);
static STATS_PACKETS_PASSTHROUGH: AtomicU64 = AtomicU64::new(0);
/// Counter for packets from monitored apps only
static STATS_MONITORED: AtomicU64 = AtomicU64::new(0);

/// Connection key: (local_port, remote_ip, remote_port)
type ConnectionKey = (u16, Ipv4Addr, u16);

/// Connection value: (process_id, timestamp)
type ConnectionValue = (u32, Instant);

/// Connection tracking map
type ConnectionMap = HashMap<ConnectionKey, ConnectionValue>;

/// Thread-safe connection tracker
static CONNECTION_TRACKER: once_cell::sync::Lazy<RwLock<ConnectionMap>> = 
    once_cell::sync::Lazy::new(|| RwLock::new(HashMap::new()));

/// Monitored process IDs
static MONITORED_PIDS: once_cell::sync::Lazy<RwLock<HashSet<u32>>> = 
    once_cell::sync::Lazy::new(|| RwLock::new(HashSet::new()));

/// Monitored process names (lowercase) — all PIDs with these names are monitored
static MONITORED_PROCESS_NAMES: once_cell::sync::Lazy<RwLock<HashSet<String>>> = 
    once_cell::sync::Lazy::new(|| RwLock::new(HashSet::new()));

// Note: PendingPacket queue is disabled for now - will implement in Phase 8.4
// when we understand WinDivert address types better

// =============================================================================
// PUBLIC API
// =============================================================================

// add_monitored_process_name is defined below after update_monitored_pids

/// Get all PIDs for a given process name
fn get_pids_for_process_name(name: &str) -> Vec<u32> {
    use std::process::Command;
    #[cfg(windows)]
    use std::os::windows::process::CommandExt;
    
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    
    let mut cmd = Command::new("powershell");
    cmd.args(["-Command", &format!(
        "Get-Process -Name '{}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id",
        name.trim_end_matches(".exe")
    )]);
    
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);
    
    let output = match cmd.output() {
        Ok(o) => o,
        Err(_) => return vec![],
    };
    
    let stdout = String::from_utf8_lossy(&output.stdout);
    stdout
        .lines()
        .filter_map(|line| line.trim().parse::<u32>().ok())
        .collect()
}

/// Check if a PID belongs to a monitored process by name
fn is_pid_monitored_by_name(pid: u32) -> bool {
    // First check explicit PID list (fast)
    {
        let monitored = MONITORED_PIDS.read().unwrap();
        if monitored.contains(&pid) {
            return true;
        }
    }
    
    // Then check by process name (slower, but catches new PIDs)
    let names = MONITORED_PROCESS_NAMES.read().unwrap();
    if names.is_empty() {
        return false;
    }
    
    // Get process name for this PID
    if let Some(proc_name) = get_process_name_for_pid(pid) {
        let proc_name_lower = proc_name.to_lowercase();
        if names.contains(&proc_name_lower) {
            // Add to PID cache for faster future lookups
            drop(names);
            let mut monitored = MONITORED_PIDS.write().unwrap();
            monitored.insert(pid);
            return true;
        }
    }
    
    false
}

/// Get process name for a PID (cached lookup)
pub fn get_process_name_for_pid(pid: u32) -> Option<String> {
    use std::process::Command;
    #[cfg(windows)]
    use std::os::windows::process::CommandExt;
    
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    
    let mut cmd = Command::new("powershell");
    cmd.args(["-Command", &format!(
        "(Get-Process -Id {} -ErrorAction SilentlyContinue).ProcessName",
        pid
    )]);
    
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);
    
    let output = cmd.output().ok()?;
    
    let name = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if name.is_empty() {
        None
    } else {
        Some(name)
    }
}

/// Update monitored PIDs from main app
pub fn update_monitored_pids(pids: &[u32]) {
    // Log to file for debugging
    use std::fs::OpenOptions;
    use std::io::Write;
    let mut log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open("C:\\temp\\sentinel_debug.log")
        .ok();
    
    macro_rules! debug_log {
        ($($arg:tt)*) => {
            if let Some(ref mut f) = log_file {
                let _ = writeln!(f, "{}", format!($($arg)*));
            }
        }
    }
    
    debug_log!(">>> UPDATE_MONITORED_PIDS called with: {:?}", pids);
    
    // Collect all PIDs with same process names
    let mut all_pids = HashSet::new();
    all_pids.extend(pids.iter().copied());
    
    // For each PID, find ALL PIDs with the same process name
    for &pid in pids {
        if let Some(name) = get_process_name_for_pid(pid) {
            debug_log!(">>> PID {} has name: {}", pid, name);
            
            // Add name to monitored names
            {
                let mut names = MONITORED_PROCESS_NAMES.write().unwrap();
                names.insert(name.to_lowercase());
            }
            
            // Find all PIDs with this name
            let related_pids = get_pids_for_process_name(&name);
            debug_log!(">>> Found {} PIDs for '{}': {:?}", related_pids.len(), name, related_pids);
            
            all_pids.extend(related_pids);
        }
    }
    
    // Update monitored PIDs with expanded set
    {
        let mut monitored = MONITORED_PIDS.write().unwrap();
        monitored.clear();
        monitored.extend(&all_pids);
    }
    
    debug_log!(">>> Total monitored PIDs: {} -> {:?}", all_pids.len(), all_pids);
    info!("🔧 Redirector: Monitored {} PIDs (expanded from {})", all_pids.len(), pids.len());
    
    // Scan existing connections for ALL PIDs
    for pid in &all_pids {
        scan_existing_connections(*pid);
    }
}

/// Add monitored process by name (for persistence across restarts)
/// Returns list of PIDs found for this process name
pub fn add_monitored_process_name(name: &str) -> Vec<u32> {
    let name_lower = name.to_lowercase();
    
    // Add to monitored names
    {
        let mut names = MONITORED_PROCESS_NAMES.write().unwrap();
        names.insert(name_lower.clone());
    }
    
    // Find all PIDs with this name
    let pids = get_pids_for_process_name(&name_lower);
    
    if !pids.is_empty() {
        // Add PIDs to monitored set
        let mut monitored = MONITORED_PIDS.write().unwrap();
        monitored.extend(&pids);
        
        info!("🔧 Added {} PIDs for process '{}': {:?}", pids.len(), name, pids);
        
        // Scan existing connections
        for pid in &pids {
            scan_existing_connections(*pid);
        }
    } else {
        info!("⚠️ No running instances of '{}' found", name);
    }
    
    pids
}

/// Scan existing TCP connections for a PID and add them to CONNECTION_TRACKER
fn scan_existing_connections(pid: u32) {
    use crate::tcp_table;
    
    // Use native Windows API instead of netstat subprocess
    let connections = tcp_table::get_connections_for_pid(pid);
    
    if connections.is_empty() {
        return;
    }
    
    let mut tracker = CONNECTION_TRACKER.write().unwrap();
    let now = Instant::now();
    
    for (local_port, remote_ip, remote_port) in &connections {
        let key: ConnectionKey = (*local_port, *remote_ip, *remote_port);
        let value: ConnectionValue = (pid, now);
        tracker.insert(key, value);
    }
    
    info!("📡 Scanned {} existing connections for PID {} (via Windows API)", connections.len(), pid);
}

/// Start the traffic redirector
pub fn start_redirector() {
    if REDIRECTOR_RUNNING.swap(true, Ordering::SeqCst) {
        info!("Redirector already running");
        return;
    }
    
    info!("🚀 Starting SENTINEL WinDivert Redirector v2");
    info!("📍 Ports: TARGET={}, PROXY={}, ALT={}", TARGET_PORT, PROXY_PORT, ALT_PORT);
    
    // Reset statistics
    STATS_PACKETS_SEEN.store(0, Ordering::SeqCst);
    STATS_PACKETS_REFLECTED.store(0, Ordering::SeqCst);
    STATS_PACKETS_PASSTHROUGH.store(0, Ordering::SeqCst);
    
    // Start socket tracker thread (SNIFF mode - safe)
    thread::Builder::new()
        .name("wd-socket-tracker".to_string())
        .stack_size(4 * 1024 * 1024)
        .spawn(socket_tracker_thread)
        .expect("Failed to spawn socket tracker");
    
    // Start network interceptor thread (SNIFF mode for now - debugging)
    thread::Builder::new()
        .name("wd-network-interceptor".to_string())
        .stack_size(16 * 1024 * 1024) // 16MB stack for WinDivert FFI
        .spawn(network_interceptor_thread)
        .expect("Failed to spawn network interceptor");
}

/// Stop the traffic redirector
pub fn stop_redirector() {
    REDIRECTOR_RUNNING.store(false, Ordering::SeqCst);
    info!("🛑 Redirector stop requested");
    
    // Log final stats
    info!("📊 Final stats: seen={}, reflected={}, passthrough={}",
        STATS_PACKETS_SEEN.load(Ordering::SeqCst),
        STATS_PACKETS_REFLECTED.load(Ordering::SeqCst),
        STATS_PACKETS_PASSTHROUGH.load(Ordering::SeqCst));
}

/// Get current redirect statistics (seen, reflected, passthrough, monitored)
#[allow(dead_code)]
pub fn get_redirect_stats() -> (u64, u64, u64, u64) {
    (
        STATS_PACKETS_SEEN.load(Ordering::SeqCst),
        STATS_PACKETS_REFLECTED.load(Ordering::SeqCst),
        STATS_PACKETS_PASSTHROUGH.load(Ordering::SeqCst),
        STATS_MONITORED.load(Ordering::SeqCst),
    )
}

// =============================================================================
// SOCKET TRACKER (SNIFF MODE)
// =============================================================================

/// Socket tracker thread - maps connections to PIDs
fn socket_tracker_thread() {
    // Debug log to file
    use std::fs::OpenOptions;
    use std::io::Write;
    let mut log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open("C:\\temp\\sentinel_debug.log")
        .ok();
    
    macro_rules! debug_log {
        ($($arg:tt)*) => {
            if let Some(ref mut f) = log_file {
                let _ = writeln!(f, "{}", format!($($arg)*));
                let _ = f.flush();
            }
        }
    }
    
    debug_log!("Socket tracker starting...");
    info!("🔌 Socket tracker starting...");
    
    // Socket layer filter: capture only CONNECT events (outbound connections)
    // Per WinDivert docs: BIND/LISTEN have RemoteAddr=0, only CONNECT has real addresses
    let filter = "event == CONNECT";
    let flags = WinDivertFlags::new().set_sniff();
    
    let wd = match WinDivert::<SocketLayer>::socket(filter, 0, flags) {
        Ok(handle) => handle,
        Err(e) => {
            debug_log!("Socket tracker FAILED: {}", e);
            error!("❌ Socket tracker failed: {}. Run as Administrator!", e);
            return;
        }
    };
    
    debug_log!("Socket tracker active");
    info!("✅ Socket tracker active");
    
    while REDIRECTOR_RUNNING.load(Ordering::SeqCst) {
        let event = match wd.recv(None) {
            Ok(e) => e,
            Err(_) => continue,
        };
        
        let addr = &event.address;
        let pid = addr.process_id();
        let local_port = addr.local_port();
        let remote_addr = addr.remote_address();
        let remote_port = addr.remote_port();
        
        // IPv4 only for now
        let remote_ip = match remote_addr {
            std::net::IpAddr::V4(ip) => ip,
            _ => continue,
        };
        
        // Check if monitored (by PID or by process name)
        let is_monitored = is_pid_monitored_by_name(pid);
        let monitored_pids = MONITORED_PIDS.read().unwrap().clone();
        
        // Log first 20 CONNECT events to file
        static EVENT_COUNT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
        let count = EVENT_COUNT.fetch_add(1, Ordering::SeqCst);
        if count < 20 || is_monitored {
            debug_log!("CONNECT #{}: PID {} -> {}:{} monitored={} (watching: {:?})", 
                count, pid, remote_ip, remote_port, is_monitored, monitored_pids);
        }
        
        if is_monitored {
            let key: ConnectionKey = (local_port, remote_ip, remote_port);
            let value: ConnectionValue = (pid, Instant::now());
            
            // Track connection
            {
                let mut tracker = CONNECTION_TRACKER.write().unwrap();
                tracker.insert(key, value);
                
                // Cleanup if too large
                if tracker.len() > MAX_CONNECTIONS {
                    cleanup_old_connections(&mut tracker);
                }
            }
            
            info!("📝 TRACKED: PID {} -> {}:{} (port {})", 
                pid, remote_ip, remote_port, local_port);
        }
    }
    
    info!("🔌 Socket tracker stopped");
}

/// Cleanup old connections (older than 5 minutes)
fn cleanup_old_connections(tracker: &mut ConnectionMap) {
    let now = Instant::now();
    let timeout = std::time::Duration::from_secs(300);
    
    tracker.retain(|_, (_, timestamp)| {
        now.duration_since(*timestamp) < timeout
    });
    
    info!("🧹 Cleaned up old connections, remaining: {}", tracker.len());
}

// TODO Phase 8.4: process_pending_for_key will be implemented here

// =============================================================================
// NETWORK INTERCEPTOR (RAW FFI - windivert 0.10 from GitHub)
// =============================================================================
//
// Using raw windivert::sys FFI with Windows crate types.
// This bypasses the broken high-level wrapper.

/// Network interceptor thread - RAW FFI passthrough
fn network_interceptor_thread() {
    info!("🌐 Network interceptor starting (RAW FFI 0.10)...");
    
    use std::ffi::CString;
    use std::ptr;
    
    let filter = CString::new("outbound and tcp and !loopback").unwrap();
    
    // WinDivertOpen: layer=NETWORK(0), priority=0, flags=default
    let handle = unsafe {
        windivert::sys::WinDivertOpen(
            filter.as_ptr(),
            windivert::sys::WinDivertLayer::Network,
            0,
            windivert::sys::WinDivertFlags::new(),
        )
    };
    
    // Check if handle is invalid (Windows HANDLE)
    if handle.is_invalid() {
        error!("❌ WinDivertOpen failed. Run as Administrator!");
        return;
    }
    
    info!("✅ RAW FFI WinDivert handle opened (v0.10)!");
    
    // Packet buffer (heap allocated to avoid stack overflow)
    let mut packet: Box<[u8; 65535]> = Box::new([0; 65535]);
    let mut addr: windivert::sys::address::WINDIVERT_ADDRESS = Default::default();
    let mut packet_len: u32 = 0;
    
    while REDIRECTOR_RUNNING.load(Ordering::SeqCst) {
        // Receive packet from WinDivert
        let recv_result = unsafe {
            windivert::sys::WinDivertRecv(
                handle,
                packet.as_mut_ptr() as *mut _,
                packet.len() as u32,
                &mut packet_len,
                &mut addr,
            )
        };
        
        if !recv_result.as_bool() {
            continue;
        }
        
        STATS_PACKETS_SEEN.fetch_add(1, Ordering::SeqCst);
        
        let pkt_data = &mut packet[..packet_len as usize];
        
        // Skip non-outbound packets (already redirected)
        if !addr.outbound() {
            // Reinject without modification
            unsafe {
                windivert::sys::WinDivertSend(
                    handle,
                    pkt_data.as_ptr() as *const _,
                    packet_len,
                    std::ptr::null_mut(),
                    &addr,
                );
            }
            continue;
        }
        
        // Parse packet to determine if we should reflect
        let should_reflect = if let Some(info) = parse_tcp_packet(pkt_data) {
            let key: ConnectionKey = (info.src_port, info.dst_ip, info.dst_port);
            
            // First try: lookup in CONNECTION_TRACKER (populated by Socket Layer)
            let tracker = CONNECTION_TRACKER.read().unwrap();
            let pid_from_tracker = tracker.get(&key).map(|(pid, _)| *pid);
            drop(tracker);
            
            // Fallback: use GetExtendedTcpTable API for existing connections
            let pid = pid_from_tracker.or_else(|| {
                use crate::tcp_table;
                tcp_table::get_pid_for_connection(info.src_port, info.dst_ip, info.dst_port)
            });
            
            // Debug logging for first monitored packets
            #[allow(dead_code)]
            static LOGGED_COUNT: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);
            let is_monitored = pid.map(|p| {
                let monitored = MONITORED_PIDS.read().unwrap();
                monitored.contains(&p)
            }).unwrap_or(false);
            
            if is_monitored {
                // Count monitored packets for statistics
                STATS_MONITORED.fetch_add(1, Ordering::SeqCst);
                
                // Get app name for logging
                let app_name = pid
                    .and_then(|p| get_process_name_for_pid(p))
                    .unwrap_or_else(|| format!("PID:{:?}", pid));
                
                // Also log to debug file (with limit to prevent disk fill)
                static FILE_LOG_COUNT: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);
                let log_count = FILE_LOG_COUNT.fetch_add(1, Ordering::SeqCst);
                
                // Log to UI (no limit - UI manages its own buffer)
                use crate::logging;
                use crate::log_info;
                
                // Debug first 10 entries
                if log_count < 10 {
                    use std::fs::OpenOptions;
                    use std::io::Write;
                    if let Ok(mut f) = OpenOptions::new()
                        .create(true)
                        .append(true)
                        .open("C:\\temp\\sentinel_debug.log") 
                    {
                        let _ = writeln!(f, ">>> log_info! CALLED for {}", app_name);
                    }
                }
                
                log_info!(
                    logging::LogCategory::Network, 
                    app_name.clone(), 
                    "{} -> {}:{}", app_name, info.dst_ip, info.dst_port
                );
                
                // Also log to debug file
                if log_count < 500 {
                    use std::fs::OpenOptions;
                    use std::io::Write;
                    if let Ok(mut f) = OpenOptions::new()
                        .create(true)
                        .append(true)
                        .open("C:\\temp\\sentinel_debug.log") 
                    {
                        let _ = writeln!(f, "MONITORED: {} -> {}:{}", 
                            app_name, info.dst_ip, info.dst_port);
                    }
                }
            }
            
            if let Some(pid) = pid {
                let monitored = MONITORED_PIDS.read().unwrap();
                if monitored.contains(&pid) {
                    // Skip localhost, NAT IP, and traffic to proxy port (prevents loop)
                    let ihl = ((pkt_data[0] & 0x0F) as usize) * 4;
                    let dst_octets = [pkt_data[16], pkt_data[17], pkt_data[18], pkt_data[19]];
                    let dst_port = ((pkt_data[ihl + 2] as u16) << 8) | (pkt_data[ihl + 3] as u16);
                    let is_localhost = dst_octets[0] == 127;
                    let is_nat_ip = dst_octets == NAT_PROXY_IP;
                    let is_proxy_traffic = dst_port == PROXY_PORT; // Already redirected
                    
                    if is_localhost || is_nat_ip || is_proxy_traffic {
                        false // Don't intercept local/proxy traffic
                    } else {
                        if info.is_syn {
                            info!("🔄 REFLECT SYN: PID {} -> {}:{} => 10.255.255.1:{}", 
                                pid, info.dst_ip, info.dst_port, PROXY_PORT);
                        }
                        true
                    }
                } else {
                    false
                }
            } else {
                false
            }
        } else {
            false
        };
        
        if should_reflect {
            STATS_PACKETS_REFLECTED.fetch_add(1, Ordering::SeqCst);
            
            // === REFLECTION MODE ===
            // Redirect monitored traffic to MITM proxy using packet reflection.
            // This allows TLS interception for content analysis.
            
            // Reflect packet: App->Remote becomes Remote->Proxy (inbound)
            let mut is_outbound = addr.outbound();
            reflect_to_proxy(pkt_data, &mut is_outbound);
            
            // Update address direction
            addr.set_outbound(is_outbound);
            
            // Reinject reflected packet
            let send_result = unsafe {
                windivert::sys::WinDivertSend(
                    handle,
                    pkt_data.as_ptr() as *const _,
                    packet_len,
                    ptr::null_mut(),
                    &addr,
                )
            };
            
            if !send_result.as_bool() {
                let error = unsafe { windows::Win32::Foundation::GetLastError() };
                warn!("❌ WinDivertSend (reflect) failed: {:?}", error);
            }
            
            continue; // Don't passthrough - we've already sent the reflected packet
        } else {
            STATS_PACKETS_PASSTHROUGH.fetch_add(1, Ordering::SeqCst);
            
            // Passthrough: recalc checksums for offloading
            let ihl = ((pkt_data[0] & 0x0F) as usize) * 4;
            if pkt_data.len() >= ihl + 20 {
                recalc_ip_checksum(pkt_data, ihl);
                recalc_tcp_checksum(pkt_data, ihl);
            }
        }
        
        // Reinject (reflected or passthrough)
        let send_result = unsafe {
            windivert::sys::WinDivertSend(
                handle,
                pkt_data.as_ptr() as *const _,
                packet_len,
                ptr::null_mut(),
                &addr,
            )
        };
        
        if !send_result.as_bool() {
            // Get Windows error code for debugging
            let error = unsafe { windows::Win32::Foundation::GetLastError() };
            warn!("❌ WinDivertSend failed: OS error {:?}", error);
            
            // Log to file for debugging
            use std::fs::OpenOptions;
            use std::io::Write;
            if let Ok(mut f) = OpenOptions::new()
                .create(true)
                .append(true)
                .open("C:\\temp\\sentinel_debug.log") 
            {
                let _ = writeln!(f, "WINDIVERT SEND FAILED: error {:?}", error);
            }
        }
    }
    
    unsafe {
        windivert::sys::WinDivertClose(handle);
    }
    
    info!("🌐 Network interceptor stopped");
}

// =============================================================================
// PACKET PARSING HELPERS
// =============================================================================

/// Parsed TCP packet info
#[derive(Debug)]
#[allow(dead_code)]
struct TcpPacketInfo {
    src_ip: Ipv4Addr,
    dst_ip: Ipv4Addr,
    src_port: u16,
    dst_port: u16,
    is_syn: bool,
    is_ack: bool,
    is_fin: bool,
    is_rst: bool,
}

/// Parse TCP/IP packet headers
fn parse_tcp_packet(data: &[u8]) -> Option<TcpPacketInfo> {
    // Minimum IP + TCP header size
    if data.len() < 40 {
        return None;
    }
    
    // Check IPv4
    let version = (data[0] >> 4) & 0x0F;
    if version != 4 {
        return None;
    }
    
    // IP header length
    let ihl = ((data[0] & 0x0F) as usize) * 4;
    if data.len() < ihl + 20 {
        return None;
    }
    
    // Check TCP protocol
    if data[9] != 6 {
        return None;
    }
    
    // Parse addresses
    let src_ip = Ipv4Addr::new(data[12], data[13], data[14], data[15]);
    let dst_ip = Ipv4Addr::new(data[16], data[17], data[18], data[19]);
    
    // Parse ports
    let src_port = u16::from_be_bytes([data[ihl], data[ihl + 1]]);
    let dst_port = u16::from_be_bytes([data[ihl + 2], data[ihl + 3]]);
    
    // Parse TCP flags
    let tcp_flags = data[ihl + 13];
    let is_syn = (tcp_flags & 0x02) != 0;
    let is_ack = (tcp_flags & 0x10) != 0;
    let is_fin = (tcp_flags & 0x01) != 0;
    let is_rst = (tcp_flags & 0x04) != 0;
    
    Some(TcpPacketInfo {
        src_ip,
        dst_ip,
        src_port,
        dst_port,
        is_syn,
        is_ack,
        is_fin,
        is_rst,
    })
}

/// Format IP address for logging
#[allow(dead_code)]
fn format_ip(ip: &[u8; 4]) -> String {
    format!("{}.{}.{}.{}", ip[0], ip[1], ip[2], ip[3])
}

// =============================================================================
// REFLECTION FUNCTIONS (TO BE IMPLEMENTED)
// =============================================================================

/// Reflect packet to proxy (App -> Remote becomes Remote -> Proxy)
#[allow(dead_code)]
fn reflect_to_proxy(packet: &mut [u8], outbound: &mut bool) {
    if packet.len() < 40 {
        return;
    }
    
    let ihl = ((packet[0] & 0x0F) as usize) * 4;
    
    // Swap src and dst IP addresses
    let mut src_ip = [0u8; 4];
    let mut dst_ip = [0u8; 4];
    src_ip.copy_from_slice(&packet[12..16]);
    dst_ip.copy_from_slice(&packet[16..20]);
    packet[12..16].copy_from_slice(&dst_ip);
    packet[16..20].copy_from_slice(&src_ip);
    
    // Change dst port to PROXY_PORT
    packet[ihl + 2] = (PROXY_PORT >> 8) as u8;
    packet[ihl + 3] = (PROXY_PORT & 0xFF) as u8;
    
    // Flip direction: outbound -> inbound
    *outbound = false;
    
    // Recalculate checksums
    recalc_ip_checksum(packet, ihl);
    recalc_tcp_checksum(packet, ihl);
}

/// Reflect response from proxy back to app
#[allow(dead_code)]
fn reflect_to_client(packet: &mut [u8], outbound: &mut bool) {
    if packet.len() < 40 {
        return;
    }
    
    let ihl = ((packet[0] & 0x0F) as usize) * 4;
    
    // Swap src and dst IP addresses
    let mut src_ip = [0u8; 4];
    let mut dst_ip = [0u8; 4];
    src_ip.copy_from_slice(&packet[12..16]);
    dst_ip.copy_from_slice(&packet[16..20]);
    packet[12..16].copy_from_slice(&dst_ip);
    packet[16..20].copy_from_slice(&src_ip);
    
    // Restore src port to TARGET_PORT (443)
    packet[ihl] = (TARGET_PORT >> 8) as u8;
    packet[ihl + 1] = (TARGET_PORT & 0xFF) as u8;
    
    // Flip direction
    *outbound = false;
    
    // Recalculate checksums
    recalc_ip_checksum(packet, ihl);
    recalc_tcp_checksum(packet, ihl);
}

/// Redirect ALT_PORT to TARGET_PORT
#[allow(dead_code)]
fn redirect_alt_to_target(packet: &mut [u8]) {
    if packet.len() < 40 {
        return;
    }
    
    let ihl = ((packet[0] & 0x0F) as usize) * 4;
    
    // Change dst port from ALT_PORT to TARGET_PORT
    packet[ihl + 2] = (TARGET_PORT >> 8) as u8;
    packet[ihl + 3] = (TARGET_PORT & 0xFF) as u8;
    
    recalc_ip_checksum(packet, ihl);
    recalc_tcp_checksum(packet, ihl);
}

/// Redirect response from TARGET_PORT to ALT_PORT
#[allow(dead_code)]
fn redirect_target_to_alt(packet: &mut [u8]) {
    if packet.len() < 40 {
        return;
    }
    
    let ihl = ((packet[0] & 0x0F) as usize) * 4;
    
    // Change src port from TARGET_PORT to ALT_PORT
    packet[ihl] = (ALT_PORT >> 8) as u8;
    packet[ihl + 1] = (ALT_PORT & 0xFF) as u8;
    
    recalc_ip_checksum(packet, ihl);
    recalc_tcp_checksum(packet, ihl);
}

// =============================================================================
// CHECKSUM CALCULATION
// =============================================================================

/// Recalculate IP header checksum
fn recalc_ip_checksum(packet: &mut [u8], ihl: usize) {
    // Zero out checksum field
    packet[10] = 0;
    packet[11] = 0;
    
    // Calculate checksum
    let mut sum: u32 = 0;
    for i in (0..ihl).step_by(2) {
        let word = ((packet[i] as u32) << 8) | (packet[i + 1] as u32);
        sum += word;
    }
    
    // Fold 32-bit sum to 16 bits
    while (sum >> 16) != 0 {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    
    let checksum = !sum as u16;
    packet[10] = (checksum >> 8) as u8;
    packet[11] = (checksum & 0xFF) as u8;
}

/// Recalculate TCP checksum
fn recalc_tcp_checksum(packet: &mut [u8], ihl: usize) {
    let tcp_len = packet.len() - ihl;
    
    // Zero out checksum field  
    packet[ihl + 16] = 0;
    packet[ihl + 17] = 0;
    
    // Pseudo header sum
    let mut sum: u32 = 0;
    
    // Source IP
    sum += ((packet[12] as u32) << 8) | (packet[13] as u32);
    sum += ((packet[14] as u32) << 8) | (packet[15] as u32);
    
    // Dest IP
    sum += ((packet[16] as u32) << 8) | (packet[17] as u32);
    sum += ((packet[18] as u32) << 8) | (packet[19] as u32);
    
    // Protocol (TCP = 6)
    sum += 6;
    
    // TCP length
    sum += tcp_len as u32;
    
    // TCP segment
    for i in (ihl..packet.len()).step_by(2) {
        if i + 1 < packet.len() {
            let word = ((packet[i] as u32) << 8) | (packet[i + 1] as u32);
            sum += word;
        } else {
            sum += (packet[i] as u32) << 8;
        }
    }
    
    // Fold
    while (sum >> 16) != 0 {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    
    let checksum = !sum as u16;
    packet[ihl + 16] = (checksum >> 8) as u8;
    packet[ihl + 17] = (checksum & 0xFF) as u8;
}
