//! Transparent HTTPS Proxy Server
//!
//! Accepts raw TLS connections (no HTTP CONNECT) and performs MITM inspection.
//! Uses SNI extraction from TLS ClientHello for dynamic certificate generation.
//! Production-grade implementation for use with WinDivert packet redirection.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::net::SocketAddr;
use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio_rustls::{TlsConnector, LazyConfigAcceptor};
use rustls::{ClientConfig, ServerConfig};
use rustls::pki_types::ServerName;
use tracing::{info, error, warn};

use super::CertificateAuthority;
use crate::engines::{self, EngineConfig, AnalysisResult, ThreatLevel};

/// Transparent proxy running flag
static TRANSPARENT_PROXY_RUNNING: AtomicBool = AtomicBool::new(false);

/// Transparent HTTPS Proxy Server
pub struct TransparentProxyServer {
    ca: Arc<CertificateAuthority>,
    listen_addr: SocketAddr,
    engine_config: EngineConfig,
}

impl TransparentProxyServer {
    pub fn new(ca: Arc<CertificateAuthority>, listen_addr: SocketAddr) -> Self {
        Self {
            ca,
            listen_addr,
            engine_config: EngineConfig::default(),
        }
    }
    
    /// Start the transparent proxy server
    pub async fn run(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        if TRANSPARENT_PROXY_RUNNING.swap(true, Ordering::SeqCst) {
            info!("Transparent proxy already running");
            return Ok(());
        }
        
        let listener = TcpListener::bind(&self.listen_addr).await?;
        info!("🔒 SENTINEL Transparent Proxy listening on {}", self.listen_addr);
        
        loop {
            match listener.accept().await {
                Ok((stream, peer_addr)) => {
                    // Debug log to file
                    use std::fs::OpenOptions;
                    use std::io::Write;
                    if let Ok(mut f) = OpenOptions::new()
                        .create(true)
                        .append(true)
                        .open("C:\\temp\\sentinel_debug.log") 
                    {
                        let _ = writeln!(f, "PROXY ACCEPT: connection from {}", peer_addr);
                    }
                    
                    let ca = Arc::clone(&self.ca);
                    let engine_config = self.engine_config.clone();
                    
                    tokio::spawn(async move {
                        if let Err(e) = handle_transparent_connection(stream, peer_addr, ca, engine_config).await {
                            // Don't log common errors (connection reset, etc)
                            let err_str = e.to_string();
                            if !err_str.contains("reset") && !err_str.contains("aborted") && !err_str.contains("peer") {
                                error!("Transparent connection error from {}: {}", peer_addr, e);
                            }
                        }
                    });
                }
                Err(e) => {
                    error!("Accept error: {}", e);
                }
            }
        }
    }
}

/// Handle a transparent TCP connection using SNI extraction
async fn handle_transparent_connection(
    stream: TcpStream,
    peer_addr: SocketAddr,
    ca: Arc<CertificateAuthority>,
    engine_config: EngineConfig,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Use LazyConfigAcceptor to peek at ClientHello and extract SNI
    let acceptor = LazyConfigAcceptor::new(rustls::server::Acceptor::default(), stream);
    
    // Start handshake to receive ClientHello
    let start_handshake = acceptor.await?;
    
    // Extract SNI from ClientHello
    let client_hello = start_handshake.client_hello();
    let sni_host = client_hello.server_name()
        .map(|s| s.to_string())
        .unwrap_or_else(|| "unknown".to_string());
    
    if sni_host == "unknown" || sni_host.is_empty() {
        warn!("No SNI in ClientHello from {}", peer_addr);
        return Ok(());
    }
    
    info!("🔐 Transparent TLS intercept: {} -> {}", peer_addr, sni_host);
    
    // Check if AI endpoint
    let is_ai = crate::AI_ENDPOINTS.iter().any(|ep| sni_host.contains(ep));
    
    // Enhanced logging
    let (level, category) = if is_ai {
        (crate::logging::LogLevel::Warn, crate::logging::LogCategory::Security)
    } else {
        (crate::logging::LogLevel::Info, crate::logging::LogCategory::Network)
    };
    
    crate::logging::logger().log(
        crate::logging::EnhancedLogEntry::new(
            level, 
            category, 
            "TransparentProxy", 
            format!("TLS intercept {} {}", sni_host, if is_ai { "🤖 AI API" } else { "" })
        )
    );
    
    // Generate certificate for this host
    let (cert, key) = ca.generate_cert_for_host(&sni_host)?;
    
    // Create server config with dynamic certificate
    let server_config = ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert], key)?;
    
    // Complete TLS handshake with our certificate
    let mut client_tls = start_handshake.into_stream(Arc::new(server_config)).await?;
    
    // Get original destination from NAT table (using client's source port)
    let client_port = peer_addr.port();
    let (original_ip, original_port) = crate::nat_table::lookup_original_destination(client_port)
        .ok_or_else(|| format!("No NAT entry for client port {}", client_port))?;
    
    // Connect to real server using original destination from NAT
    let server_addr = format!("{}:{}", original_ip, original_port);
    info!("🎯 NAT lookup: client port {} -> original destination {}", client_port, server_addr);
    let server_stream = TcpStream::connect(&server_addr).await?;
    
    // Create client config for server connection
    let mut root_store = rustls::RootCertStore::empty();
    root_store.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());
    
    let client_config = ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();
    
    let connector = TlsConnector::from(Arc::new(client_config));
    let server_name = ServerName::try_from(sni_host.clone())?;
    
    let mut server_tls = connector.connect(server_name, server_stream).await?;
    
    info!("🔗 TLS tunnel established: client <-> SENTINEL <-> {}", sni_host);
    
    // Bidirectional proxy with inspection
    let mut client_buf = vec![0u8; 65536];
    let mut server_buf = vec![0u8; 65536];
    
    loop {
        tokio::select! {
            // Client -> Server (request)
            result = client_tls.read(&mut client_buf) => {
                match result {
                    Ok(0) => break,
                    Ok(n) => {
                        let request_data = &client_buf[..n];
                        
                        // Analyze request with engines
                        if let Ok(text) = std::str::from_utf8(request_data) {
                            let analysis = engines::analyze_content(text, &engine_config);
                            log_analysis(&sni_host, "REQUEST", &analysis);
                            
                            if analysis.should_block {
                                error!("🚫 BLOCKED request to {} - threat detected!", sni_host);
                                let blocked_response = b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\n\r\nSENTINEL: Request blocked due to security policy";
                                let _ = client_tls.write_all(blocked_response).await;
                                break;
                            }
                        }
                        
                        // Forward to server
                        if server_tls.write_all(request_data).await.is_err() {
                            break;
                        }
                    }
                    Err(_) => break,
                }
            }
            
            // Server -> Client (response)
            result = server_tls.read(&mut server_buf) => {
                match result {
                    Ok(0) => break,
                    Ok(n) => {
                        let response_data = &server_buf[..n];
                        
                        // Analyze response
                        if let Ok(text) = std::str::from_utf8(response_data) {
                            let analysis = engines::analyze_content(text, &engine_config);
                            log_analysis(&sni_host, "RESPONSE", &analysis);
                        }
                        
                        // Forward to client
                        if client_tls.write_all(response_data).await.is_err() {
                            break;
                        }
                    }
                    Err(_) => break,
                }
            }
        }
    }
    
    Ok(())
}

/// Log analysis results
fn log_analysis(host: &str, direction: &str, analysis: &AnalysisResult) {
    if analysis.threat_level != ThreatLevel::None {
        info!(
            "🔍 [{}] {} - Threat: {:?}, Keywords: {}, PII: {}",
            direction,
            host,
            analysis.threat_level,
            analysis.keywords_match.len(),
            analysis.pii_match.len()
        );
    }
}

/// Check if transparent proxy is running
pub fn is_transparent_proxy_running() -> bool {
    TRANSPARENT_PROXY_RUNNING.load(Ordering::SeqCst)
}
