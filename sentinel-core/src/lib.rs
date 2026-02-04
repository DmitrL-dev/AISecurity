//! SENTINEL Core — High-Performance AI Security Engine
//!
//! Rust extension for SENTINEL Brain providing:
//! - Aho-Corasick keyword pre-filtering
//! - Regex pattern matching
//! - Unicode normalization
//! - 8 Super-Engines consolidating 220 Python engines

use pyo3::prelude::*;

mod engines;
mod patterns;
mod unicode_norm;

use engines::{AnalysisResult, SentinelEngine};

/// Quick scan function for one-shot detection
#[pyfunction]
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
    Ok(())
}
