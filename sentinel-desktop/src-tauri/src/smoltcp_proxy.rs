//! smoltcp Proxy — User-space TCP/IP stack based transparent proxy
//!
//! This module uses netstack-smoltcp to receive TCP connections from
//! WinDivert-captured packets and process them through our TLS inspection pipeline.

#![allow(unused)]

use std::net::SocketAddr;
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tracing::{info, warn, error, debug};

use netstack_smoltcp::{StackBuilder, TcpListener, TcpStream as SmolTcpStream};

use crate::packet_device::{PacketReceiver, PacketInjector, NAT_TABLE};
use crate::proxy::ca::CertificateAuthority;
use crate::AppState;

/// Proxy port that smoltcp TcpListener will bind to
const PROXY_PORT: u16 = 8443;

/// Run the smoltcp-based transparent proxy
/// 
/// This function:
/// 1. Creates a smoltcp Stack using packets from WinDivert
/// 2. Listens for TCP connections on PROXY_PORT
/// 3. Handles each connection with TLS MITM inspection
pub async fn run_smoltcp_proxy(
    mut packet_rx: PacketReceiver,
    packet_tx: PacketInjector,
    ca: Arc<CertificateAuthority>,
    state: Arc<AppState>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    info!("🚀 Starting smoltcp transparent proxy on port {}", PROXY_PORT);
    
    // Create a channel pair for the smoltcp stack device
    let (device_tx, mut device_rx) = tokio::sync::mpsc::channel::<Vec<u8>>(4096);
    let (stack_tx, mut stack_rx) = tokio::sync::mpsc::channel::<Vec<u8>>(4096);
    
    // Spawn packet feeder task: WinDivert packets -> smoltcp
    let feeder_handle = tokio::spawn(async move {
        while let Some(captured) = packet_rx.receive().await {
            // Register in NAT table for later lookup
            NAT_TABLE.register(
                captured.original_src_port,
                captured.original_dst_ip,
                captured.original_dst_port,
                captured.pid,
            );
            
            // Feed raw packet data to smoltcp
            if let Err(e) = device_tx.send(captured.data).await {
                warn!("Failed to feed packet to smoltcp: {}", e);
            }
        }
        info!("Packet feeder task ended");
    });
    
    // Spawn packet collector task: smoltcp -> WinDivert
    let collector_tx = packet_tx.clone();
    let collector_handle = tokio::spawn(async move {
        while let Some(data) = stack_rx.recv().await {
            if let Err(e) = collector_tx.inject(data).await {
                warn!("Failed to inject packet from smoltcp: {}", e);
            }
        }
        info!("Packet collector task ended");
    });
    
    // Build the smoltcp stack
    // Note: netstack-smoltcp uses a different device model than raw smoltcp
    // We'll use a simplified approach for now
    
    info!("📡 smoltcp stack initialized, accepting connections...");
    
    // For now, create a simple TCP listener using tokio
    // In full implementation, this would use smoltcp's TcpListener
    let addr: SocketAddr = format!("0.0.0.0:{}", PROXY_PORT).parse()?;
    let listener = tokio::net::TcpListener::bind(addr).await?;
    
    info!("✅ smoltcp proxy listening on {}", addr);
    
    // Debug logging
    use std::fs::OpenOptions;
    use std::io::Write;
    if let Ok(mut f) = OpenOptions::new()
        .create(true)
        .append(true)
        .open("C:\\temp\\sentinel_debug.log") 
    {
        let _ = writeln!(f, "SMOLTCP PROXY: listening on {}", addr);
    }
    
    loop {
        match listener.accept().await {
            Ok((stream, peer_addr)) => {
                info!("📥 SMOLTCP ACCEPT: connection from {}", peer_addr);
                
                // Debug log
                if let Ok(mut f) = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open("C:\\temp\\sentinel_debug.log") 
                {
                    let _ = writeln!(f, "SMOLTCP ACCEPT: connection from {}", peer_addr);
                }
                
                // Look up original destination from NAT table
                let original_dest = NAT_TABLE.lookup(peer_addr.port());
                
                let ca_clone = ca.clone();
                let state_clone = state.clone();
                
                tokio::spawn(async move {
                    if let Err(e) = handle_connection(stream, peer_addr, original_dest, ca_clone, state_clone).await {
                        warn!("Connection handler error: {}", e);
                    }
                });
            }
            Err(e) => {
                error!("Accept error: {}", e);
            }
        }
    }
}

/// Handle a single proxied connection
async fn handle_connection(
    mut client_stream: tokio::net::TcpStream,
    peer_addr: SocketAddr,
    original_dest: Option<([u8; 4], u16, Option<u32>)>,
    ca: Arc<CertificateAuthority>,
    state: Arc<AppState>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let (dst_ip, dst_port, pid) = match original_dest {
        Some(dest) => dest,
        None => {
            warn!("No NAT entry for port {}, dropping connection", peer_addr.port());
            return Ok(());
        }
    };
    
    let dst_ip_str = format!("{}.{}.{}.{}", dst_ip[0], dst_ip[1], dst_ip[2], dst_ip[3]);
    info!("🔗 Proxying {} -> {}:{} (PID: {:?})", peer_addr, dst_ip_str, dst_port, pid);
    
    // Debug log
    use std::fs::OpenOptions;
    use std::io::Write;
    if let Ok(mut f) = OpenOptions::new()
        .create(true)
        .append(true)
        .open("C:\\temp\\sentinel_debug.log") 
    {
        let _ = writeln!(f, "SMOLTCP PROXY: {} -> {}:{} (PID: {:?})", peer_addr, dst_ip_str, dst_port, pid);
    }
    
    // Connect to the original destination
    let server_addr: SocketAddr = format!("{}:{}", dst_ip_str, dst_port).parse()?;
    let mut server_stream = match tokio::net::TcpStream::connect(server_addr).await {
        Ok(s) => s,
        Err(e) => {
            warn!("Failed to connect to {}: {}", server_addr, e);
            return Err(e.into());
        }
    };
    
    info!("✅ Connected to upstream {}", server_addr);
    
    // For now, simple bidirectional copy (no TLS inspection yet)
    // In full implementation, we would:
    // 1. Perform TLS handshake with client using generated cert
    // 2. Perform TLS handshake with server
    // 3. Decrypt, analyze, re-encrypt
    
    let (mut client_read, mut client_write) = client_stream.split();
    let (mut server_read, mut server_write) = server_stream.split();
    
    let client_to_server = async {
        let mut buf = vec![0u8; 8192];
        loop {
            match client_read.read(&mut buf).await {
                Ok(0) => break,
                Ok(n) => {
                    if server_write.write_all(&buf[..n]).await.is_err() {
                        break;
                    }
                }
                Err(_) => break,
            }
        }
    };
    
    let server_to_client = async {
        let mut buf = vec![0u8; 8192];
        loop {
            match server_read.read(&mut buf).await {
                Ok(0) => break,
                Ok(n) => {
                    if client_write.write_all(&buf[..n]).await.is_err() {
                        break;
                    }
                }
                Err(_) => break,
            }
        }
    };
    
    // Run both directions concurrently
    tokio::select! {
        _ = client_to_server => {}
        _ = server_to_client => {}
    }
    
    debug!("Connection {} closed", peer_addr);
    Ok(())
}
