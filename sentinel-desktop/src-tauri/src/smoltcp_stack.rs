//! smoltcp Stack Runner — User-space TCP/IP stack
//!
//! Simplified: no separate collector, direct tx_queue access from stack task

#![allow(unused)]

use std::collections::VecDeque;
use std::sync::Arc;
use netstack_smoltcp::{StackBuilder, TcpListener, TcpStream};
use futures_util::{StreamExt, SinkExt};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::sync::mpsc;
use tracing::{info, warn, debug, error};

use crate::proxy::ca::CertificateAuthority;
use crate::AppState;

/// Packet channels for WinDivert <-> smoltcp communication
pub struct SmoltcpChannels {
    pub rx_queue: Arc<std::sync::Mutex<VecDeque<Vec<u8>>>>,
    pub tx_queue: Arc<std::sync::Mutex<VecDeque<Vec<u8>>>>,
}

pub fn create_stack_channels() -> SmoltcpChannels {
    SmoltcpChannels {
        rx_queue: Arc::new(std::sync::Mutex::new(VecDeque::with_capacity(4096))),
        tx_queue: Arc::new(std::sync::Mutex::new(VecDeque::with_capacity(4096))),
    }
}

pub static SMOLTCP_CHANNELS: once_cell::sync::Lazy<SmoltcpChannels> = 
    once_cell::sync::Lazy::new(create_stack_channels);

pub fn run_stack_loop(
    channels: SmoltcpChannels,
    ca: Arc<CertificateAuthority>,
    _state: Arc<AppState>,
) {
    info!("🚀 Starting smoltcp stack (direct tx_queue mode)");
    
    let rt = tokio::runtime::Runtime::new().expect("Failed to create tokio runtime");
    
    rt.block_on(async move {
        let (stack, runner, _udp_socket, tcp_listener) = match StackBuilder::default()
            .enable_tcp(true)
            .enable_udp(false)
            .tcp_buffer_size(65535)
            .build() 
        {
            Ok(result) => result,
            Err(e) => {
                error!("Failed to build smoltcp stack: {}", e);
                return;
            }
        };
        
        let mut tcp_listener = match tcp_listener {
            Some(l) => l,
            None => {
                error!("TCP listener not created");
                return;
            }
        };
        
        use std::fs::OpenOptions;
        use std::io::Write;
        if let Ok(mut f) = OpenOptions::new()
            .create(true)
            .append(true)
            .open("C:\\temp\\sentinel_debug.log") 
        {
            let _ = writeln!(f, "NETSTACK: direct tx_queue mode starting");
        }
        
        if let Some(runner) = runner {
            tokio::spawn(async move {
                let _ = runner.await;
            });
        }
        
        // Feeder channel
        let (stack_input_tx, mut stack_input_rx) = mpsc::channel::<Vec<u8>>(4096);
        
        // Stack I/O task - DIRECTLY writes to tx_queue (no collector)
        let tx_queue_clone = Arc::clone(&channels.tx_queue);
        tokio::spawn(async move {
            use std::fs::OpenOptions;
            use std::io::Write;
            
            if let Ok(mut f) = OpenOptions::new()
                .create(true)
                .append(true)
                .open("C:\\temp\\sentinel_debug.log") 
            {
                let _ = writeln!(f, "STACK IO: started (direct tx_queue)");
            }
            
            let mut stack = stack;
            let mut tx_count = 0u32;
            let mut rx_count = 0u32;
            
            loop {
                tokio::select! {
                    Some(pkt) = stack_input_rx.recv() => {
                        rx_count += 1;
                        if let Err(e) = stack.send(pkt).await {
                            debug!("Stack send error: {:?}", e);
                        }
                    }
                    
                    result = stack.next() => {
                        if let Some(Ok(pkt)) = result {
                            tx_count += 1;
                            let pkt_len = pkt.len();
                            
                            // DIRECTLY put into tx_queue
                            {
                                let mut queue = tx_queue_clone.lock().unwrap();
                                if queue.len() < 8192 {
                                    queue.push_back(pkt);
                                }
                            }
                            
                            if tx_count % 5 == 0 {
                                if let Ok(mut f) = OpenOptions::new()
                                    .create(true)
                                    .append(true)
                                    .open("C:\\temp\\sentinel_debug.log") 
                                {
                                    let _ = writeln!(f, "STACK TX: {} pkts to tx_queue (last {}b)", tx_count, pkt_len);
                                }
                            }
                        }
                    }
                }
            }
        });
        
        // Feeder task
        let rx_queue = Arc::clone(&channels.rx_queue);
        let input_tx = stack_input_tx.clone();
        tokio::spawn(async move {
            loop {
                let packet = {
                    let mut queue = rx_queue.lock().unwrap();
                    queue.pop_front()
                };
                
                if let Some(pkt) = packet {
                    if input_tx.send(pkt).await.is_err() {
                        break;
                    }
                }
                
                tokio::time::sleep(tokio::time::Duration::from_micros(50)).await;
            }
        });
        
        // Main accept loop
        while let Some((stream, local_addr, peer_addr)) = tcp_listener.next().await {
            if let Ok(mut f) = OpenOptions::new()
                .create(true)
                .append(true)
                .open("C:\\temp\\sentinel_debug.log") 
            {
                let _ = writeln!(f, "NETSTACK ACCEPT: {} -> {}", peer_addr, local_addr);
            }
            
            let ca = Arc::clone(&ca);
            tokio::spawn(async move {
                handle_connection(stream, ca).await;
            });
        }
    });
}

async fn handle_connection(
    mut stream: TcpStream,
    _ca: Arc<CertificateAuthority>,
) {
    let mut buffer = [0u8; 4096];
    
    match stream.read(&mut buffer).await {
        Ok(n) if n > 0 => {
            use std::fs::OpenOptions;
            use std::io::Write;
            if let Ok(mut f) = OpenOptions::new()
                .create(true)
                .append(true)
                .open("C:\\temp\\sentinel_debug.log") 
            {
                let _ = writeln!(f, "NETSTACK RECV: {} bytes", n);
            }
        }
        _ => {}
    }
}
