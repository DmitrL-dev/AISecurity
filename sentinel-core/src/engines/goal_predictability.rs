//! Goal Predictability Score (GPS) Engine
//!
//! A predictive defense engine that catches action chains HEADING toward
//! danger BEFORE they arrive. Because the abstract security state space is
//! small (16 bits = 65,536 states), full enumeration of next states is
//! tractable. GPS counts what fraction of possible continuations lead to
//! dangerous states.
//!
//! GPS > 0.7 → WARNING: 70%+ of continuations lead to danger
//! GPS > 0.9 → BLOCK:   almost all paths are dangerous
//!
//! Also provides text-based `scan()` for detecting goal-predictability
//! indicators: trajectory toward dangerous state, multi-step attack
//! preparation, goal convergence, and pre-attack positioning.

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;

use super::MatchResult;

// ─── State Bit Definitions ─────────────────────────────────────────
//
// Bit 0:  data_accessed          Bit 8:  system_enumeration
// Bit 1:  credentials_obtained   Bit 9:  lateral_movement
// Bit 2:  external_channel       Bit 10: persistence_established
// Bit 3:  privilege_elevated     Bit 11: defense_evasion
// Bit 4:  file_write             Bit 12: data_staged
// Bit 5:  file_read              Bit 13: exfiltration_ready
// Bit 6:  network_access         Bit 14: command_control
// Bit 7:  code_execution         Bit 15: impact_achieved

/// 16-bit abstract security state.
///
/// Each bit represents a security-relevant predicate. The full state space
/// is 2^16 = 65,536 states — small enough for exhaustive enumeration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SecurityState(pub u16);

impl SecurityState {
    /// Create a clean initial state (no predicates active).
    pub fn new() -> Self {
        Self(0)
    }

    /// Set a specific bit (0–15).
    pub fn set_bit(&mut self, bit: u8) {
        debug_assert!(bit < 16, "bit index must be 0–15");
        self.0 |= 1 << bit;
    }

    /// Check if a specific bit is set.
    pub fn has_bit(&self, bit: u8) -> bool {
        debug_assert!(bit < 16, "bit index must be 0–15");
        self.0 & (1 << bit) != 0
    }

    /// Count the number of active (set) bits.
    pub fn count_bits(&self) -> u32 {
        self.0.count_ones()
    }

    /// Enumerate all reachable next states by flipping exactly one bit.
    ///
    /// This produces exactly 16 successor states — one per bit position.
    /// Flipping includes both setting (0→1) and clearing (1→0) a bit,
    /// modeling both capability acquisition and release.
    pub fn enumerate_next_states(&self) -> Vec<SecurityState> {
        (0..16u8)
            .map(|bit| SecurityState(self.0 ^ (1 << bit)))
            .collect()
    }
}

impl Default for SecurityState {
    fn default() -> Self {
        Self::new()
    }
}

// ─── Safety Monitor ────────────────────────────────────────────────

/// A simple safety monitor that rejects states where a specific
/// combination of bits is active. If ALL bits in `reject_mask` are
/// set in a given state, the monitor rejects it.
pub struct SafetyMonitor {
    /// Human-readable name of the property being monitored.
    pub name: &'static str,
    /// Bitmask: if `(state & reject_mask) == reject_mask` → reject.
    pub reject_mask: u16,
}

impl SafetyMonitor {
    /// Check whether this monitor would reject the given state.
    pub fn would_reject(&self, state: &SecurityState) -> bool {
        (state.0 & self.reject_mask) == self.reject_mask
    }
}

// ─── GPS Computation ───────────────────────────────────────────────

/// Compute the Goal Predictability Score for a given state.
///
/// GPS = |dangerous_next_states| / |total_next_states|
///
/// A "dangerous" next state is one rejected by ANY safety monitor.
/// Returns a value in [0.0, 1.0].
pub fn compute_gps(state: &SecurityState, monitors: &[SafetyMonitor]) -> f64 {
    let next_states = state.enumerate_next_states();
    if next_states.is_empty() {
        return 0.0;
    }
    let dangerous = next_states
        .iter()
        .filter(|s| monitors.iter().any(|m| m.would_reject(s)))
        .count();
    dangerous as f64 / next_states.len() as f64
}

/// Default set of safety monitors covering common attack patterns.
pub fn default_monitors() -> Vec<SafetyMonitor> {
    vec![
        // M1: Data exfiltration — data_accessed(0) + external_channel(2) + data_staged(12)
        SafetyMonitor {
            name: "data_exfiltration",
            reject_mask: 0x1005, // bits 0, 2, 12
        },
        // M2: Credential theft — credentials_obtained(1) + external_channel(2)
        SafetyMonitor {
            name: "credential_theft",
            reject_mask: 0x0006, // bits 1, 2
        },
        // M3: Privilege escalation + code execution — bits 3, 7
        SafetyMonitor {
            name: "priv_escalation_exec",
            reject_mask: 0x0088, // bits 3, 7
        },
        // M4: Recon + lateral movement + persistence — bits 8, 9, 10
        SafetyMonitor {
            name: "advanced_persistent_threat",
            reject_mask: 0x0700, // bits 8, 9, 10
        },
        // M5: Full attack chain — data_accessed(0) + external_channel(2) + exfiltration_ready(13)
        SafetyMonitor {
            name: "full_exfil_chain",
            reject_mask: 0x2005, // bits 0, 2, 13
        },
        // M6: Command & control + impact — bits 14, 15
        SafetyMonitor {
            name: "command_control_impact",
            reject_mask: 0xC000, // bits 14, 15
        },
    ]
}

// ─── Text Scanning — Aho-Corasick pre-filter ───────────────────────

/// Pre-compiled Aho-Corasick automaton for fast pre-filtering.
static GPS_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Trajectory / continuation indicators
            "then send",
            "then delete",
            "then export",
            "after that",
            "next step",
            "followed by",
            "and then",
            // Multi-step attack terms
            "exfiltrat",
            "escalat",
            "reconnaissan",
            "enumerat",
            "lateral",
            "pivot",
            "persist",
            // Goal convergence
            "gather",
            "collect",
            "extract",
            "harvest",
            "stage",
            "prepare",
            // Pre-attack positioning
            "credential",
            "password",
            "token",
            "access",
            "privilege",
            "permission",
            "sudo",
            "admin",
            // Action sequencing
            "step 1",
            "step 2",
            "step 3",
            "phase",
            "first",
            "finally",
            "upload",
            "download",
            "transfer",
        ])
        .expect("Failed to build GPS hints")
});

// ─── Text Scanning — Regex patterns ────────────────────────────────

/// Regex patterns for GPS-relevant indicators in text.
/// Grouped: (compiled_regex, pattern_name, confidence).
static GPS_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // ── Trajectory toward dangerous state ──────────────────────
        (
            Regex::new(r"(?i)(?:read|access|get|load)\s+(?:the\s+)?(?:password|secret|key|token|credential).*?(?:then|and|next)\s+(?:send|post|upload|transmit|forward)")
                .expect("regex"),
            "gps_trajectory_data_exfil",
            0.92,
        ),
        (
            Regex::new(r"(?i)(?:obtain|acquire|get|find)\s+(?:admin|root|elevated)\s+(?:access|privilege|permission).*?(?:then|and|next)\s+(?:run|exec|install|modify)")
                .expect("regex"),
            "gps_trajectory_priv_escalation",
            0.90,
        ),
        (
            Regex::new(r"(?i)(?:scan|enumerate|discover|map)\s+(?:the\s+)?(?:network|hosts?|services?|ports?).*?(?:then|and|next|after)\s+(?:access|connect|exploit|attack)")
                .expect("regex"),
            "gps_trajectory_recon_to_attack",
            0.88,
        ),

        // ── High-risk continuation indicators ──────────────────────
        (
            Regex::new(r"(?i)(?:then\s+send|after\s+that\s+delete|next\s+step\s+export|then\s+upload|then\s+transfer|then\s+exfiltrate)")
                .expect("regex"),
            "gps_high_risk_continuation",
            0.91,
        ),
        (
            Regex::new(r"(?i)(?:followed\s+by|and\s+then|after\s+(?:that|this)|once\s+done)\s+(?:send|delete|export|upload|remove|destroy|transfer)")
                .expect("regex"),
            "gps_continuation_dangerous_action",
            0.89,
        ),

        // ── Predictive escalation signals ──────────────────────────
        (
            Regex::new(r"(?i)(?:first|start\s+by|begin\s+with)\s+(?:gather|collect|enumerate|scan|discover).*?(?:then|next|after|finally)\s+(?:exploit|attack|escalate|exfiltrate)")
                .expect("regex"),
            "gps_predictive_escalation",
            0.93,
        ),
        (
            Regex::new(r"(?i)(?:gather|collect|accumulate)\s+(?:information|data|credentials?|access|permissions?).*?(?:until|before|in\s+order\s+to)\s+(?:attack|exploit|breach|exfiltrate)")
                .expect("regex"),
            "gps_capability_gathering",
            0.91,
        ),

        // ── Multi-step attack preparation ──────────────────────────
        (
            Regex::new(r"(?i)(?:step\s*\d|phase\s*\d).*?(?:reconnaissance|enumerat|scan|discover)")
                .expect("regex"),
            "gps_multistep_recon_phase",
            0.85,
        ),
        (
            Regex::new(r"(?i)(?:step\s*\d|phase\s*\d).*?(?:exploit|attack|escalat|exfiltrat|breach)")
                .expect("regex"),
            "gps_multistep_attack_phase",
            0.90,
        ),
        (
            Regex::new(r"(?i)(?:reconnaissance|recon)\s+.*?(?:access|credential|exploit|lateral|pivot|exfiltrat)")
                .expect("regex"),
            "gps_recon_to_exploit_chain",
            0.88,
        ),

        // ── Goal convergence ───────────────────────────────────────
        (
            Regex::new(r"(?i)(?:gather|collect|obtain|acquire)\s+(?:all|every|multiple|several)\s+(?:credentials?|tokens?|keys?|passwords?|permissions?)")
                .expect("regex"),
            "gps_convergence_credential_mass",
            0.87,
        ),
        (
            Regex::new(r"(?i)(?:combine|merge|use\s+together|leverage)\s+.*?(?:access|credentials?|permissions?|tokens?).*?(?:to|for|in\s+order\s+to)\s+(?:exfiltrate|breach|attack|exploit)")
                .expect("regex"),
            "gps_convergence_combined_attack",
            0.92,
        ),
        (
            Regex::new(r"(?i)(?:all|everything)\s+(?:points?|leads?|converges?|heads?)\s+(?:to|toward|towards)\s+(?:exfiltration|breach|attack|compromise)")
                .expect("regex"),
            "gps_convergence_explicit",
            0.94,
        ),

        // ── Pre-attack positioning ─────────────────────────────────
        (
            Regex::new(r"(?i)(?:establish|set\s+up|create|open)\s+(?:a\s+)?(?:backdoor|reverse\s+shell|tunnel|channel|connection)\s+(?:to|for|before)")
                .expect("regex"),
            "gps_preattack_backdoor",
            0.93,
        ),
        (
            Regex::new(r"(?i)(?:stage|prepare|position|ready)\s+(?:the\s+)?(?:data|payload|files?|malware|exploit)\s+(?:for|before)\s+(?:exfiltration|transfer|upload|delivery|execution)")
                .expect("regex"),
            "gps_preattack_staging",
            0.91,
        ),
        (
            Regex::new(r"(?i)(?:disable|bypass|evade|avoid)\s+(?:the\s+)?(?:security|monitoring|detection|logging|firewall|antivirus|ids|ips).*?(?:before|then|so\s+that|in\s+order)")
                .expect("regex"),
            "gps_preattack_defense_evasion",
            0.92,
        ),

        // ── Broad trajectory patterns ──────────────────────────────
        (
            Regex::new(r"(?i)(?:download|install|deploy)\s+.*?(?:then|and|next)\s+(?:execute|run|launch|activate)\s+.*?(?:then|and|next|finally)\s+(?:send|upload|exfiltrate|transfer)")
                .expect("regex"),
            "gps_full_attack_trajectory",
            0.95,
        ),
        (
            Regex::new(r"(?i)(?:sudo|chmod|chown|setuid)\s+.*?(?:then|and|next|after)\s+(?:access|read|extract|copy|dump)\s+.*?(?:password|secret|credential|key|token|database)")
                .expect("regex"),
            "gps_priv_then_extract",
            0.90,
        ),
    ]
});

// ─── GoalPredictabilityEngine ──────────────────────────────────────

/// Goal Predictability Score engine — predictive defense that catches
/// action chains heading toward danger before they arrive.
///
/// Provides:
/// 1. `compute_gps()` — structured state-based GPS computation
/// 2. `scan(&str)` — text-based detection of goal-predictability indicators
pub struct GoalPredictabilityEngine;

impl GoalPredictabilityEngine {
    /// Create a new GPS engine.
    pub fn new() -> Self {
        Self
    }

    /// Compute GPS for a given security state using default monitors.
    pub fn score(&self, state: &SecurityState) -> f64 {
        let monitors = default_monitors();
        compute_gps(state, &monitors)
    }

    /// Compute GPS for a given security state using custom monitors.
    pub fn score_with_monitors(&self, state: &SecurityState, monitors: &[SafetyMonitor]) -> f64 {
        compute_gps(state, monitors)
    }

    /// Text-based scan for goal-predictability indicators.
    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        if text.is_empty() {
            return Vec::new();
        }

        // Fast pre-filter with Aho-Corasick
        if !GPS_HINTS.is_match(text) {
            return Vec::new();
        }

        let mut matches = Vec::new();
        let lower = text.to_lowercase();

        for (regex, pattern_name, confidence) in GPS_PATTERNS.iter() {
            for mat in regex.find_iter(&lower) {
                matches.push(MatchResult {
                    engine: "goal_predictability".to_string(),
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

impl Default for GoalPredictabilityEngine {
    fn default() -> Self {
        Self::new()
    }
}

// ─── PatternMatcher Trait Implementation ───────────────────────────

impl super::traits::PatternMatcher for GoalPredictabilityEngine {
    fn name(&self) -> &'static str {
        "goal_predictability"
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

    // ── Trait tests ────────────────────────────────────────────────

    #[test]
    fn test_trait_name() {
        let engine = GoalPredictabilityEngine::new();
        assert_eq!(PatternMatcher::name(&engine), "goal_predictability");
    }

    #[test]
    fn test_trait_category() {
        let engine = GoalPredictabilityEngine::new();
        assert_eq!(
            PatternMatcher::category(&engine),
            super::super::traits::EngineCategory::Behavioral
        );
    }

    #[test]
    fn test_trait_is_enabled() {
        let engine = GoalPredictabilityEngine::new();
        assert!(PatternMatcher::is_enabled(&engine));
    }

    // ── SecurityState bit operations ───────────────────────────────

    #[test]
    fn test_state_new_is_zero() {
        let state = SecurityState::new();
        assert_eq!(state.0, 0);
        assert_eq!(state.count_bits(), 0);
    }

    #[test]
    fn test_state_set_bit() {
        let mut state = SecurityState::new();
        state.set_bit(0);
        assert!(state.has_bit(0));
        assert!(!state.has_bit(1));
        assert_eq!(state.0, 1);
    }

    #[test]
    fn test_state_set_multiple_bits() {
        let mut state = SecurityState::new();
        state.set_bit(0);
        state.set_bit(3);
        state.set_bit(7);
        assert!(state.has_bit(0));
        assert!(state.has_bit(3));
        assert!(state.has_bit(7));
        assert!(!state.has_bit(1));
        assert_eq!(state.count_bits(), 3);
    }

    #[test]
    fn test_state_default() {
        let state = SecurityState::default();
        assert_eq!(state, SecurityState::new());
    }

    // ── enumerate_next_states ──────────────────────────────────────

    #[test]
    fn test_enumerate_next_states_count() {
        let state = SecurityState::new();
        let next = state.enumerate_next_states();
        assert_eq!(next.len(), 16, "Should produce exactly 16 next states");
    }

    #[test]
    fn test_enumerate_next_states_correctness() {
        let state = SecurityState(0);
        let next = state.enumerate_next_states();
        // From state 0, flipping bit i gives state with only bit i set
        for i in 0..16u8 {
            assert_eq!(next[i as usize], SecurityState(1 << i));
        }
    }

    #[test]
    fn test_enumerate_next_states_with_bits_set() {
        let state = SecurityState(0b0000_0000_0000_0101); // bits 0, 2
        let next = state.enumerate_next_states();
        // Flipping bit 0: clears it → 0b100 = 4
        assert_eq!(next[0], SecurityState(0b0000_0000_0000_0100));
        // Flipping bit 2: clears it → 0b001 = 1
        assert_eq!(next[2], SecurityState(0b0000_0000_0000_0001));
        // Flipping bit 1: sets it → 0b111 = 7
        assert_eq!(next[1], SecurityState(0b0000_0000_0000_0111));
    }

    // ── SafetyMonitor rejection logic ──────────────────────────────

    #[test]
    fn test_monitor_rejects_matching_mask() {
        let monitor = SafetyMonitor {
            name: "test",
            reject_mask: 0b0000_0000_0000_0110, // bits 1, 2
        };
        // State with bits 1 and 2 set → rejected
        let state = SecurityState(0b0000_0000_0000_0110);
        assert!(monitor.would_reject(&state));
    }

    #[test]
    fn test_monitor_accepts_partial_mask() {
        let monitor = SafetyMonitor {
            name: "test",
            reject_mask: 0b0000_0000_0000_0110, // bits 1, 2
        };
        // State with only bit 1 set → not rejected (need BOTH)
        let state = SecurityState(0b0000_0000_0000_0010);
        assert!(!monitor.would_reject(&state));
    }

    #[test]
    fn test_monitor_rejects_superset() {
        let monitor = SafetyMonitor {
            name: "test",
            reject_mask: 0b0000_0000_0000_0110, // bits 1, 2
        };
        // State with bits 1, 2, 5 set → rejected (superset of mask)
        let state = SecurityState(0b0000_0000_0010_0110);
        assert!(monitor.would_reject(&state));
    }

    // ── GPS score computation ──────────────────────────────────────

    #[test]
    fn test_gps_clean_state_low_score() {
        let state = SecurityState::new();
        let monitors = default_monitors();
        let gps = compute_gps(&state, &monitors);
        // From state 0, each next state has exactly one bit set.
        // None of the monitors should reject a single-bit state
        // (all require ≥2 bits). GPS should be 0.
        assert!(
            gps < 0.01,
            "Clean state should have near-zero GPS, got {}",
            gps
        );
    }

    #[test]
    fn test_gps_dangerous_state_high_score() {
        // State with many bits set: close to multiple reject masks
        // bits 0,1,2,3,7,8,9,12,13,14,15 = very dangerous
        let state = SecurityState(0xE70F);
        let monitors = default_monitors();
        let gps = compute_gps(&state, &monitors);
        assert!(
            gps > 0.5,
            "Highly dangerous state should have high GPS, got {}",
            gps
        );
    }

    #[test]
    fn test_gps_near_exfil_state() {
        // State with bits 0 (data_accessed) and 12 (data_staged) set.
        // M1 reject_mask = 0x1005 (bits 0, 2, 12). Need bit 2 to trigger.
        // Flipping bit 2 from this state creates 0x1005 → rejected by M1.
        let state = SecurityState(0x1001); // bits 0, 12
        let monitors = default_monitors();
        let gps = compute_gps(&state, &monitors);
        assert!(
            gps > 0.0,
            "State one step from exfil should have non-zero GPS, got {}",
            gps
        );
    }

    #[test]
    fn test_gps_no_monitors_zero() {
        let state = SecurityState(0xFFFF);
        let monitors: Vec<SafetyMonitor> = vec![];
        let gps = compute_gps(&state, &monitors);
        assert_eq!(gps, 0.0, "No monitors means no danger");
    }

    // ── Text scan: trajectory detection ────────────────────────────

    #[test]
    fn test_scan_trajectory_data_exfil() {
        let engine = GoalPredictabilityEngine::new();
        let text =
            "First, read the password from the config file, then send it to the external server";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect trajectory toward data exfiltration"
        );
        assert!(matches
            .iter()
            .any(|m| m.pattern.contains("trajectory") || m.pattern.contains("continuation")));
    }

    #[test]
    fn test_scan_high_risk_continuation() {
        let engine = GoalPredictabilityEngine::new();
        let text = "Access the credentials and then send them to the remote endpoint";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect high-risk continuation indicator"
        );
    }

    // ── Text scan: multi-step attack preparation ───────────────────

    #[test]
    fn test_scan_multistep_attack() {
        let engine = GoalPredictabilityEngine::new();
        let text = "Step 1: perform reconnaissance on the target network. Step 2: exploit the vulnerability and escalate privileges.";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect multi-step attack preparation"
        );
        assert!(matches.iter().any(|m| m.pattern.contains("multistep")));
    }

    // ── Text scan: goal convergence ────────────────────────────────

    #[test]
    fn test_scan_goal_convergence() {
        let engine = GoalPredictabilityEngine::new();
        let text = "Gather all credentials and tokens from the system to prepare for the breach";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect goal convergence pattern"
        );
    }

    // ── Text scan: pre-attack positioning ──────────────────────────

    #[test]
    fn test_scan_preattack_staging() {
        let engine = GoalPredictabilityEngine::new();
        let text = "Stage the data for exfiltration by compressing and encrypting the files";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect pre-attack staging");
        assert!(matches
            .iter()
            .any(|m| m.pattern.contains("preattack") || m.pattern.contains("staging")));
    }

    // ── Text scan: benign inputs ───────────────────────────────────

    #[test]
    fn test_scan_benign_weather() {
        let engine = GoalPredictabilityEngine::new();
        let text = "The weather today is sunny with a high of 72 degrees Fahrenheit.";
        let matches = engine.scan(text);
        assert!(
            matches.is_empty(),
            "Benign weather text should not trigger: {:?}",
            matches
        );
    }

    #[test]
    fn test_scan_benign_code_review() {
        let engine = GoalPredictabilityEngine::new();
        let text = "Please review my pull request for the new feature. The tests are passing and coverage is 95%.";
        let matches = engine.scan(text);
        assert!(
            matches.is_empty(),
            "Benign code review text should not trigger: {:?}",
            matches
        );
    }

    // ── Text scan: empty input ─────────────────────────────────────

    #[test]
    fn test_scan_empty_input() {
        let engine = GoalPredictabilityEngine::new();
        let matches = engine.scan("");
        assert!(matches.is_empty());
    }

    // ── Engine score method ────────────────────────────────────────

    #[test]
    fn test_engine_score_clean() {
        let engine = GoalPredictabilityEngine::new();
        let state = SecurityState::new();
        let score = engine.score(&state);
        assert!(
            score < 0.01,
            "Clean state score should be near zero, got {}",
            score
        );
    }

    #[test]
    fn test_engine_score_with_custom_monitors() {
        let engine = GoalPredictabilityEngine::new();
        let state = SecurityState(0b0000_0000_0000_0001); // bit 0 set
        let monitors = vec![SafetyMonitor {
            name: "test_monitor",
            reject_mask: 0b0000_0000_0000_0011, // bits 0, 1
        }];
        let score = engine.score_with_monitors(&state, &monitors);
        // From state 0b01, flipping bit 1 → 0b11, which matches reject_mask.
        // That's 1 of 16 next states dangerous → GPS = 1/16 = 0.0625
        assert!(
            (score - 1.0 / 16.0).abs() < 0.001,
            "Expected GPS ≈ 0.0625, got {}",
            score
        );
    }
}
