//! Temporal Safety Automata (TSA) Engine
//!
//! Runtime verification engine for LLM tool-call chains.
//! Implements monitor automata for six core safety properties
//! derived from temporal logic specifications:
//!
//! - P1: Data Exfiltration Guard  — `[](read_sensitive -> []~send_external)`
//! - P2: Credential Theft Guard   — `~<>(read_credentials /\ <>send_external)`
//! - P3: Privilege Escalation Guard — `[](privilege_change -> O approval_received)`
//! - P4: Write-Before-Read Guard  — `[](write -> Previously(read))`
//! - P5: Unbounded Chain Guard    — max 5 consecutive calls without confirmation
//! - P6: Auth-Before-Access Guard — `[](db_access -> Previously(auth))`
//!
//! Provides BOTH:
//! 1. `scan(&str)` — text-based detection of temporal violations in logs
//! 2. `check_event()` — structured runtime monitoring of tool-call sequences

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;
use std::sync::atomic::{AtomicU16, AtomicU32, Ordering};

use super::MatchResult;

// ─── Security Predicates ───────────────────────────────────────────

/// Security-relevant predicates encoded as bit flags in a u16.
/// Each tool-call event carries a bitmask of active predicates.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u16)]
pub enum SecurityPredicate {
    SensitiveDataAccessed = 1 << 0,
    CredentialsAccessed = 1 << 1,
    ExternalChannelOpened = 1 << 2,
    PrivilegeElevated = 1 << 3,
    WritePerformed = 1 << 4,
    ApprovalPending = 1 << 5,
    AuthCompleted = 1 << 6,
    FileRead = 1 << 7,
    FileWritten = 1 << 8,
    DbAccessed = 1 << 9,
    CodeExecuted = 1 << 10,
    NetworkAccess = 1 << 11,
    UserConfirmation = 1 << 12,
    ToolChainActive = 1 << 13,
    SandboxActive = 1 << 14,
    AuditLogged = 1 << 15,
}

// ─── Tool-Call Event ───────────────────────────────────────────────

/// A tool-call event to be checked against safety properties.
#[derive(Debug, Clone)]
pub struct ToolCallEvent {
    /// Name of the tool being invoked
    pub tool_name: String,
    /// Bitwise OR of SecurityPredicate flags for this event
    pub predicates: u16,
    /// Position in the tool-call chain
    pub sequence_index: usize,
}

// ─── Monitor Verdict ───────────────────────────────────────────────

/// Verdict returned by the temporal safety monitor.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MonitorVerdict {
    /// All properties satisfied
    Safe,
    /// Property at the given index was violated (0-5)
    Violation(u8),
    /// GPS score above warning threshold (approaching danger)
    Warning,
}

// ─── Property Monitor ──────────────────────────────────────────────

/// A single property monitor automaton with flat transition table.
struct PropertyMonitor {
    /// Human-readable property name
    name: &'static str,
    /// Current automaton state (atomic for thread safety)
    current_state: AtomicU32,
    /// Flattened transition table: transitions[state * num_events + event] -> next_state
    transitions: Vec<u32>,
    /// Number of distinct event categories for this property
    num_events: usize,
    /// Whether each state is a violation state
    violation_states: Vec<bool>,
    /// (predicate_mask, event_index) — checked in order; first match wins
    event_map: Vec<(u16, usize)>,
    /// Default event index when no predicate mask matches
    default_event: usize,
}

impl PropertyMonitor {
    /// Classify a predicate bitmask into an event index for this property.
    fn classify_event(&self, predicates: u16) -> usize {
        for &(mask, event) in &self.event_map {
            if predicates & mask != 0 {
                return event;
            }
        }
        self.default_event
    }

    /// Advance the monitor by one step. Returns the new state.
    fn step(&self, predicates: u16) -> u32 {
        let event = self.classify_event(predicates);
        let state = self.current_state.load(Ordering::Relaxed) as usize;
        let idx = state * self.num_events + event;
        let next = if idx < self.transitions.len() {
            self.transitions[idx]
        } else {
            state as u32
        };
        self.current_state.store(next, Ordering::Relaxed);
        next
    }

    /// Check if the monitor is currently in a violation state.
    fn is_violation(&self) -> bool {
        let state = self.current_state.load(Ordering::Relaxed) as usize;
        state < self.violation_states.len() && self.violation_states[state]
    }

    /// Reset the monitor to its initial state.
    fn reset(&self) {
        self.current_state.store(0, Ordering::Relaxed);
    }
}

/// Maximum consecutive tool calls without user confirmation (P5).
const MAX_CHAIN_LENGTH: u16 = 5;

// ─── Property Monitor Builders ─────────────────────────────────────
//
// Each builder creates a PropertyMonitor with hand-compiled transition
// tables for the corresponding LTL safety property.

/// P1: Data Exfiltration Guard
/// `□(read_sensitive → □¬send_external)`
/// States: 0=INIT, 1=SENSITIVE_READ, 2=VIOLATION
/// Events: 0=sensitive_read, 1=external_channel, 2=other
fn build_p1_exfiltration_guard() -> PropertyMonitor {
    // 3 states × 3 events = 9 transitions
    #[rustfmt::skip]
    let transitions = vec![
        // State 0 (INIT)
        1, // + sensitive_read  → SENSITIVE_READ
        0, // + external_channel → INIT (ok, no sensitive data yet)
        0, // + other           → INIT
        // State 1 (SENSITIVE_READ) — sticky
        1, // + sensitive_read  → SENSITIVE_READ
        2, // + external_channel → VIOLATION
        1, // + other           → SENSITIVE_READ
        // State 2 (VIOLATION) — absorbing
        2, // + sensitive_read  → VIOLATION
        2, // + external_channel → VIOLATION
        2, // + other           → VIOLATION
    ];

    PropertyMonitor {
        name: "P1_exfiltration_guard",
        current_state: AtomicU32::new(0),
        transitions,
        num_events: 3,
        violation_states: vec![false, false, true],
        event_map: vec![
            (SecurityPredicate::SensitiveDataAccessed as u16, 0),
            (SecurityPredicate::ExternalChannelOpened as u16, 1),
        ],
        default_event: 2,
    }
}

/// P2: Credential Theft Guard
/// `¬◇(read_credentials ∧ ◇send_external)`
/// States: 0=INIT, 1=CREDS_READ, 2=VIOLATION
/// Events: 0=creds_read, 1=external_channel, 2=other
fn build_p2_credential_guard() -> PropertyMonitor {
    #[rustfmt::skip]
    let transitions = vec![
        // State 0 (INIT)
        1, 0, 0,
        // State 1 (CREDS_READ) — sticky
        1, 2, 1,
        // State 2 (VIOLATION) — absorbing
        2, 2, 2,
    ];

    PropertyMonitor {
        name: "P2_credential_theft_guard",
        current_state: AtomicU32::new(0),
        transitions,
        num_events: 3,
        violation_states: vec![false, false, true],
        event_map: vec![
            (SecurityPredicate::CredentialsAccessed as u16, 0),
            (SecurityPredicate::ExternalChannelOpened as u16, 1),
        ],
        default_event: 2,
    }
}

/// P3: Privilege Escalation Guard
/// `□(privilege_change → ○approval_received)`
/// States: 0=INIT, 1=AWAITING_APPROVAL, 2=VIOLATION
/// Events: 0=privilege_elevated, 1=user_confirmation, 2=other
fn build_p3_privilege_guard() -> PropertyMonitor {
    #[rustfmt::skip]
    let transitions = vec![
        // State 0 (INIT)
        1, 0, 0,
        // State 1 (AWAITING_APPROVAL)
        2, 0, 2, // confirmation → INIT, anything else → VIOLATION
        // State 2 (VIOLATION) — absorbing
        2, 2, 2,
    ];

    PropertyMonitor {
        name: "P3_privilege_escalation_guard",
        current_state: AtomicU32::new(0),
        transitions,
        num_events: 3,
        violation_states: vec![false, false, true],
        event_map: vec![
            (SecurityPredicate::PrivilegeElevated as u16, 0),
            (SecurityPredicate::UserConfirmation as u16, 1),
        ],
        default_event: 2,
    }
}

/// P4: Write-Before-Read Guard
/// `□(write_performed → Previously(file_read))`
/// States: 0=INIT, 1=READ_DONE, 2=VIOLATION
/// Events: 0=file_read, 1=write_performed, 2=other
fn build_p4_write_before_read_guard() -> PropertyMonitor {
    #[rustfmt::skip]
    let transitions = vec![
        // State 0 (INIT) — no read yet
        1, 2, 0,
        // State 1 (READ_DONE) — read happened
        1, 1, 1, // write is ok after read
        // State 2 (VIOLATION) — absorbing
        2, 2, 2,
    ];

    PropertyMonitor {
        name: "P4_write_before_read_guard",
        current_state: AtomicU32::new(0),
        transitions,
        num_events: 3,
        violation_states: vec![false, false, true],
        event_map: vec![
            (SecurityPredicate::FileRead as u16, 0),
            (SecurityPredicate::WritePerformed as u16, 1),
        ],
        default_event: 2,
    }
}

/// P5: Unbounded Chain Guard — counting property handled via AtomicU16
/// This monitor always stays in INIT; the counter is managed externally.
/// We still create a monitor so indexing is uniform, but use a trivial automaton.
/// States: 0=OK, 1=VIOLATION
/// Events: 0=user_confirmation, 1=other
fn build_p5_chain_guard() -> PropertyMonitor {
    #[rustfmt::skip]
    let transitions = vec![
        // State 0 (OK)
        0, 0, // stays OK; actual counting done externally
        // State 1 (VIOLATION) — set externally when counter > MAX
        1, 1,
    ];

    PropertyMonitor {
        name: "P5_unbounded_chain_guard",
        current_state: AtomicU32::new(0),
        transitions,
        num_events: 2,
        violation_states: vec![false, true],
        event_map: vec![(SecurityPredicate::UserConfirmation as u16, 0)],
        default_event: 1,
    }
}

/// P6: Auth-Before-Access Guard
/// `□(db_accessed → Previously(auth_completed))`
/// States: 0=INIT, 1=AUTHED, 2=VIOLATION
/// Events: 0=auth_completed, 1=db_accessed, 2=other
fn build_p6_auth_guard() -> PropertyMonitor {
    #[rustfmt::skip]
    let transitions = vec![
        // State 0 (INIT) — not authenticated
        1, 2, 0,
        // State 1 (AUTHED) — authenticated
        1, 1, 1, // db_access ok after auth
        // State 2 (VIOLATION) — absorbing
        2, 2, 2,
    ];

    PropertyMonitor {
        name: "P6_auth_before_access_guard",
        current_state: AtomicU32::new(0),
        transitions,
        num_events: 3,
        violation_states: vec![false, false, true],
        event_map: vec![
            (SecurityPredicate::AuthCompleted as u16, 0),
            (SecurityPredicate::DbAccessed as u16, 1),
        ],
        default_event: 2,
    }
}

// ─── Text Scanning — Aho-Corasick hints + Regex patterns ───────────

/// Pre-compiled Aho-Corasick automaton for fast pre-filtering of text.
static TSA_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Exfiltration sequences
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "curl",
            "wget",
            "fetch",
            "send",
            "post",
            "http",
            // Privilege escalation
            "sudo",
            "chmod",
            "escalat",
            "elevat",
            "admin",
            "root",
            "privilege",
            // Tool chains
            "tool_call",
            "tool call",
            // Write/read ordering
            "write",
            "delete",
            "drop",
            "truncate",
            "update",
            "without",
            "before",
            // Auth
            "database",
            "query",
            "select",
            "auth",
            "login",
            // Confirmation
            "confirm",
            "approv",
        ])
        .expect("Failed to build TSA hints")
});

/// Regex patterns for temporal safety violation detection in text/logs.
/// Grouped by property: (compiled_regex, pattern_name, confidence).
static TSA_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // ── P1/P2: Exfiltration sequences in tool logs ──
        (
            Regex::new(r"(?i)(?:read|access|get|load|fetch)\s+(?:the\s+)?(?:password|secret|key|token|credential|api.?key|private.?key).*?(?:curl|wget|fetch|send|post|http|upload|forward)")
                .expect("regex"),
            "temporal_exfil_read_then_send",
            0.92,
        ),
        (
            Regex::new(r"(?i)(?:SELECT|read|get|load|dump)\s+.*?(?:users|credentials|secrets|passwords|tokens).*?(?:external|remote|http|api|webhook|send)")
                .expect("regex"),
            "temporal_exfil_query_then_external",
            0.90,
        ),
        (
            Regex::new(r"(?i)(?:access|read)\s+(?:sensitive|confidential|private)\s+(?:data|info|file).*?(?:send|transmit|upload|post|forward|exfil)")
                .expect("regex"),
            "temporal_sensitive_then_transmit",
            0.93,
        ),
        (
            Regex::new(r"(?i)(?:extract|steal|copy)\s+(?:credentials?|passwords?|secrets?|keys?).*?(?:to\s+)?(?:external|remote|attacker|server)")
                .expect("regex"),
            "temporal_credential_theft_sequence",
            0.95,
        ),

        // ── P3: Privilege escalation without approval ──
        (
            Regex::new(r"(?i)(?:sudo|chmod|escalat|elevat|admin|root)\s+.*?(?:exec|run|call|invoke)")
                .expect("regex"),
            "temporal_priv_escalation_exec",
            0.88,
        ),
        (
            Regex::new(r"(?i)privilege\s+(?:change|escal|elevat|increase|raise)")
                .expect("regex"),
            "temporal_priv_no_approval",
            0.82,
        ),
        (
            Regex::new(r"(?i)(?:grant|assign|set)\s+(?:admin|root|superuser|elevated)\s+(?:role|access|permission)")
                .expect("regex"),
            "temporal_grant_without_approval",
            0.80,
        ),

        // ── P4: Write before read violations ──
        (
            Regex::new(r"(?i)(?:write|delete|drop|truncate|update|INSERT)\s+.*?(?:without|before|no)\s+(?:read|check|verify|review)")
                .expect("regex"),
            "temporal_write_before_read",
            0.89,
        ),
        (
            Regex::new(r"(?i)(?:blind|unverified|unchecked)\s+(?:write|update|delete|modify|overwrite)")
                .expect("regex"),
            "temporal_blind_write",
            0.85,
        ),
        (
            Regex::new(r"(?i)(?:overwrite|replace|destroy)\s+(?:without|before)\s+(?:reading|backing.?up|checking|verifying)")
                .expect("regex"),
            "temporal_overwrite_no_check",
            0.87,
        ),

        // ── P5: Unbounded tool chains ──
        (
            Regex::new(r"(?i)tool.?call.*tool.?call.*tool.?call.*tool.?call.*tool.?call")
                .expect("regex"),
            "temporal_unbounded_chain",
            0.78,
        ),
        (
            Regex::new(r"(?i)(?:chain|sequence|series)\s+(?:of\s+)?(?:tool|function|api)\s+(?:calls?|invocations?).*(?:unbounded|unlimited|no\s+limit|without\s+(?:check|confirm))")
                .expect("regex"),
            "temporal_unbounded_chain_desc",
            0.83,
        ),
        (
            Regex::new(r"(?i)(?:automated|autonomous)\s+(?:tool|function)\s+(?:execution|calls?).*(?:without|no)\s+(?:human|user|manual)\s+(?:review|confirm|approval)")
                .expect("regex"),
            "temporal_autonomous_no_confirm",
            0.86,
        ),

        // ── P6: Unauthenticated access ──
        (
            Regex::new(r"(?i)(?:database|db|query|SELECT|table)\s+.*?(?:without|no|missing|skip)\s+(?:auth|login|token|session|credential)")
                .expect("regex"),
            "temporal_unauth_db_access",
            0.91,
        ),
        (
            Regex::new(r"(?i)(?:bypass|skip|ignore)\s+(?:auth|authentication|login|credential)\s+.*?(?:access|query|read|write|connect)")
                .expect("regex"),
            "temporal_auth_bypass_access",
            0.90,
        ),
        (
            Regex::new(r"(?i)(?:unauthenticated|anonymous|guest)\s+(?:access|query|connection)\s+(?:to\s+)?(?:database|db|backend|api)")
                .expect("regex"),
            "temporal_anon_db_access",
            0.88,
        ),

        // ── Cross-property: combined temporal patterns ──
        (
            Regex::new(r"(?i)(?:read|access).*?(?:then|and|next|after|followed.?by).*?(?:send|post|upload|transmit|forward)")
                .expect("regex"),
            "temporal_read_then_send_generic",
            0.80,
        ),
        (
            Regex::new(r"(?i)(?:first|step.?1).*?(?:read|get|access|fetch).*?(?:then|step.?2|next|after).*?(?:send|post|curl|wget|upload)")
                .expect("regex"),
            "temporal_step_by_step_exfil",
            0.88,
        ),
    ]
});

// ─── GPS Pre-computation ───────────────────────────────────────────

/// Compute the GPS (Goal Predictability Score) table for a property monitor.
/// GPS(state) = |dangerous_transitions| / |total_transitions|
/// A "dangerous" transition is one that leads to a violation state.
fn compute_gps_table(monitor: &PropertyMonitor) -> Vec<f64> {
    let num_states = monitor.violation_states.len();
    let num_events = monitor.num_events;
    let mut gps = Vec::with_capacity(num_states);

    for state in 0..num_states {
        let mut dangerous = 0usize;
        for event in 0..num_events {
            let idx = state * num_events + event;
            if idx < monitor.transitions.len() {
                let next = monitor.transitions[idx] as usize;
                if next < monitor.violation_states.len() && monitor.violation_states[next] {
                    dangerous += 1;
                }
            }
        }
        gps.push(if num_events > 0 {
            dangerous as f64 / num_events as f64
        } else {
            0.0
        });
    }
    gps
}

// ─── TemporalSafetyEngine ──────────────────────────────────────────

/// Temporal Safety Automata engine — runtime verification for tool-call chains.
///
/// Monitors six safety properties via hand-compiled automata.
/// Also provides text-based `scan()` for detecting temporal violations in logs.
pub struct TemporalSafetyEngine {
    /// Per-property monitor automata (P1–P6)
    monitors: Vec<PropertyMonitor>,
    /// GPS lookup table: gps_table[property_idx][state] → f64
    gps_table: Vec<Vec<f64>>,
    /// Tool call counter for the counting property (P5)
    chain_counter: AtomicU16,
}

impl TemporalSafetyEngine {
    /// Create a new engine with all six property monitors.
    pub fn new() -> Self {
        let monitors = vec![
            build_p1_exfiltration_guard(),
            build_p2_credential_guard(),
            build_p3_privilege_guard(),
            build_p4_write_before_read_guard(),
            build_p5_chain_guard(),
            build_p6_auth_guard(),
        ];

        let gps_table: Vec<Vec<f64>> = monitors.iter().map(|m| compute_gps_table(m)).collect();

        Self {
            monitors,
            gps_table,
            chain_counter: AtomicU16::new(0),
        }
    }

    /// Check a tool-call event against all safety properties — O(1) per property.
    pub fn check_event(&self, event: &ToolCallEvent) -> MonitorVerdict {
        let preds = event.predicates;

        // Handle P5 counting property first
        if preds & (SecurityPredicate::UserConfirmation as u16) != 0 {
            self.chain_counter.store(0, Ordering::Relaxed);
        } else {
            let prev = self.chain_counter.fetch_add(1, Ordering::Relaxed);
            if prev + 1 > MAX_CHAIN_LENGTH {
                // Set P5 monitor to violation state
                self.monitors[4].current_state.store(1, Ordering::Relaxed);
                return MonitorVerdict::Violation(4);
            }
        }

        // Step all property monitors
        for (i, monitor) in self.monitors.iter().enumerate() {
            if i == 4 {
                continue; // P5 handled above via counter
            }
            monitor.step(preds);
            if monitor.is_violation() {
                return MonitorVerdict::Violation(i as u8);
            }
        }

        // Check GPS for warnings
        let gps = self.gps_score();
        if gps > 0.7 {
            return MonitorVerdict::Warning;
        }

        MonitorVerdict::Safe
    }

    /// Get current aggregate GPS score (maximum across all properties).
    pub fn gps_score(&self) -> f64 {
        let mut max_gps = 0.0f64;
        for (i, monitor) in self.monitors.iter().enumerate() {
            let state = monitor.current_state.load(Ordering::Relaxed) as usize;
            if let Some(table) = self.gps_table.get(i) {
                if let Some(&score) = table.get(state) {
                    if score > max_gps {
                        max_gps = score;
                    }
                }
            }
        }
        max_gps
    }

    /// Reset all monitors and the chain counter (new session).
    pub fn reset(&self) {
        for monitor in &self.monitors {
            monitor.reset();
        }
        self.chain_counter.store(0, Ordering::Relaxed);
    }

    /// Get per-property status: (name, is_safe).
    pub fn property_status(&self) -> Vec<(&'static str, bool)> {
        self.monitors
            .iter()
            .map(|m| (m.name, !m.is_violation()))
            .collect()
    }

    /// Text-based scan for temporal violation patterns in conversation logs.
    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        if text.is_empty() {
            return Vec::new();
        }

        // Fast pre-filter with Aho-Corasick
        if !TSA_HINTS.is_match(text) {
            return Vec::new();
        }

        let mut matches = Vec::new();
        let lower = text.to_lowercase();

        for (regex, pattern_name, confidence) in TSA_PATTERNS.iter() {
            for mat in regex.find_iter(&lower) {
                matches.push(MatchResult {
                    engine: "temporal_safety".to_string(),
                    pattern: pattern_name.to_string(),
                    confidence: *confidence,
                    start: mat.start(),
                    end: mat.end(),
                });
            }
        }

        matches
    }
}

// ─── PatternMatcher Trait Implementation ───────────────────────────

impl super::traits::PatternMatcher for TemporalSafetyEngine {
    fn name(&self) -> &'static str {
        "temporal_safety"
    }

    fn scan(&self, text: &str) -> Vec<MatchResult> {
        self.scan(text)
    }

    fn category(&self) -> super::traits::EngineCategory {
        super::traits::EngineCategory::Behavioral
    }
}

// ─── Tests ─────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::super::traits::PatternMatcher;
    use super::*;

    /// Helper: create a ToolCallEvent with given predicates.
    fn event(name: &str, predicates: u16, seq: usize) -> ToolCallEvent {
        ToolCallEvent {
            tool_name: name.to_string(),
            predicates,
            sequence_index: seq,
        }
    }

    // ── P1: Data Exfiltration Guard ────────────────────────────────

    #[test]
    fn test_p1_violation_read_sensitive_then_send_external() {
        let engine = TemporalSafetyEngine::new();
        let v1 = engine.check_event(&event(
            "read_db",
            SecurityPredicate::SensitiveDataAccessed as u16,
            0,
        ));
        assert_eq!(v1, MonitorVerdict::Safe);

        let v2 = engine.check_event(&event(
            "http_post",
            SecurityPredicate::ExternalChannelOpened as u16,
            1,
        ));
        assert_eq!(v2, MonitorVerdict::Violation(0));
    }

    #[test]
    fn test_p1_safe_send_external_then_read_sensitive() {
        let engine = TemporalSafetyEngine::new();
        // External send first — no sensitive data read yet → safe
        let v1 = engine.check_event(&event(
            "http_post",
            SecurityPredicate::ExternalChannelOpened as u16,
            0,
        ));
        assert_eq!(v1, MonitorVerdict::Safe);

        let v2 = engine.check_event(&event(
            "read_db",
            SecurityPredicate::SensitiveDataAccessed as u16,
            1,
        ));
        assert_eq!(v2, MonitorVerdict::Safe);
    }

    // ── P2: Credential Theft Guard ─────────────────────────────────

    #[test]
    fn test_p2_violation_credentials_then_external() {
        let engine = TemporalSafetyEngine::new();
        let v1 = engine.check_event(&event(
            "read_creds",
            SecurityPredicate::CredentialsAccessed as u16,
            0,
        ));
        assert_eq!(v1, MonitorVerdict::Safe);

        let v2 = engine.check_event(&event(
            "curl",
            SecurityPredicate::ExternalChannelOpened as u16,
            1,
        ));
        assert_eq!(v2, MonitorVerdict::Violation(1));
    }

    // ── P3: Privilege Escalation Guard ──────────────────────────────

    #[test]
    fn test_p3_violation_escalation_without_approval() {
        let engine = TemporalSafetyEngine::new();
        let v1 = engine.check_event(&event(
            "sudo",
            SecurityPredicate::PrivilegeElevated as u16,
            0,
        ));
        assert_eq!(v1, MonitorVerdict::Safe);

        // Next event is NOT an approval → violation
        let v2 = engine.check_event(&event(
            "run_command",
            SecurityPredicate::CodeExecuted as u16,
            1,
        ));
        assert_eq!(v2, MonitorVerdict::Violation(2));
    }

    #[test]
    fn test_p3_safe_escalation_with_approval() {
        let engine = TemporalSafetyEngine::new();
        let v1 = engine.check_event(&event(
            "sudo",
            SecurityPredicate::PrivilegeElevated as u16,
            0,
        ));
        assert_eq!(v1, MonitorVerdict::Safe);

        // Immediately followed by user confirmation → safe
        let v2 = engine.check_event(&event(
            "confirm",
            SecurityPredicate::UserConfirmation as u16,
            1,
        ));
        assert_eq!(v2, MonitorVerdict::Safe);
    }

    // ── P4: Write-Before-Read Guard ────────────────────────────────

    #[test]
    fn test_p4_violation_write_without_read() {
        let engine = TemporalSafetyEngine::new();
        let v = engine.check_event(&event(
            "write_file",
            SecurityPredicate::WritePerformed as u16,
            0,
        ));
        assert_eq!(v, MonitorVerdict::Violation(3));
    }

    #[test]
    fn test_p4_safe_read_then_write() {
        let engine = TemporalSafetyEngine::new();
        let v1 = engine.check_event(&event("read_file", SecurityPredicate::FileRead as u16, 0));
        assert_eq!(v1, MonitorVerdict::Safe);

        let v2 = engine.check_event(&event(
            "write_file",
            SecurityPredicate::WritePerformed as u16,
            1,
        ));
        assert_eq!(v2, MonitorVerdict::Safe);
    }

    // ── P5: Unbounded Chain Guard ──────────────────────────────────

    #[test]
    fn test_p5_violation_6_calls_without_confirmation() {
        let engine = TemporalSafetyEngine::new();
        // 5 tool calls should be fine
        for i in 0..5 {
            let v =
                engine.check_event(&event("tool", SecurityPredicate::ToolChainActive as u16, i));
            assert_ne!(
                v,
                MonitorVerdict::Violation(4),
                "Call {} should not violate P5",
                i
            );
        }
        // 6th call should violate
        let v6 = engine.check_event(&event("tool", SecurityPredicate::ToolChainActive as u16, 5));
        assert_eq!(v6, MonitorVerdict::Violation(4));
    }

    #[test]
    fn test_p5_safe_confirmation_resets_counter() {
        let engine = TemporalSafetyEngine::new();
        // 4 tool calls
        for i in 0..4 {
            engine.check_event(&event("tool", SecurityPredicate::ToolChainActive as u16, i));
        }
        // User confirmation resets
        engine.check_event(&event(
            "confirm",
            SecurityPredicate::UserConfirmation as u16,
            4,
        ));
        // 4 more tool calls — still safe
        for i in 5..9 {
            let v =
                engine.check_event(&event("tool", SecurityPredicate::ToolChainActive as u16, i));
            assert_ne!(v, MonitorVerdict::Violation(4));
        }
    }

    // ── P6: Auth-Before-Access Guard ───────────────────────────────

    #[test]
    fn test_p6_violation_db_access_without_auth() {
        let engine = TemporalSafetyEngine::new();
        let v = engine.check_event(&event("query_db", SecurityPredicate::DbAccessed as u16, 0));
        assert_eq!(v, MonitorVerdict::Violation(5));
    }

    #[test]
    fn test_p6_safe_auth_then_db_access() {
        let engine = TemporalSafetyEngine::new();
        let v1 = engine.check_event(&event("login", SecurityPredicate::AuthCompleted as u16, 0));
        assert_eq!(v1, MonitorVerdict::Safe);

        let v2 = engine.check_event(&event("query_db", SecurityPredicate::DbAccessed as u16, 1));
        assert_eq!(v2, MonitorVerdict::Safe);
    }

    // ── GPS Warning ────────────────────────────────────────────────

    #[test]
    fn test_gps_warning_state() {
        let engine = TemporalSafetyEngine::new();
        // Move P1 to SENSITIVE_READ state (state 1)
        // In state 1: 1 of 3 transitions leads to violation → GPS = 0.33
        // Move P2 to CREDS_READ state (state 1) as well → GPS = 0.33
        // Neither alone exceeds 0.7, so no warning from those.
        //
        // Instead, test by checking that GPS is computed correctly.
        // P1 state 1 has GPS = 1/3 ≈ 0.33
        engine.check_event(&event(
            "read_sensitive",
            SecurityPredicate::SensitiveDataAccessed as u16,
            0,
        ));
        let gps = engine.gps_score();
        assert!(
            gps > 0.3,
            "GPS should reflect danger from SENSITIVE_READ state, got {}",
            gps
        );
    }

    // ── Reset ──────────────────────────────────────────────────────

    #[test]
    fn test_reset_clears_state() {
        let engine = TemporalSafetyEngine::new();
        // Create a violation
        engine.check_event(&event("write", SecurityPredicate::WritePerformed as u16, 0));
        assert!(engine.monitors[3].is_violation());

        // Reset
        engine.reset();

        // All monitors back to initial state
        for monitor in &engine.monitors {
            assert!(!monitor.is_violation());
            assert_eq!(monitor.current_state.load(Ordering::Relaxed), 0);
        }
        assert_eq!(engine.chain_counter.load(Ordering::Relaxed), 0);
    }

    // ── Text Scan: Positive Cases ──────────────────────────────────

    #[test]
    fn test_scan_exfiltration_sequence() {
        let engine = TemporalSafetyEngine::new();
        let text = "The agent read the password from the config and then used curl to send it to an external server";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect exfiltration sequence");
        assert!(matches.iter().any(|m| m.pattern.contains("exfil")));
    }

    #[test]
    fn test_scan_privilege_escalation() {
        let engine = TemporalSafetyEngine::new();
        let text = "privilege escalation detected without approval or confirmation";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect privilege escalation pattern"
        );
        assert!(matches.iter().any(|m| m.pattern.contains("priv")));
    }

    #[test]
    fn test_scan_unbounded_chain() {
        let engine = TemporalSafetyEngine::new();
        let text = "tool_call then tool_call then tool_call then tool_call then tool_call executed without any break";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect unbounded tool chain");
    }

    #[test]
    fn test_scan_write_before_read() {
        let engine = TemporalSafetyEngine::new();
        let text = "The agent attempted to write the file without reading or checking it first";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect write-before-read pattern"
        );
    }

    #[test]
    fn test_scan_unauth_db_access() {
        let engine = TemporalSafetyEngine::new();
        let text = "database query executed without auth token";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect unauthenticated DB access"
        );
        assert!(matches
            .iter()
            .any(|m| m.pattern.contains("unauth") || m.pattern.contains("auth")));
    }

    // ── Text Scan: Negative Cases ──────────────────────────────────

    #[test]
    fn test_scan_negative_benign_output() {
        let engine = TemporalSafetyEngine::new();
        let text = "The weather today is sunny with a high of 72 degrees Fahrenheit.";
        let matches = engine.scan(text);
        assert!(
            matches.is_empty(),
            "Benign text should not trigger: {:?}",
            matches
        );
    }

    #[test]
    fn test_scan_empty_input() {
        let engine = TemporalSafetyEngine::new();
        let matches = engine.scan("");
        assert!(matches.is_empty());
    }

    // ── PatternMatcher Trait ───────────────────────────────────────

    #[test]
    fn test_trait_name() {
        let engine = TemporalSafetyEngine::new();
        assert_eq!(PatternMatcher::name(&engine), "temporal_safety");
    }

    #[test]
    fn test_trait_category() {
        let engine = TemporalSafetyEngine::new();
        assert_eq!(
            PatternMatcher::category(&engine),
            super::super::traits::EngineCategory::Behavioral
        );
    }

    // ── Property Status ────────────────────────────────────────────

    #[test]
    fn test_property_status_initial() {
        let engine = TemporalSafetyEngine::new();
        let status = engine.property_status();
        assert_eq!(status.len(), 6);
        for (_, is_safe) in &status {
            assert!(is_safe, "All properties should be safe initially");
        }
    }
}
