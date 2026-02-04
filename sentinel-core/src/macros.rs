//! Pattern compilation macros and utilities
//!
//! Provides safe pattern compilation with clear error messages.

/// Compile a regex pattern with a descriptive panic message.
///
/// Used for static patterns that are validated at compile-time.
/// If the pattern is invalid, panics with a clear message.
///
/// # Example
/// ```ignore
/// let re = regex!("sql_injection", r"(?i)\bunion\b.*\bselect\b");
/// ```
#[macro_export]
macro_rules! regex {
    ($name:expr, $pattern:expr) => {
        regex::Regex::new($pattern)
            .expect(concat!("Invalid regex pattern: ", $name))
    };
}

/// Compile multiple regex patterns into a Vec with detailed error messages.
///
/// # Example
/// ```ignore
/// patterns![
///     ("pattern_name", r"regex", 0.8),
///     ("another", r"regex2", 0.9),
/// ]
/// ```
#[macro_export]
macro_rules! patterns {
    [$(($name:expr, $pattern:expr, $confidence:expr)),* $(,)?] => {
        vec![
            $(
                (
                    regex::Regex::new($pattern)
                        .expect(concat!("Invalid pattern '", $name, "'")),
                    $name,
                    $confidence
                ),
            )*
        ]
    };
}
