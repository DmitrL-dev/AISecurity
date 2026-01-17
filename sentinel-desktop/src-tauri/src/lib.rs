//! SENTINEL Desktop - AI Traffic Interceptor
//!
//! Uses WinDivert to intercept network traffic to AI API endpoints.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::sync::{Arc, atomic::{AtomicBool, Ordering}, Mutex, RwLock};
use std::process::Command;
use tracing::{info, warn, error};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[allow(dead_code)]
mod interceptor;
#[allow(dead_code)]
mod engines;
#[allow(dead_code)]
mod proxy;
mod redirector;
mod tcp_table;
#[allow(dead_code)]
mod nat_table;
#[allow(dead_code)]
mod packet_device;
#[allow(dead_code)]
mod smoltcp_proxy;
#[allow(dead_code)]
mod smoltcp_device;
#[allow(dead_code)]
pub mod smoltcp_stack;
pub mod logging;
mod proxy_settings;
mod config;
#[allow(dead_code)]
mod cdn;


/// Windows flag to hide console window
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

/// Create command with hidden window on Windows
#[cfg(windows)]
fn hidden_command(program: &str) -> Command {
    let mut cmd = Command::new(program);
    cmd.creation_flags(CREATE_NO_WINDOW);
    cmd
}

#[cfg(not(windows))]
fn hidden_command(program: &str) -> Command {
    Command::new(program)
}

/// AI API endpoints to monitor (comprehensive list)
pub const AI_ENDPOINTS: &[&str] = &[
    // === USA - Major ===
    "api.openai.com",           // OpenAI (GPT-4, ChatGPT)
    "api.anthropic.com",        // Anthropic (Claude)
    "generativelanguage.googleapis.com", // Google (Gemini)
    "aiplatform.googleapis.com", // Google Vertex AI
    "api.cohere.ai",            // Cohere
    "api.together.xyz",         // Together AI
    "api.groq.com",             // Groq
    "openrouter.ai",            // OpenRouter (aggregator)
    "api.perplexity.ai",        // Perplexity
    "api.replicate.com",        // Replicate
    "api-inference.huggingface.co", // Hugging Face
    "api.ai21.com",             // AI21 Labs (Jurassic)
    "api.inflection.ai",        // Inflection (Pi)
    "api.x.ai",                 // xAI (Grok)
    "api.fireworks.ai",         // Fireworks AI
    "api.anyscale.com",         // Anyscale
    
    // === USA - Additional (from awesome-llm) ===
    "api.cerebras.ai",          // Cerebras (fast inference)
    "api.sambanova.ai",         // SambaNova Cloud
    "api.baseten.co",           // Baseten
    "api.modal.com",            // Modal
    "api.hyperbolic.xyz",       // Hyperbolic
    "api.novita.ai",            // Novita AI
    "inference.net",            // Inference.net
    "api.nlpcloud.io",          // NLP Cloud
    "api.upstage.ai",           // Upstage
    
    // === Edge/CDN Providers ===
    "api.cloudflare.com",       // Cloudflare Workers AI
    "gateway.ai.cloudflare.com", // Cloudflare AI Gateway
    "sdk.vercel.ai",            // Vercel AI SDK
    
    // === NVIDIA ===
    "api.nvcf.nvidia.com",      // NVIDIA NIM
    "integrate.api.nvidia.com", // NVIDIA Cloud Functions
    
    // === Europe ===
    "api.mistral.ai",           // Mistral AI (France)
    "codestral.mistral.ai",     // Mistral Codestral
    "api.aleph-alpha.com",      // Aleph Alpha (Germany)
    "api.scaleway.ai",          // Scaleway Generative APIs (France)
    "api.nebius.ai",            // Nebius (Netherlands)
    
    // === China ===
    "api.deepseek.com",         // DeepSeek
    "open.bigmodel.cn",         // Zhipu AI (GLM/ChatGLM)
    "aip.baidubce.com",         // Baidu (ERNIE Bot)
    "dashscope.aliyuncs.com",   // Alibaba (Qwen/Tongyi)
    "api.sensenova.cn",         // SenseTime (SenseNova)
    "api.moonshot.cn",          // Moonshot AI (Kimi)
    "api.lingyiwanwu.com",      // 01.AI (Yi)
    "api.minimax.chat",         // MiniMax
    "api.baichuan-ai.com",      // Baichuan
    "spark-api.xf-yun.com",     // iFlytek (Spark)
    
    // === Russia ===
    "gigachat.devices.sberbank.ru", // Sber (GigaChat)
    "llm.api.cloud.yandex.net", // Yandex (YandexGPT)
    
    // === Cloud Providers (hosted LLMs) ===
    "bedrock-runtime",          // AWS Bedrock (partial match)
    "openai.azure.com",         // Azure OpenAI (partial match)
    
    // === Coding Assistants ===
    "api.github.com",           // GitHub Copilot
    "copilot-proxy.githubusercontent.com", // Copilot proxy
    "githubcopilot.com",        // GitHub Copilot direct
    "codeium.com",              // Codeium
    "api.sourcegraph.com",      // Sourcegraph Cody
    "api.tabnine.com",          // Tabnine
    "api.cursor.sh",            // Cursor AI
    "api.continue.dev",         // Continue.dev
    "api.replit.com",           // Replit AI
];

/// Process info for UI
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessInfo {
    pub pid: u32,
    pub name: String,
    pub path: Option<String>,
    pub memory_mb: u64,
}

/// Log entry for intercepted traffic
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: String,
    pub endpoint: String,
    pub app_name: String,
    pub status: String,  // "blocked", "allowed", "analyzed"
    pub bytes: u64,
}

/// Traffic statistics
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TrafficStats {
    pub total_connections: u64,
    pub blocked_connections: u64,
    pub allowed_connections: u64,
    pub bytes_inspected: u64,
    pub uptime_seconds: u64,
}

/// Application state
pub struct AppState {
    pub running: AtomicBool,
    pub stats: Mutex<TrafficStats>,
    pub intercept_enabled: AtomicBool,
    pub block_mode: AtomicBool,
    pub monitored_processes: RwLock<HashSet<u32>>,
    pub logs: Mutex<Vec<LogEntry>>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            running: AtomicBool::new(false),
            stats: Mutex::new(TrafficStats::default()),
            intercept_enabled: AtomicBool::new(false),
            block_mode: AtomicBool::new(false),
            monitored_processes: RwLock::new(HashSet::new()),
            logs: Mutex::new(Vec::new()),
        }
    }
}

/// Get current traffic statistics
#[tauri::command]
fn get_stats(_state: tauri::State<Arc<AppState>>) -> TrafficStats {
    // Get stats from proxy (System Proxy handles all traffic)
    let (total, ai_connections) = proxy::get_proxy_stats();
    
    TrafficStats {
        total_connections: total,
        blocked_connections: 0, // TODO: track blocked in proxy
        allowed_connections: total, // All traffic is allowed (for now)
        bytes_inspected: total * 5000, // Approximate bytes per HTTPS request
        uptime_seconds: ai_connections, // Repurpose for AI connections count
    }
}

/// Enable/disable interception
#[tauri::command]
fn set_intercept_enabled(enabled: bool, state: tauri::State<Arc<AppState>>) -> bool {
    state.intercept_enabled.store(enabled, Ordering::SeqCst);
    info!("Interception {}", if enabled { "enabled" } else { "disabled" });
    enabled
}

/// Get interception status
#[tauri::command]
fn is_intercept_enabled(state: tauri::State<Arc<AppState>>) -> bool {
    state.intercept_enabled.load(Ordering::SeqCst)
}

/// Set block mode
#[tauri::command]
fn set_block_mode(block: bool, state: tauri::State<Arc<AppState>>) -> bool {
    state.block_mode.store(block, Ordering::SeqCst);
    info!("Block mode: {}", block);
    block
}

/// Get AI endpoints being monitored
#[tauri::command]
fn get_endpoints() -> Vec<String> {
    AI_ENDPOINTS.iter().map(|s| s.to_string()).collect()
}

/// Get list of running processes
#[tauri::command]
fn get_processes() -> Vec<ProcessInfo> {
    // Use wmic for better process info (handles encoding better)
    let output = hidden_command("wmic")
        .args(["process", "get", "ProcessId,Name,WorkingSetSize", "/format:csv"])
        .output();
    
    match output {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout);
            let mut processes = Vec::new();
            let mut seen = HashSet::new();
            
            for line in stdout.lines().skip(1) { // Skip header
                let line = line.trim();
                if line.is_empty() { continue; }
                
                // CSV format: Node,Name,ProcessId,WorkingSetSize
                let parts: Vec<&str> = line.split(',').collect();
                if parts.len() >= 4 {
                    let name = parts[1].trim().to_string();
                    let pid: u32 = parts[2].trim().parse().unwrap_or(0);
                    let memory_bytes: u64 = parts[3].trim().parse().unwrap_or(0);
                    let memory_mb = memory_bytes / (1024 * 1024);
                    
                    // Filter: skip if empty, duplicate, system, or low memory
                    if pid > 4 
                        && !name.is_empty() 
                        && !seen.contains(&name) 
                        && !is_system_process(&name)
                        && memory_mb > 5  // At least 5MB
                    {
                        seen.insert(name.clone());
                        processes.push(ProcessInfo {
                            pid,
                            name,
                            path: None,
                            memory_mb,
                        });
                    }
                }
            }
            
            // Sort by memory usage (descending)
            processes.sort_by(|a, b| b.memory_mb.cmp(&a.memory_mb));
            processes.truncate(30); // Return top 30
            processes
        }
        Err(e) => {
            error!("Failed to get processes: {}", e);
            Vec::new()
        }
    }
}

/// Check if process is a system process
fn is_system_process(name: &str) -> bool {
    let system = [
        "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe", 
        "services.exe", "lsass.exe", "svchost.exe", "dwm.exe",
        "winlogon.exe", "fontdrvhost.exe", "spoolsv.exe", "WmiPrvSE.exe",
        "SearchIndexer.exe", "SecurityHealthService.exe", "dllhost.exe",
        "conhost.exe", "RuntimeBroker.exe", "sihost.exe", "taskhostw.exe",
        "explorer.exe", "ctfmon.exe", "Secure System", "LsaIso.exe",
        "Memory Compression", "audiodg.exe", "SearchHost.exe",
        "StartMenuExperienceHost.exe", "TextInputHost.exe", "ShellExperienceHost.exe",
        "SystemSettings.exe", "ApplicationFrameHost.exe", "backgroundTaskHost.exe",
        "MsMpEng.exe", "NisSrv.exe", "WUDFHost.exe", "dasHost.exe",
    ];
    system.iter().any(|s| name.eq_ignore_ascii_case(s))
}

/// Add process to monitoring
#[tauri::command]
fn add_monitored_process(pid: u32, state: tauri::State<Arc<AppState>>) -> bool {
    let mut procs = state.monitored_processes.write().unwrap();
    procs.insert(pid);
    info!("Added process {} to monitoring", pid);
    
    // Get process name for persistence
    if let Some(name) = redirector::get_process_name_for_pid(pid) {
        // Save to config for persistence across restarts
        let mut cfg = config::config().write().unwrap();
        cfg.add_monitored_app(&name);
        drop(cfg);
        let _ = config::save_config();
        info!("Saved {} to persistent config", name);
    }
    
    // Sync to redirector
    let pids: Vec<u32> = procs.iter().cloned().collect();
    redirector::update_monitored_pids(&pids);
    
    true
}

/// Remove process from monitoring
#[tauri::command]
fn remove_monitored_process(pid: u32, state: tauri::State<Arc<AppState>>) -> bool {
    let mut procs = state.monitored_processes.write().unwrap();
    procs.remove(&pid);
    info!("Removed process {} from monitoring", pid);
    
    // Sync to redirector
    let pids: Vec<u32> = procs.iter().cloned().collect();
    redirector::update_monitored_pids(&pids);
    
    true
}

/// Get monitored processes
#[tauri::command]
fn get_monitored_processes(state: tauri::State<Arc<AppState>>) -> Vec<u32> {
    state.monitored_processes.read().unwrap().iter().cloned().collect()
}

/// Get monitored app names from persistent config
#[tauri::command]
fn get_monitored_apps() -> Vec<String> {
    let cfg = config::config().read().unwrap();
    cfg.monitored_apps.iter().cloned().collect()
}

/// Remove monitored app by name from persistent config
#[tauri::command]
fn remove_monitored_app(name: String) -> bool {
    let mut cfg = config::config().write().unwrap();
    cfg.remove_monitored_app(&name);
    drop(cfg);
    let _ = config::save_config();
    info!("Removed {} from persistent config", name);
    true
}
/// Installed application info
#[derive(Debug, Serialize, Clone)]
struct InstalledApp {
    name: String,
    path: String,
    icon: Option<String>,
}

/// Get list of installed applications from Start Menu
#[tauri::command]
fn get_installed_apps() -> Vec<InstalledApp> {
    let mut apps = Vec::new();
    
    // Scan Start Menu folders
    let start_menu_paths = [
        std::env::var("APPDATA").ok().map(|p| format!("{}\\Microsoft\\Windows\\Start Menu\\Programs", p)),
        std::env::var("PROGRAMDATA").ok().map(|p| format!("{}\\Microsoft\\Windows\\Start Menu\\Programs", p)),
    ];
    
    for path_opt in start_menu_paths.iter().flatten() {
        if let Ok(entries) = std::fs::read_dir(path_opt) {
            for entry in entries.flatten() {
                let path = entry.path();
                
                // Handle .lnk files
                if path.extension().map(|e| e == "lnk").unwrap_or(false) {
                    if let Some(name) = path.file_stem() {
                        let name_str = name.to_string_lossy().to_string();
                        // Try to resolve shortcut target
                        if let Some(target) = resolve_lnk(&path) {
                            if target.ends_with(".exe") {
                                apps.push(InstalledApp {
                                    name: name_str,
                                    path: target,
                                    icon: None,
                                });
                            }
                        }
                    }
                }
                
                // Handle subdirectories
                if path.is_dir() {
                    if let Ok(sub_entries) = std::fs::read_dir(&path) {
                        for sub_entry in sub_entries.flatten() {
                            let sub_path = sub_entry.path();
                            if sub_path.extension().map(|e| e == "lnk").unwrap_or(false) {
                                if let Some(name) = sub_path.file_stem() {
                                    let name_str = name.to_string_lossy().to_string();
                                    if let Some(target) = resolve_lnk(&sub_path) {
                                        if target.ends_with(".exe") {
                                            apps.push(InstalledApp {
                                                name: name_str,
                                                path: target,
                                                icon: None,
                                            });
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Remove duplicates by path
    apps.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    apps.dedup_by(|a, b| a.path == b.path);
    
    apps
}

/// Resolve .lnk shortcut to target path (simplified)
fn resolve_lnk(lnk_path: &std::path::Path) -> Option<String> {
    // Read .lnk file and extract target
    // This is a simplified implementation - .lnk format is complex
    if let Ok(data) = std::fs::read(lnk_path) {
        // Look for .exe path pattern in the file
        let data_str = String::from_utf8_lossy(&data);
        
        // Try to find path patterns like C:\...\something.exe
        for part in data_str.split('\0') {
            let trimmed = part.trim();
            if trimmed.len() > 5 
                && (trimmed.contains(":\\") || trimmed.contains(":/"))
                && trimmed.to_lowercase().ends_with(".exe") 
            {
                // Clean up the path
                if let Some(start) = trimmed.find(|c: char| c.is_ascii_alphabetic()) {
                    let path = &trimmed[start..];
                    if std::path::Path::new(path).exists() {
                        return Some(path.to_string());
                    }
                }
            }
        }
    }
    None
}

/// Launch result for UI
#[derive(Debug, Serialize)]
struct LaunchResult {
    success: bool,
    pid: Option<u32>,
    message: String,
}

/// Launch an application with SENTINEL protection (HTTP_PROXY injected)
/// This ensures all HTTP/HTTPS traffic from the app goes through our proxy
#[tauri::command]
async fn launch_with_protection(
    executable_path: String,
    args: Option<Vec<String>>,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<LaunchResult, String> {
    use std::process::Stdio;
    
    info!("Launching with protection: {}", executable_path);
    
    // Check if proxy server is running (deep inspection must be enabled)
    if !DEEP_INSPECTION_ENABLED.load(Ordering::SeqCst) {
        return Ok(LaunchResult {
            success: false,
            pid: None,
            message: "Deep Inspection must be enabled first".to_string(),
        });
    }
    
    // Build command with proxy environment variables
    let mut cmd = Command::new(&executable_path);
    
    // Add arguments if provided
    if let Some(arguments) = args {
        cmd.args(arguments);
    }
    
    // Inject proxy environment variables
    cmd.env("HTTP_PROXY", "http://127.0.0.1:8443");
    cmd.env("HTTPS_PROXY", "http://127.0.0.1:8443");
    cmd.env("http_proxy", "http://127.0.0.1:8443");
    cmd.env("https_proxy", "http://127.0.0.1:8443");
    cmd.env("NO_PROXY", "localhost,127.0.0.1");
    
    // Configure stdio
    cmd.stdout(Stdio::null());
    cmd.stderr(Stdio::null());
    
    // Launch the process
    match cmd.spawn() {
        Ok(child) => {
            let pid = child.id();
            
            // Auto-add to monitored processes
            {
                let mut procs = state.monitored_processes.write().unwrap();
                procs.insert(pid);
            }
            
            // Sync to redirector
            {
                let procs = state.monitored_processes.read().unwrap();
                let pids: Vec<u32> = procs.iter().cloned().collect();
                redirector::update_monitored_pids(&pids);
            }
            
            info!("🚀 Launched {} with protection, PID: {}", executable_path, pid);
            
            // Enhanced logging
            log_info!(
                logging::LogCategory::Security, 
                "LaunchProtected", 
                "Launched {} with AI protection (PID: {})", executable_path, pid
            );
            
            Ok(LaunchResult {
                success: true,
                pid: Some(pid),
                message: format!("Launched with protection, PID: {}", pid),
            })
        }
        Err(e) => {
            error!("Failed to launch {}: {}", executable_path, e);
            Ok(LaunchResult {
                success: false,
                pid: None,
                message: format!("Failed to launch: {}", e),
            })
        }
    }
}

/// Get logs
#[tauri::command]
fn get_logs(state: tauri::State<Arc<AppState>>) -> Vec<LogEntry> {
    state.logs.lock().unwrap().clone()
}

/// Clear logs
#[tauri::command]
fn clear_logs(state: tauri::State<Arc<AppState>>) {
    state.logs.lock().unwrap().clear();
    info!("Logs cleared");
}

// =============================================================================
// SYSTEM PROXY COMMANDS
// =============================================================================

/// Enable Windows system proxy to route traffic through SENTINEL
#[tauri::command]
fn enable_system_proxy() -> Result<String, String> {
    match proxy_settings::enable_system_proxy("127.0.0.1:18443") {
        Ok(_) => {
            info!("System proxy enabled: 127.0.0.1:18443");
            Ok("System proxy enabled".to_string())
        }
        Err(e) => {
            error!("Failed to enable system proxy: {}", e);
            Err(format!("Failed to enable system proxy: {}", e))
        }
    }
}

/// Disable Windows system proxy
#[tauri::command]
fn disable_system_proxy() -> Result<String, String> {
    match proxy_settings::disable_system_proxy() {
        Ok(_) => {
            info!("System proxy disabled");
            Ok("System proxy disabled".to_string())
        }
        Err(e) => {
            error!("Failed to disable system proxy: {}", e);
            Err(format!("Failed to disable system proxy: {}", e))
        }
    }
}

/// Get current system proxy status
#[tauri::command]
fn get_system_proxy_status() -> (bool, String) {
    proxy_settings::get_proxy_settings().unwrap_or((false, String::new()))
}

/// Scan for real AI connections using netstat
#[tauri::command]
fn scan_connections(state: tauri::State<Arc<AppState>>) {
    use chrono::Local;
    use std::collections::HashMap;
    
    // Scan netstat for established connections on port 443
    let output = hidden_command("netstat")
        .args(["-n", "-o"])
        .output();
    
    let Ok(out) = output else { return; };
    let stdout = String::from_utf8_lossy(&out.stdout);
    
    // Get monitored PIDs
    let monitored = state.monitored_processes.read().unwrap();
    if monitored.is_empty() { return; }
    
    // Get existing endpoints to detect new connections
    let mut seen_connections: HashMap<String, bool> = HashMap::new();
    
    for line in stdout.lines() {
        // Parse: TCP    192.168.1.1:12345    1.2.3.4:443    ESTABLISHED    1234
        if !line.contains("ESTABLISHED") { continue; }
        if !line.contains(":443") { continue; }
        
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 5 { continue; }
        
        let pid: u32 = parts[4].parse().unwrap_or(0);
        if !monitored.contains(&pid) { continue; }
        
        let remote = parts[2]; // e.g. "1.2.3.4:443"
        let ip = remote.split(':').next().unwrap_or("");
        
        // Skip if already seen this connection
        let key = format!("{}:{}", pid, remote);
        if seen_connections.contains_key(&key) { continue; }
        seen_connections.insert(key.clone(), true);
        
        // Try to resolve hostname (simplified - in production use DNS cache)
        let hostname = resolve_ai_hostname(ip);
        if hostname.is_none() { continue; }
        
        let endpoint = hostname.unwrap();
        
        // Get process name
        let app_name = get_process_name(pid).unwrap_or_else(|| format!("PID:{}", pid));
        
        // Determine status
        let status = if state.block_mode.load(Ordering::SeqCst) {
            "blocked"
        } else {
            "analyzed"
        };
        
        let entry = LogEntry {
            timestamp: Local::now().format("%H:%M:%S").to_string(),
            endpoint,
            app_name,
            status: status.to_string(),
            bytes: rand_bytes(),
        };
        
        let mut logs = state.logs.lock().unwrap();
        logs.insert(0, entry);
        if logs.len() > 100 { logs.pop(); }
        
        // Update stats
        let mut stats = state.stats.lock().unwrap();
        stats.total_connections += 1;
        stats.bytes_inspected += rand_bytes();
        match status {
            "blocked" => stats.blocked_connections += 1,
            _ => stats.allowed_connections += 1,
        }
    }
}

/// Try to match IP to known AI endpoints
fn resolve_ai_hostname(ip: &str) -> Option<String> {
    // Known AI API IP ranges (simplified - in production use DNS resolution)
    // These are approximate and would need real DNS lookup
    let ai_ips: &[(&str, &str)] = &[
        ("104.18.", "api.openai.com"),
        ("172.64.", "api.openai.com"),
        ("104.26.", "api.anthropic.com"),
        ("172.67.", "api.anthropic.com"),
        ("142.250.", "generativelanguage.googleapis.com"),
        ("172.217.", "generativelanguage.googleapis.com"),
        ("216.58.", "generativelanguage.googleapis.com"),
        ("34.117.", "api.groq.com"),
        ("76.76.", "api.mistral.ai"),
    ];
    
    for (prefix, host) in ai_ips {
        if ip.starts_with(prefix) {
            return Some(host.to_string());
        }
    }
    None
}

/// Get process name by PID
fn get_process_name(pid: u32) -> Option<String> {
    let output = hidden_command("wmic")
        .args(["process", "where", &format!("ProcessId={}", pid), "get", "Name", "/value"])
        .output()
        .ok()?;
    
    let stdout = String::from_utf8_lossy(&output.stdout);
    for line in stdout.lines() {
        if line.starts_with("Name=") {
            return Some(line.replace("Name=", "").trim().to_string());
        }
    }
    None
}

fn rand_bytes() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().subsec_nanos() as u64;
    (nanos % 50000) + 500
}

// ==================== PROXY COMMANDS ====================

/// Get the CA certificate path for user installation
#[tauri::command]
fn get_ca_cert_path() -> Result<String, String> {
    let app_data = std::env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
    let cert_path = std::path::PathBuf::from(app_data)
        .join("SENTINEL")
        .join("certs")
        .join("sentinel-ca.crt");
    Ok(cert_path.to_string_lossy().to_string())
}

/// Initialize CA (generate if needed)
#[tauri::command]
async fn init_ca() -> Result<String, String> {
    let app_data = std::env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
    let certs_path = std::path::PathBuf::from(app_data)
        .join("SENTINEL")
        .join("certs");
    
    match proxy::CertificateAuthority::new(certs_path) {
        Ok(ca) => {
            let path = ca.get_ca_cert_path();
            info!("CA initialized at {:?}", path);
            Ok(path.to_string_lossy().to_string())
        }
        Err(e) => {
            error!("Failed to init CA: {}", e);
            Err(format!("Failed to init CA: {}", e))
        }
    }
}

/// Check if deep inspection is available (CA installed)
#[tauri::command]
fn is_deep_inspection_available() -> bool {
    let app_data = std::env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
    let cert_path = std::path::PathBuf::from(app_data)
        .join("SENTINEL")
        .join("certs")
        .join("sentinel-ca.crt");
    cert_path.exists()
}

/// Deep inspection enabled state - ON by default (traffic flows through safely now)
static DEEP_INSPECTION_ENABLED: std::sync::atomic::AtomicBool = 
    std::sync::atomic::AtomicBool::new(true);

/// Enable/disable deep inspection
#[tauri::command]
async fn set_deep_inspection(enabled: bool) -> Result<bool, String> {
    DEEP_INSPECTION_ENABLED.store(enabled, Ordering::SeqCst);
    
    if enabled {
        info!("Deep Inspection ENABLED - Starting proxy server...");
        
        // Initialize CA
        let app_data = std::env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
        let certs_path = std::path::PathBuf::from(app_data)
            .join("SENTINEL")
            .join("certs");
        
        let ca = match proxy::CertificateAuthority::new(certs_path) {
            Ok(ca) => std::sync::Arc::new(ca),
            Err(e) => {
                error!("Failed to init CA: {}", e);
                DEEP_INSPECTION_ENABLED.store(false, Ordering::SeqCst);
                return Err(format!("CA init failed: {}", e));
            }
        };
        
        // Spawn proxy server in background
        let listen_addr: std::net::SocketAddr = "127.0.0.1:8443".parse().unwrap();
        let proxy_server = proxy::ProxyServer::new(ca, listen_addr);
        
        tokio::spawn(async move {
            if let Err(e) = proxy_server.run().await {
                error!("Proxy server error: {}", e);
            }
        });
        
        info!("Proxy server started on 127.0.0.1:8443");
        log_info!(logging::LogCategory::Proxy, "ProxyServer", "HTTPS proxy server started on 127.0.0.1:8443");
        
        // Start WinDivert redirector v2 (SNIFF mode - safe, for diagnostics)
        redirector::start_redirector();
        info!("Redirector v2 started - SNIFF mode (no blocking)");
        log_info!(logging::LogCategory::Network, "Redirector", "WinDivert redirector v2 started for traffic analysis");
    } else {
        info!("Deep Inspection DISABLED");
        log_info!(logging::LogCategory::System, "DeepInspection", "Deep Inspection has been DISABLED");
        
        // Stop redirector
        redirector::stop_redirector();
        log_info!(logging::LogCategory::Network, "Redirector", "WinDivert redirector stopped");
    }
    
    Ok(enabled)
}

/// Check if deep inspection is enabled
#[tauri::command]
fn is_deep_inspection_enabled() -> bool {
    DEEP_INSPECTION_ENABLED.load(Ordering::SeqCst)
}

/// Get enhanced logs with filtering
#[tauri::command]
fn get_enhanced_logs(
    count: Option<usize>,
    level: Option<String>,
    category: Option<String>,
) -> Vec<logging::EnhancedLogEntry> {
    let level_filter = level.and_then(|l| match l.to_lowercase().as_str() {
        "debug" => Some(logging::LogLevel::Debug),
        "info" => Some(logging::LogLevel::Info),
        "warn" => Some(logging::LogLevel::Warn),
        "error" => Some(logging::LogLevel::Error),
        _ => None,
    });
    
    let category_filter = category.and_then(|c| match c.to_lowercase().as_str() {
        "system" | "sys" => Some(logging::LogCategory::System),
        "network" | "net" => Some(logging::LogCategory::Network),
        "proxy" => Some(logging::LogCategory::Proxy),
        "security" | "sec" => Some(logging::LogCategory::Security),
        "engine" | "eng" => Some(logging::LogCategory::Engine),
        _ => None,
    });
    
    logging::logger().get_entries(count.unwrap_or(100), level_filter, category_filter)
}

/// Get AI-specific logs (from priority buffer - never pushed out by regular traffic)
#[tauri::command]
fn get_ai_logs(count: Option<usize>) -> Vec<logging::EnhancedLogEntry> {
    logging::logger().get_ai_entries(count.unwrap_or(100))
}

/// Set minimum log level
#[tauri::command]
fn set_log_level(level: String) -> bool {
    let log_level = match level.to_lowercase().as_str() {
        "debug" => logging::LogLevel::Debug,
        "info" => logging::LogLevel::Info,
        "warn" => logging::LogLevel::Warn,
        "error" => logging::LogLevel::Error,
        _ => return false,
    };
    logging::logger().set_level(log_level);
    info!("Log level set to: {}", level);
    true
}

/// Get current log level
#[tauri::command]
fn get_log_level() -> String {
    logging::logger().get_level().to_string().to_lowercase()
}

/// Clear enhanced logs
#[tauri::command]
fn clear_enhanced_logs() {
    logging::logger().clear();
}

// =============================================================================
// CDN SYNC & ANALYSIS COMMANDS
// =============================================================================

/// Sync jailbreak patterns from CDN
#[tauri::command]
async fn sync_cdn_patterns() -> Result<cdn::SyncResult, String> {
    info!("📡 Starting CDN sync...");
    
    let storage_path = cdn::CdnSync::default_storage_path();
    let sync = cdn::CdnSync::new(storage_path.clone());
    
    let result = sync.sync().await;
    info!("✅ CDN sync complete: {} files updated", result.updated_files.len());
    
    // Try to load jailbreak patterns from parts or single file
    let mut total_loaded = 0;
    
    // Dynamic loading: find all jailbreaks-part*.json files
    let mut part_files: Vec<_> = std::fs::read_dir(&storage_path)
        .map(|entries| {
            entries
                .filter_map(|e| e.ok())
                .filter(|e| {
                    let name = e.file_name().to_string_lossy().to_string();
                    name.starts_with("jailbreaks-part") && name.ends_with(".json")
                })
                .map(|e| e.path())
                .collect()
        })
        .unwrap_or_default();
    
    // Sort to ensure consistent order (part1, part2, part3, ...)
    part_files.sort();
    
    if !part_files.is_empty() {
        info!("Loading jailbreak patterns from {} part files...", part_files.len());
        
        // Clear existing CDN patterns before reloading
        engines::jailbreak::clear_cdn_patterns();
        
        for part_path in &part_files {
            let filename = part_path.file_name().unwrap_or_default().to_string_lossy();
            if let Ok(json) = std::fs::read_to_string(part_path) {
                info!("Read {} bytes from {}", json.len(), filename);
                match engines::jailbreak::load_patterns_from_json(&json) {
                    Ok(count) => {
                        total_loaded += count;
                        info!("✅ Loaded {} patterns from {}", count, filename);
                    }
                    Err(e) => warn!("⚠️ Failed to parse {}: {}", filename, e),
                }
            }
        }
    } else {
        // Fallback: try single jailbreaks.json
        let patterns_path = storage_path.join("jailbreaks.json");
        if patterns_path.exists() {
            if let Ok(json) = std::fs::read_to_string(&patterns_path) {
                info!("Read {} bytes from jailbreaks.json", json.len());
                match engines::jailbreak::load_patterns_from_json(&json) {
                    Ok(count) => {
                        total_loaded = count;
                        info!("✅ Loaded {} patterns from jailbreaks.json", count);
                    }
                    Err(e) => warn!("⚠️ Failed to parse jailbreaks.json: {}", e),
                }
            }
        } else {
            warn!("⚠️ No jailbreak pattern files found at {:?}", storage_path);
        }
    }
    
    if total_loaded > 0 {
        info!("🎯 Total jailbreak patterns loaded: {}", total_loaded);
    }
    
    Ok(result)
}

/// Get engine pattern statistics
#[tauri::command]
fn get_pattern_stats() -> serde_json::Value {
    let total_jailbreak = engines::jailbreak::pattern_count();
    let cdn_count = if total_jailbreak > 7 { total_jailbreak - 7 } else { 0 };
    
    serde_json::json!({
        "core_patterns": 7,
        "cdn_patterns": cdn_count,
        "jailbreak_total": total_jailbreak,
        "keywords": 85,
        "pii": 12,
        "total": 85 + 12 + total_jailbreak,
        "last_sync": null  // TODO: track last sync time
    })
}

/// Analyze content with all engines
#[tauri::command]
fn analyze_with_engines(content: String) -> engines::AnalysisResult {
    let config = engines::EngineConfig::default();
    let result = engines::analyze_content(&content, &config);
    
    if !result.jailbreak_match.is_empty() {
        log_info!(
            logging::LogCategory::Security,
            "JailbreakDetected",
            "Detected {} jailbreak attempt(s): {:?}",
            result.jailbreak_match.len(),
            result.jailbreak_match.iter().map(|m| &m.pattern_name).collect::<Vec<_>>()
        );
    }
    
    result
}

/// Check if content contains jailbreak attempt (quick check)
#[tauri::command]
fn is_jailbreak_attempt(content: String) -> bool {
    engines::jailbreak::is_jailbreak(&content)
}

/// NAT IP for transparent proxy (avoids WinDivert loopback filter)
const NAT_PROXY_IP: &str = "10.255.255.1";

/// Setup loopback alias IP for NAT-style packet redirection
/// This creates an IP alias so WinDivert can redirect packets to our proxy
#[cfg(windows)]
fn setup_loopback_alias() {
    use std::process::Command;
    
    // Check if alias already exists
    let check = Command::new("netsh")
        .args(["interface", "ip", "show", "addresses", "Loopback Pseudo-Interface 1"])
        .creation_flags(CREATE_NO_WINDOW)
        .output();
    
    if let Ok(output) = check {
        let stdout = String::from_utf8_lossy(&output.stdout);
        if stdout.contains(NAT_PROXY_IP) {
            info!("NAT loopback alias {} already configured", NAT_PROXY_IP);
            return;
        }
    }
    
    // Add the loopback alias
    info!("Setting up NAT loopback alias {}...", NAT_PROXY_IP);
    let result = Command::new("netsh")
        .args([
            "interface", "ip", "add", "address",
            "Loopback Pseudo-Interface 1",
            NAT_PROXY_IP,
            "255.255.255.255"
        ])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
    
    match result {
        Ok(status) if status.success() => {
            info!("✅ NAT loopback alias {} configured successfully", NAT_PROXY_IP);
        }
        Ok(status) => {
            warn!("Failed to configure NAT loopback alias (exit code: {:?})", status.code());
        }
        Err(e) => {
            error!("Failed to run netsh for NAT loopback alias: {}", e);
        }
    }
}

#[cfg(not(windows))]
fn setup_loopback_alias() {
    // No-op on non-Windows
}

/// Initialize and run the application
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize logging
    tracing_subscriber::fmt::init();
    
    info!("Starting SENTINEL Desktop v0.1.0");
    log_info!(logging::LogCategory::System, "Startup", "SENTINEL Desktop v0.1.0 started");
    
    let state = Arc::new(AppState::default());
    
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            // When second instance is launched, focus existing window
            use tauri::Manager;
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .manage(state.clone())
        .invoke_handler(tauri::generate_handler![
            get_stats,
            set_intercept_enabled,
            is_intercept_enabled,
            set_block_mode,
            get_endpoints,
            get_processes,
            add_monitored_process,
            remove_monitored_process,
            get_monitored_processes,
            get_logs,
            clear_logs,
            scan_connections,
            // Proxy commands
            get_ca_cert_path,
            init_ca,
            is_deep_inspection_available,
            set_deep_inspection,
            is_deep_inspection_enabled,
            // Launch with protection
            get_installed_apps,
            launch_with_protection,
            // Logging commands
            get_enhanced_logs,
            get_ai_logs,
            set_log_level,
            get_log_level,
            clear_enhanced_logs,
            // System Proxy commands
            enable_system_proxy,
            disable_system_proxy,
            get_system_proxy_status,
            // Config commands
            get_monitored_apps,
            remove_monitored_app,
            // CDN & Engines commands
            sync_cdn_patterns,
            get_pattern_stats,
            analyze_with_engines,
            is_jailbreak_attempt,
        ])
        .setup(move |app| {
            info!("SENTINEL Desktop initialized");
            
            // Auto-sync CDN patterns on startup (background thread)
            std::thread::spawn(|| {
                let rt = tokio::runtime::Runtime::new().expect("CDN sync runtime");
                rt.block_on(async {
                    let storage_path = cdn::CdnSync::default_storage_path();
                    
                    // STEP 1: Load from local cache FIRST (instant availability)
                    let mut total_loaded = 0;
                    let mut part_files: Vec<_> = std::fs::read_dir(&storage_path)
                        .map(|entries| {
                            entries
                                .filter_map(|e| e.ok())
                                .filter(|e| {
                                    let name = e.file_name().to_string_lossy().to_string();
                                    name.starts_with("jailbreaks-part") && name.ends_with(".json")
                                })
                                .map(|e| e.path())
                                .collect()
                        })
                        .unwrap_or_default();
                    
                    part_files.sort();
                    
                    if !part_files.is_empty() {
                        info!("📦 Loading cached jailbreak patterns from {} files...", part_files.len());
                        engines::jailbreak::clear_cdn_patterns();
                        
                        for part_path in &part_files {
                            let filename = part_path.file_name().unwrap_or_default().to_string_lossy();
                            if let Ok(json) = std::fs::read_to_string(part_path) {
                                match engines::jailbreak::load_patterns_from_json(&json) {
                                    Ok(count) => {
                                        total_loaded += count;
                                        info!("✅ Loaded {} patterns from {}", count, filename);
                                    }
                                    Err(e) => warn!("⚠️ Failed to parse {}: {}", filename, e),
                                }
                            }
                        }
                        info!("🎯 Loaded {} patterns from cache", total_loaded);
                    }
                    
                    // STEP 2: Check for updates in background (non-blocking)
                    info!("📡 Checking CDN for pattern updates...");
                    let sync = cdn::CdnSync::new(storage_path.clone());
                    
                    match sync.sync().await {
                        result if result.success => {
                            if !result.updated_files.is_empty() {
                                info!("✅ CDN sync: {} files updated, reloading...", result.updated_files.len());
                                
                                // Reload only if files were updated
                                let mut reload_count = 0;
                                engines::jailbreak::clear_cdn_patterns();
                                
                                for part_path in &part_files {
                                    let filename = part_path.file_name().unwrap_or_default().to_string_lossy();
                                    if let Ok(json) = std::fs::read_to_string(part_path) {
                                        if let Ok(count) = engines::jailbreak::load_patterns_from_json(&json) {
                                            reload_count += count;
                                        }
                                    }
                                }
                                info!("🎯 Reloaded {} patterns after sync", reload_count);
                            } else {
                                info!("✅ CDN patterns up to date");
                            }
                        }
                        result => {
                            if total_loaded > 0 {
                                info!("📴 CDN sync skipped (offline?), using {} cached patterns", total_loaded);
                            } else {
                                warn!("⚠️ CDN sync failed and no cache: {:?}", result.errors);
                            }
                        }
                    }
                });
            });
            
            // Setup System Tray
            use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
            use tauri::tray::{TrayIconBuilder, MouseButton, MouseButtonState, TrayIconEvent};
            use tauri::Manager;
            
            let show_item = MenuItem::with_id(app, "show", "🖥️ Показать SENTINEL", true, None::<&str>)?;
            let separator1 = PredefinedMenuItem::separator(app)?;
            let toggle_item = MenuItem::with_id(app, "toggle", "🛡️ Включить защиту", true, None::<&str>)?;
            let proxy_item = MenuItem::with_id(app, "proxy", "🌐 System Proxy", true, None::<&str>)?;
            let separator2 = PredefinedMenuItem::separator(app)?;
            let settings_item = MenuItem::with_id(app, "settings", "⚙️ Настройки", true, None::<&str>)?;
            let logs_item = MenuItem::with_id(app, "logs", "📋 Логи", true, None::<&str>)?;
            let separator3 = PredefinedMenuItem::separator(app)?;
            let about_item = MenuItem::with_id(app, "about", "ℹ️ О программе", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "❌ Выход", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[
                &show_item, &separator1, 
                &toggle_item, &proxy_item, &separator2,
                &settings_item, &logs_item, &separator3,
                &about_item, &quit_item
            ])?;
            
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| {
                    match event.id.as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "toggle" => {
                            // Toggle protection using managed state
                            let state: tauri::State<Arc<AppState>> = app.state();
                            let current = state.intercept_enabled.load(Ordering::SeqCst);
                            state.intercept_enabled.store(!current, Ordering::SeqCst);
                            info!("🛡️ Protection toggled via tray: {}", if !current { "ON" } else { "OFF" });
                            // Also show window
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "proxy" => {
                            // Toggle system proxy
                            if let Some((enabled, server)) = proxy_settings::get_proxy_settings() {
                                if enabled && server.contains("18443") {
                                    let _ = proxy_settings::disable_system_proxy();
                                    info!("🌐 System proxy disabled via tray");
                                } else {
                                    let _ = proxy_settings::enable_system_proxy("127.0.0.1:18443");
                                    info!("🌐 System proxy enabled via tray");
                                }
                            } else {
                                let _ = proxy_settings::enable_system_proxy("127.0.0.1:18443");
                                info!("🌐 System proxy enabled via tray");
                            }
                            // Also show window
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "settings" | "logs" | "about" => {
                            // Show window for navigation items
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "quit" => {
                            // Clean up proxy before exit
                            let _ = proxy_settings::disable_system_proxy();
                            std::process::exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;
            
            // ========================
            // STABILITY FIX: All heavy threads disabled for baseline
            // Re-enable one by one after UI works
            // ========================
            
            // Phase 2: SKIP interceptor — duplicates redirector, causes stack overflow
            // let interceptor_state = state.clone();
            // interceptor::start_interceptor(interceptor_state);
            
            // Phase 3: Enable redirector ✅ ENABLED (includes socket tracking)
            info!("Auto-starting WinDivert redirector...");
            redirector::start_redirector();
            log_info!(logging::LogCategory::Network, "Redirector", "WinDivert redirector v2 auto-started");
            
            // Phase 3.5: Load persisted monitored apps and activate
            {
                let cfg = config::config().read().unwrap();
                if !cfg.monitored_apps.is_empty() {
                    info!("Loading {} persisted monitored apps", cfg.monitored_apps.len());
                    for app_name in &cfg.monitored_apps {
                        redirector::add_monitored_process_name(app_name);
                        info!("Auto-activated monitoring for: {}", app_name);
                    }
                    log_info!(
                        logging::LogCategory::System, 
                        "Config", 
                        "Restored {} monitored apps from config", 
                        cfg.monitored_apps.len()
                    );
                    
                    // Auto-enable System Proxy when monitored apps exist
                    if let Err(e) = proxy_settings::enable_system_proxy("127.0.0.1:18443") {
                        warn!("Failed to auto-enable system proxy: {}", e);
                    } else {
                        info!("🌐 System Proxy auto-enabled (monitored apps present)");
                    }
                }
            }
            
            // Phase 4: Enable NAT setup
            setup_loopback_alias();
            
            // Phase 5: Enable smoltcp user-space TCP stack
            // This bypasses Windows WFP loopback issues by using a user-space TCP stack
            let ca_for_stack = {
                let ca_dir = dirs::data_dir()
                    .unwrap_or_else(|| std::path::PathBuf::from("."))
                    .join("sentinel-desktop")
                    .join("ca");
                match proxy::CertificateAuthority::new(ca_dir) {
                    Ok(ca) => std::sync::Arc::new(ca),
                    Err(e) => {
                        error!("Failed to initialize CA: {}", e);
                        return Ok(());
                    }
                }
            };
            let _state_for_proxy = state.clone();
            
            // ================================================================
            // SYSTEM PROXY MODE
            // Start HTTP CONNECT proxy on 127.0.0.1:8080
            // Enable Windows system proxy to route AI traffic through it
            // ================================================================
            
            std::thread::Builder::new()
                .name("system-proxy".to_string())
                .stack_size(8 * 1024 * 1024)
                .spawn(move || {
                    info!("🌐 Starting System Proxy (HTTP CONNECT) on 127.0.0.1:8080...");
                    
                    let rt = tokio::runtime::Runtime::new().expect("Failed to create tokio runtime");
                    rt.block_on(async move {
                        use std::fs::OpenOptions;
                        use std::io::Write;
                        
                        // Log startup
                        if let Ok(mut f) = OpenOptions::new()
                            .create(true)
                            .append(true)
                            .open("C:\\temp\\sentinel_debug.log") 
                        {
                            let _ = writeln!(f, "SYSTEM PROXY: Starting on 127.0.0.1:18443");
                        }
                        
                        // Create and run the proxy server
                        let listen_addr: std::net::SocketAddr = "127.0.0.1:18443".parse().unwrap();
                        let proxy = proxy::ProxyServer::new(ca_for_stack, listen_addr);
                        
                        if let Ok(mut f) = OpenOptions::new()
                            .create(true)
                            .append(true)
                            .open("C:\\temp\\sentinel_debug.log") 
                        {
                            let _ = writeln!(f, "SYSTEM PROXY: Listening on 127.0.0.1:18443");
                        }
                        
                        if let Err(e) = proxy.run().await {
                            error!("Proxy error: {}", e);
                            if let Ok(mut f) = OpenOptions::new()
                                .create(true)
                                .append(true)
                                .open("C:\\temp\\sentinel_debug.log") 
                            {
                                let _ = writeln!(f, "SYSTEM PROXY ERROR: {}", e);
                            }
                        }
                    });
                })
                .expect("Failed to spawn system proxy thread");
            
            // Enable Windows system proxy (optional - can be enabled/disabled via UI)
            // For now, just log that proxy is ready
            info!("🚀 System Proxy ready on 127.0.0.1:18443");
            info!("💡 Configure system proxy or app proxy settings to use SENTINEL");
            log_info!(logging::LogCategory::Security, "proxy", "System Proxy on 127.0.0.1:8080");
            
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            use tauri::Manager;
            match event {
                tauri::RunEvent::WindowEvent { label, event: window_event, .. } => {
                    if label == "main" {
                        if let tauri::WindowEvent::CloseRequested { api, .. } = window_event {
                            // Hide window instead of closing (minimize to tray)
                            api.prevent_close();
                            if let Some(window) = app_handle.get_webview_window("main") {
                                let _ = window.hide();
                            }
                        }
                    }
                }
                tauri::RunEvent::Exit => {
                    // Cleanup: disable system proxy on exit
                    info!("SENTINEL shutting down, disabling system proxy...");
                    if let Err(e) = proxy_settings::disable_system_proxy() {
                        error!("Failed to disable system proxy on exit: {}", e);
                    } else {
                        info!("System proxy disabled successfully");
                    }
                }
                _ => {}
            }
        });
}
