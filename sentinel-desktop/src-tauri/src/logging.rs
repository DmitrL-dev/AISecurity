//! SENTINEL Desktop - Enhanced Logging System
//!
//! Multi-level logging with file output and UI integration.

use std::sync::{Arc, RwLock};
use std::collections::VecDeque;
use chrono::Local;
use serde::{Serialize, Deserialize};

/// Log levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogLevel {
    Debug = 0,
    Info = 1,
    Warn = 2,
    Error = 3,
}

impl std::fmt::Display for LogLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LogLevel::Debug => write!(f, "DEBUG"),
            LogLevel::Info => write!(f, "INFO"),
            LogLevel::Warn => write!(f, "WARN"),
            LogLevel::Error => write!(f, "ERROR"),
        }
    }
}

/// Log categories for filtering
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogCategory {
    System,     // App lifecycle, config
    Network,    // Connections, traffic
    Proxy,      // TLS inspection, proxy events
    Security,   // Threats, blocks, alerts
    Engine,     // Detection engine results
}

impl std::fmt::Display for LogCategory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LogCategory::System => write!(f, "SYS"),
            LogCategory::Network => write!(f, "NET"),
            LogCategory::Proxy => write!(f, "PROXY"),
            LogCategory::Security => write!(f, "SEC"),
            LogCategory::Engine => write!(f, "ENG"),
        }
    }
}

/// Enhanced log entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnhancedLogEntry {
    pub timestamp: String,
    pub level: LogLevel,
    pub category: LogCategory,
    pub source: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<String>,
}

impl EnhancedLogEntry {
    pub fn new(level: LogLevel, category: LogCategory, source: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            timestamp: Local::now().format("%Y-%m-%d %H:%M:%S%.3f").to_string(),
            level,
            category,
            source: source.into(),
            message: message.into(),
            details: None,
        }
    }
    
    pub fn with_details(mut self, details: impl Into<String>) -> Self {
        self.details = Some(details.into());
        self
    }
}

/// Global logger state
pub struct Logger {
    entries: RwLock<VecDeque<EnhancedLogEntry>>,
    /// Separate buffer for AI-related logs (higher priority)
    ai_entries: RwLock<VecDeque<EnhancedLogEntry>>,
    min_level: RwLock<LogLevel>,
    max_entries: usize,
    max_ai_entries: usize,
}

impl Logger {
    pub fn new(max_entries: usize) -> Self {
        Self {
            entries: RwLock::new(VecDeque::with_capacity(max_entries)),
            ai_entries: RwLock::new(VecDeque::with_capacity(1000)), // AI gets 1000 entries
            min_level: RwLock::new(LogLevel::Info),
            max_entries,
            max_ai_entries: 1000,
        }
    }
    
    pub fn set_level(&self, level: LogLevel) {
        *self.min_level.write().unwrap() = level;
    }
    
    pub fn get_level(&self) -> LogLevel {
        *self.min_level.read().unwrap()
    }
    
    pub fn log(&self, entry: EnhancedLogEntry) {
        let min_level = *self.min_level.read().unwrap();
        if entry.level < min_level {
            return;
        }
        
        // Also log to tracing
        match entry.level {
            LogLevel::Debug => tracing::debug!("[{}] {}: {}", entry.category, entry.source, entry.message),
            LogLevel::Info => tracing::info!("[{}] {}: {}", entry.category, entry.source, entry.message),
            LogLevel::Warn => tracing::warn!("[{}] {}: {}", entry.category, entry.source, entry.message),
            LogLevel::Error => tracing::error!("[{}] {}: {}", entry.category, entry.source, entry.message),
        }
        
        // Check if this is an AI-related log (contains 🤖 or is Security category)
        let is_ai = entry.message.contains("🤖") || entry.category == LogCategory::Security;
        
        if is_ai {
            // Store in AI buffer (priority)
            let mut ai_entries = self.ai_entries.write().unwrap();
            ai_entries.push_front(entry.clone());
            while ai_entries.len() > self.max_ai_entries {
                ai_entries.pop_back();
            }
        }
        
        // Also store in general buffer
        let mut entries = self.entries.write().unwrap();
        entries.push_front(entry);
        while entries.len() > self.max_entries {
            entries.pop_back();
        }
    }
    
    pub fn get_entries(&self, count: usize, level_filter: Option<LogLevel>, category_filter: Option<LogCategory>) -> Vec<EnhancedLogEntry> {
        let entries = self.entries.read().unwrap();
        entries
            .iter()
            .filter(|e| {
                level_filter.map_or(true, |l| e.level >= l) &&
                category_filter.map_or(true, |c| e.category == c)
            })
            .take(count)
            .cloned()
            .collect()
    }
    
    /// Get AI-specific entries (from priority buffer)
    pub fn get_ai_entries(&self, count: usize) -> Vec<EnhancedLogEntry> {
        let ai_entries = self.ai_entries.read().unwrap();
        ai_entries.iter().take(count).cloned().collect()
    }
    
    pub fn clear(&self) {
        self.entries.write().unwrap().clear();
        self.ai_entries.write().unwrap().clear();
    }
}

/// Global logger instance
static LOGGER: once_cell::sync::Lazy<Arc<Logger>> = 
    once_cell::sync::Lazy::new(|| Arc::new(Logger::new(500)));

/// Get global logger
pub fn logger() -> Arc<Logger> {
    Arc::clone(&LOGGER)
}

// Convenience macros
#[macro_export]
macro_rules! log_debug {
    ($cat:expr, $src:expr, $($arg:tt)*) => {
        $crate::logging::logger().log(
            $crate::logging::EnhancedLogEntry::new(
                $crate::logging::LogLevel::Debug,
                $cat,
                $src,
                format!($($arg)*)
            )
        )
    };
}

#[macro_export]
macro_rules! log_info {
    ($cat:expr, $src:expr, $($arg:tt)*) => {
        $crate::logging::logger().log(
            $crate::logging::EnhancedLogEntry::new(
                $crate::logging::LogLevel::Info,
                $cat,
                $src,
                format!($($arg)*)
            )
        )
    };
}

#[macro_export]
macro_rules! log_warn {
    ($cat:expr, $src:expr, $($arg:tt)*) => {
        $crate::logging::logger().log(
            $crate::logging::EnhancedLogEntry::new(
                $crate::logging::LogLevel::Warn,
                $cat,
                $src,
                format!($($arg)*)
            )
        )
    };
}

#[macro_export]
macro_rules! log_error {
    ($cat:expr, $src:expr, $($arg:tt)*) => {
        $crate::logging::logger().log(
            $crate::logging::EnhancedLogEntry::new(
                $crate::logging::LogLevel::Error,
                $cat,
                $src,
                format!($($arg)*)
            )
        )
    };
}

#[macro_export]
macro_rules! log_security {
    ($src:expr, $($arg:tt)*) => {
        $crate::logging::logger().log(
            $crate::logging::EnhancedLogEntry::new(
                $crate::logging::LogLevel::Warn,
                $crate::logging::LogCategory::Security,
                $src,
                format!($($arg)*)
            )
        )
    };
}
