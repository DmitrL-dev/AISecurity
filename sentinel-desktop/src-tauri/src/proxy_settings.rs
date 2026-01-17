//! Windows System Proxy Settings Management
//!
//! Controls Windows proxy settings via registry for transparent interception.

use tracing::{info, error};
use winreg::enums::*;
use winreg::RegKey;

const INTERNET_SETTINGS_PATH: &str = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings";

/// Enable system proxy pointing to SENTINEL
pub fn enable_system_proxy(proxy_addr: &str) -> Result<(), Box<dyn std::error::Error>> {
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let (key, _) = hkcu.create_subkey(INTERNET_SETTINGS_PATH)?;
    
    // Enable proxy
    key.set_value("ProxyEnable", &1u32)?;
    key.set_value("ProxyServer", &proxy_addr)?;
    
    // Bypass for local addresses
    key.set_value("ProxyOverride", &"localhost;127.*;10.*;192.168.*;<local>")?;
    
    // Notify Internet Explorer/Edge of settings change
    notify_proxy_change();
    
    info!("✅ System proxy enabled: {}", proxy_addr);
    Ok(())
}

/// Disable system proxy
pub fn disable_system_proxy() -> Result<(), Box<dyn std::error::Error>> {
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let (key, _) = hkcu.create_subkey(INTERNET_SETTINGS_PATH)?;
    
    // Disable proxy
    key.set_value("ProxyEnable", &0u32)?;
    
    notify_proxy_change();
    
    info!("✅ System proxy disabled");
    Ok(())
}

/// Get current proxy settings
pub fn get_proxy_settings() -> Option<(bool, String)> {
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let key = hkcu.open_subkey(INTERNET_SETTINGS_PATH).ok()?;
    
    let enabled: u32 = key.get_value("ProxyEnable").unwrap_or(0);
    let server: String = key.get_value("ProxyServer").unwrap_or_default();
    
    Some((enabled != 0, server))
}

/// Notify Windows of proxy settings change
fn notify_proxy_change() {
    // Call InternetSetOptionW to notify of settings change
    use windows::Win32::Networking::WinInet::*;
    
    unsafe {
        // INTERNET_OPTION_SETTINGS_CHANGED = 39
        // INTERNET_OPTION_REFRESH = 37
        let _ = InternetSetOptionW(
            None,
            INTERNET_OPTION_SETTINGS_CHANGED,
            None,
            0,
        );
        let _ = InternetSetOptionW(
            None,
            INTERNET_OPTION_REFRESH,
            None,
            0,
        );
    }
}

/// RAII guard that restores proxy settings when dropped
#[allow(dead_code)]
pub struct ProxyGuard {
    original_enabled: bool,
    original_server: String,
}

impl ProxyGuard {
    pub fn new(new_proxy: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let (original_enabled, original_server) = get_proxy_settings()
            .unwrap_or((false, String::new()));
        
        enable_system_proxy(new_proxy)?;
        
        Ok(Self {
            original_enabled,
            original_server,
        })
    }
}

impl Drop for ProxyGuard {
    fn drop(&mut self) {
        if self.original_enabled {
            if let Err(e) = enable_system_proxy(&self.original_server) {
                error!("Failed to restore proxy settings: {}", e);
            }
        } else {
            if let Err(e) = disable_system_proxy() {
                error!("Failed to disable proxy: {}", e);
            }
        }
    }
}
