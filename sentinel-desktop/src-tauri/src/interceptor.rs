//! SENTINEL Desktop - WinDivert Network Interceptor
//!
//! Intercepts ALL network traffic from monitored applications.
//! Uses WinDivert in SNIFF mode for safer operation.

use std::sync::{Arc, atomic::Ordering};
use std::thread;
use std::collections::HashSet;
use tracing::{info, error};
use windivert::prelude::*;

use crate::{AppState, LogEntry, AI_ENDPOINTS};

/// Start WinDivert interceptor in background thread
pub fn start_interceptor(state: Arc<AppState>) {
    thread::Builder::new()
        .name("windivert-interceptor".to_string())
        .stack_size(8 * 1024 * 1024) // 8MB stack for safety
        .spawn(move || {
            run_interceptor_impl(state);
        })
        .expect("Failed to spawn interceptor thread");
}

fn run_interceptor_impl(state: Arc<AppState>) {
    info!("Starting WinDivert interceptor (sniff mode)...");
    
    // Use SNIFF mode - just observe packets, don't intercept
    let filter = "outbound and tcp.DstPort == 443 and tcp.PayloadLength > 0";
    
    let flags = WinDivertFlags::new().set_sniff(); // SNIFF mode - read-only
    
    let wd = match WinDivert::<NetworkLayer>::network(filter, 0, flags) {
        Ok(handle) => handle,
        Err(e) => {
            error!("WinDivert error: {}. Run as Administrator!", e);
            return;
        }
    };
    
    info!("WinDivert opened in SNIFF mode");
    state.running.store(true, Ordering::SeqCst);
    
    let mut seen: HashSet<String> = HashSet::new();
    
    loop {
        if !state.intercept_enabled.load(Ordering::SeqCst) {
            thread::sleep(std::time::Duration::from_millis(100));
            continue;
        }
        
        // Receive packet (in sniff mode, packet continues normally)
        let packet = match wd.recv(None) {
            Ok(p) => p,
            Err(_) => continue,
        };
        
        let data = packet.data;
        
        // Extract SNI from TLS ClientHello
        if let Some(payload) = extract_tcp_payload(&data) {
            if let Some(sni) = extract_sni(payload) {
                if !seen.contains(&sni) {
                    seen.insert(sni.clone());
                    
                    // Check if from monitored process
                    let monitored = state.monitored_processes.read().unwrap();
                    if !monitored.is_empty() {
                        let is_ai = is_ai_endpoint(&sni);
                        let status = if is_ai { "ai" } else { "allowed" };
                        
                        log_connection(&state, &sni, status, data.len() as u64, is_ai);
                    }
                }
                
                if seen.len() > 500 { seen.clear(); }
            }
        }
    }
}

fn extract_tcp_payload(packet: &[u8]) -> Option<&[u8]> {
    if packet.len() < 40 { return None; }
    
    let version = (packet[0] >> 4) & 0x0F;
    if version != 4 { return None; }
    
    let ihl = (packet[0] & 0x0F) as usize * 4;
    if packet.len() < ihl + 20 { return None; }
    if packet[9] != 6 { return None; }
    
    let tcp_start = ihl;
    let data_offset = ((packet[tcp_start + 12] >> 4) & 0x0F) as usize * 4;
    let payload_start = tcp_start + data_offset;
    
    if payload_start >= packet.len() { return None; }
    Some(&packet[payload_start..])
}

pub fn extract_sni(payload: &[u8]) -> Option<String> {
    if payload.len() < 43 { return None; }
    if payload[0] != 0x16 || payload.get(5) != Some(&0x01) { return None; }
    
    let session_id_len = *payload.get(43)? as usize;
    let mut offset = 44 + session_id_len;
    
    if offset + 2 > payload.len() { return None; }
    let cipher_len = u16::from_be_bytes([payload[offset], payload[offset + 1]]) as usize;
    offset += 2 + cipher_len;
    
    if offset >= payload.len() { return None; }
    let comp_len = payload[offset] as usize;
    offset += 1 + comp_len;
    
    if offset + 2 > payload.len() { return None; }
    let ext_len = u16::from_be_bytes([payload[offset], payload[offset + 1]]) as usize;
    offset += 2;
    
    let ext_end = offset + ext_len;
    
    while offset + 4 <= ext_end && offset + 4 <= payload.len() {
        let ext_type = u16::from_be_bytes([payload[offset], payload[offset + 1]]);
        let len = u16::from_be_bytes([payload[offset + 2], payload[offset + 3]]) as usize;
        offset += 4;
        
        if ext_type == 0x0000 {
            if offset + 5 > payload.len() { return None; }
            offset += 3; // Skip list len + type
            let host_len = u16::from_be_bytes([payload[offset], payload[offset + 1]]) as usize;
            offset += 2;
            
            if offset + host_len <= payload.len() {
                return String::from_utf8(payload[offset..offset + host_len].to_vec()).ok();
            }
        }
        offset += len;
    }
    None
}

fn is_ai_endpoint(hostname: &str) -> bool {
    AI_ENDPOINTS.iter().any(|ep| hostname.contains(ep))
}

fn log_connection(state: &AppState, endpoint: &str, status: &str, bytes: u64, is_ai: bool) {
    use chrono::Local;
    
    let entry = LogEntry {
        timestamp: Local::now().format("%H:%M:%S").to_string(),
        endpoint: if is_ai { format!("🤖 {}", endpoint) } else { endpoint.to_string() },
        app_name: "Monitored".to_string(),
        status: status.to_string(),
        bytes,
    };
    
    let mut logs = state.logs.lock().unwrap();
    logs.insert(0, entry);
    if logs.len() > 100 { logs.pop(); }
    
    let mut stats = state.stats.lock().unwrap();
    stats.total_connections += 1;
    stats.bytes_inspected += bytes;
    stats.allowed_connections += 1;
    
    // Enhanced logging
    let category = if is_ai {
        crate::logging::LogCategory::Security
    } else {
        crate::logging::LogCategory::Network
    };
    
    let level = if is_ai {
        crate::logging::LogLevel::Warn
    } else {
        crate::logging::LogLevel::Info
    };
    
    crate::logging::logger().log(
        crate::logging::EnhancedLogEntry::new(level, category, "Connection", format!("{} ({} bytes) - {}", endpoint, bytes, status))
    );
}
