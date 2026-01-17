//! HTTPS Proxy Server
//!
//! Handles CONNECT requests and performs TLS inspection.

use std::sync::Arc;
use std::net::SocketAddr;
use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio_rustls::{TlsAcceptor, TlsConnector};
use rustls::{ClientConfig, ServerConfig};
use rustls::pki_types::ServerName;
use tracing::{info, error};

use super::CertificateAuthority;
use crate::engines::{self, EngineConfig, AnalysisResult, ThreatLevel};

/// HTTPS Proxy Server
pub struct ProxyServer {
    ca: Arc<CertificateAuthority>,
    listen_addr: SocketAddr,
    engine_config: EngineConfig,
}

impl ProxyServer {
    pub fn new(ca: Arc<CertificateAuthority>, listen_addr: SocketAddr) -> Self {
        Self {
            ca,
            listen_addr,
            engine_config: EngineConfig::default(),
        }
    }
    
    /// Start the proxy server
    pub async fn run(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let listener = TcpListener::bind(&self.listen_addr).await?;
        info!("SENTINEL Proxy listening on {}", self.listen_addr);
        
        loop {
            let (stream, peer_addr) = listener.accept().await?;
            let ca = Arc::clone(&self.ca);
            let engine_config = self.engine_config.clone();
            
            tokio::spawn(async move {
                if let Err(e) = handle_connection(stream, peer_addr, ca, engine_config).await {
                    error!("Connection error from {}: {}", peer_addr, e);
                }
            });
        }
    }
}

/// Handle a single connection
async fn handle_connection(
    mut stream: TcpStream,
    _peer_addr: SocketAddr,
    ca: Arc<CertificateAuthority>,
    engine_config: EngineConfig,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let mut buf = vec![0u8; 4096];
    let n = stream.read(&mut buf).await?;
    
    if n == 0 {
        return Ok(());
    }
    
    let request = String::from_utf8_lossy(&buf[..n]);
    
    // Check for CONNECT request (HTTPS tunnel)
    if request.starts_with("CONNECT ") {
        let host = extract_host(&request)?;
        info!("CONNECT tunnel to: {}", host);
        
        // Log to debug file
        {
            use std::fs::OpenOptions;
            use std::io::Write;
            if let Ok(mut f) = OpenOptions::new()
                .create(true)
                .append(true)
                .open("C:\\temp\\sentinel_debug.log") 
            {
                let _ = writeln!(f, "PROXY CONNECT: {}", host);
            }
        }
        
        // Only log AI API endpoints (not all traffic)
        // WinDivert handles per-app logging
        let is_ai = crate::AI_ENDPOINTS.iter().any(|ep| host.contains(ep));
        
        // Increment proxy statistics
        super::inc_proxy_connection();
        if is_ai {
            super::inc_ai_connection();
        }
        
        // Log ALL connections to UI (proxy handles all traffic when System Proxy enabled)
        crate::logging::logger().log(
            crate::logging::EnhancedLogEntry::new(
                if is_ai { crate::logging::LogLevel::Warn } else { crate::logging::LogLevel::Info },
                crate::logging::LogCategory::Network, 
                "Proxy", 
                format!("{}{}", if is_ai { "🤖 " } else { "" }, host)
            )
        );
        // Non-AI traffic is not logged to reduce noise
        
        // Send 200 Connection Established
        stream.write_all(b"HTTP/1.1 200 Connection Established\r\n\r\n").await?;
        
        if is_ai {
            // AI endpoints: Perform TLS MITM for inspection
            handle_tls_tunnel(stream, &host, ca, engine_config).await?;
        } else {
            // Non-AI: Simple TCP passthrough (no TLS termination = no cert issues)
            handle_passthrough(stream, &host).await?;
        }
    } else {
        // Plain HTTP - just log and forward (not recommended for AI APIs)
        info!("Plain HTTP request (not intercepted)");
    }
    
    Ok(())
}

/// Extract host from CONNECT request
fn extract_host(request: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    // CONNECT api.openai.com:443 HTTP/1.1
    let parts: Vec<&str> = request.split_whitespace().collect();
    if parts.len() < 2 {
        return Err("Invalid CONNECT request".into());
    }
    
    let host_port = parts[1];
    let host = host_port.split(':').next().unwrap_or(host_port);
    
    Ok(host.to_string())
}

/// Handle simple TCP passthrough (no TLS termination)
/// This is used for non-AI traffic to avoid certificate pinning issues
async fn handle_passthrough(
    mut client_stream: TcpStream,
    host: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Connect to the actual server
    let server_addr = format!("{}:443", host);
    let mut server_stream = TcpStream::connect(&server_addr).await?;
    
    // Simple bidirectional copy - no TLS termination
    // Client thinks it's talking directly to server
    let (mut client_read, mut client_write) = client_stream.split();
    let (mut server_read, mut server_write) = server_stream.split();
    
    let client_to_server = tokio::io::copy(&mut client_read, &mut server_write);
    let server_to_client = tokio::io::copy(&mut server_read, &mut client_write);
    
    // Wait for either direction to complete
    tokio::select! {
        _ = client_to_server => {},
        _ = server_to_client => {},
    }
    
    Ok(())
}

/// Handle TLS tunnel with MITM inspection
async fn handle_tls_tunnel(
    client_stream: TcpStream,
    host: &str,
    ca: Arc<CertificateAuthority>,
    engine_config: EngineConfig,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Generate certificate for this host
    let (cert, key) = ca.generate_cert_for_host(host)?;
    
    // Create server config for client connection
    let server_config = ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert], key)?;
    
    let acceptor = TlsAcceptor::from(Arc::new(server_config));
    
    // Accept TLS from client
    let mut client_tls = acceptor.accept(client_stream).await?;
    
    // Connect to real server
    let server_stream = TcpStream::connect(format!("{}:443", host)).await?;
    
    // Create client config for server connection
    let mut root_store = rustls::RootCertStore::empty();
    root_store.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());
    
    let client_config = ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();
    
    let connector = TlsConnector::from(Arc::new(client_config));
    let server_name = ServerName::try_from(host.to_string())?;
    
    let mut server_tls = connector.connect(server_name, server_stream).await?;
    
    // Bidirectional proxy with inspection
    let mut client_buf = vec![0u8; 65536];
    let mut server_buf = vec![0u8; 65536];
    
    loop {
        tokio::select! {
            // Client -> Server (request)
            result = client_tls.read(&mut client_buf) => {
                let n = result?;
                if n == 0 { break; }
                
                let request_data = &client_buf[..n];
                
                // Analyze request with engines
                if let Ok(text) = std::str::from_utf8(request_data) {
                    let analysis = engines::analyze_content(text, &engine_config);
                    log_analysis(host, "REQUEST", &analysis);
                    
                    if analysis.should_block {
                        error!("BLOCKED request to {} - threat detected!", host);
                        // Send error response
                        let blocked_response = b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\n\r\nSENTINEL: Request blocked due to security policy";
                        client_tls.write_all(blocked_response).await?;
                        break;
                    }
                }
                
                // Forward to server
                server_tls.write_all(request_data).await?;
            }
            
            // Server -> Client (response)
            result = server_tls.read(&mut server_buf) => {
                let n = result?;
                if n == 0 { break; }
                
                let response_data = &server_buf[..n];
                
                // Analyze response
                if let Ok(text) = std::str::from_utf8(response_data) {
                    let analysis = engines::analyze_content(text, &engine_config);
                    log_analysis(host, "RESPONSE", &analysis);
                }
                
                // Forward to client
                client_tls.write_all(response_data).await?;
            }
        }
    }
    
    Ok(())
}

/// Log analysis results
fn log_analysis(host: &str, direction: &str, analysis: &AnalysisResult) {
    if analysis.threat_level != ThreatLevel::None {
        info!(
            "[{}] {} - Threat: {:?}, Keywords: {}, PII: {}",
            direction,
            host,
            analysis.threat_level,
            analysis.keywords_match.len(),
            analysis.pii_match.len()
        );
    }
}
