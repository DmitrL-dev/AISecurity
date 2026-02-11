//! Error types for SENTINEL Core
//!
//! Provides structured error handling with clear error messages.

use thiserror::Error;

/// Main error type for SENTINEL Core operations.
#[derive(Error, Debug)]
pub enum SentinelError {
    /// Pattern compilation failed
    #[error("Pattern compilation error: {pattern} - {reason}")]
    PatternCompile {
        pattern: String,
        reason: String,
    },

    /// Engine initialization failed
    #[error("Engine initialization failed: {engine} - {reason}")]
    EngineInit {
        engine: String,
        reason: String,
    },

    /// Analysis error
    #[error("Analysis failed: {0}")]
    Analysis(String),

    /// Unicode normalization error
    #[error("Unicode normalization failed: {0}")]
    Unicode(String),

    /// Configuration error
    #[error("Configuration error: {0}")]
    Config(String),
}

/// Result type alias for SENTINEL operations.
pub type SentinelResult<T> = Result<T, SentinelError>;

impl From<regex::Error> for SentinelError {
    fn from(err: regex::Error) -> Self {
        SentinelError::PatternCompile {
            pattern: "regex".to_string(),
            reason: err.to_string(),
        }
    }
}

impl From<SentinelError> for pyo3::PyErr {
    fn from(err: SentinelError) -> Self {
        pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
    }
}
