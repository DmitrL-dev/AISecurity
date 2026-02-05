//! SENTINEL Core — High-Performance AI Security Engine
//!
//! Rust extension for SENTINEL Brain providing:
//! - Aho-Corasick keyword pre-filtering
//! - Regex pattern matching
//! - Unicode normalization
//! - 36 Engines consolidating 187 Python engines

// PyO3 generates code that triggers this false positive
#![allow(clippy::useless_conversion)]

use pyo3::prelude::*;

pub mod engines;
mod error;
#[macro_use]
mod macros;
mod patterns;
pub mod signatures;
pub mod unicode_norm;
pub mod bindings;

pub use error::{SentinelError, SentinelResult};
pub use signatures::{SignatureLoader, PiiSignatures, KeywordSignatures, CompiledPattern};

use engines::{AnalysisResult, SentinelEngine};

/// Quick scan function for one-shot detection
#[pyfunction]
#[allow(clippy::useless_conversion)] // PyO3 requires this return type
fn quick_scan(text: &str) -> PyResult<AnalysisResult> {
    let engine = SentinelEngine::new()?;
    engine.analyze(text)
}

/// Get library version
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Python module definition
#[pymodule]
fn sentinel_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(quick_scan, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_class::<SentinelEngine>()?;
    m.add_class::<AnalysisResult>()?;
    
    // Register all 36 engines via EngineRegistry
    bindings::register_bindings(m)?;
    
    Ok(())
}
