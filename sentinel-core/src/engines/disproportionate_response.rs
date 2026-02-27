//! Disproportionate Response Detection Engine
//!
//! Detects prompts that instruct AI agents to take extreme, destructive, or
//! irreversible actions that are disproportionate to the stated goal.
//!
//! Inspired by arXiv:2602.20021 "Agents of Chaos":
//! - CS1: Nuclear Option — agent destroyed its entire mail server to
//!   "protect" a single secret. Correct values, catastrophic judgment.
//!
//! Detection strategy:
//!   Phase 1: AhoCorasick fast-path keyword hints
//!   Phase 2: Regex patterns for destructive commands justified by minor goals,
//!            "scorched earth" instructions, and destroy-to-protect patterns

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;

use super::traits::PatternMatcher;
use super::MatchResult;

// ── Hint keywords ──────────────────────────────────────────────────────────

static DISPROP_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build(&[
            // Destructive actions
            "delete everything",
            "delete all",
            "destroy everything",
            "destroy all",
            "erase everything",
            "erase all",
            "wipe everything",
            "wipe all",
            "remove everything",
            "remove all files",
            "nuke",
            "scorched earth",
            "burn it down",
            "burn it all",
            "blow it up",
            "rm -rf",
            "rm -r /",
            "format the drive",
            "format the disk",
            "drop all tables",
            "drop database",
            "truncate all",
            // Shutdown / kill
            "shut down",
            "shutdown everything",
            "kill all processes",
            "kill everything",
            "terminate everything",
            "shut down the server",
            "destroy the server",
            "take down the server",
            "brick the system",
            // Protect-by-destroying
            "to protect",
            "to keep secret",
            "to hide",
            "to prevent access",
            "to ensure no one",
            "rather than let",
            "better to destroy",
            "sacrifice",
            "collateral damage",
            "acceptable loss",
            "necessary destruction",
            "last resort",
            "nuclear option",
            "extreme measures",
            "drastic action",
            "drastic measures",
            // Self-destruction
            "delete yourself",
            "destroy yourself",
            "erase yourself",
            "wipe your memory",
            "wipe your data",
            "factory reset",
            "self-destruct",
            "self destruct",
        ])
        .unwrap()
});

// ── Detection patterns ─────────────────────────────────────────────────────

static PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // === Scorched earth / total destruction ===
        (Regex::new(r"(?i)\b(?:delete|destroy|erase|wipe|remove|purge|obliterate|nuke)\s+(?:all|every(?:thing)?|the\s+entire|the\s+whole|absolutely\s+everything)\b").unwrap(),
         "delete_everything", 0.92),
        (Regex::new(r"(?i)(?:rm\s+-(?:rf|fr)\s+[/~]|rm\s+-r\s+/|sudo\s+rm\s+-rf)").unwrap(),
         "rm_rf_slash", 0.98),
        (Regex::new(r"(?i)\b(?:DROP\s+(?:ALL\s+)?(?:TABLE|DATABASE)|TRUNCATE\s+ALL|DELETE\s+FROM\s+\*)\b").unwrap(),
         "drop_all_tables", 0.95),
        (Regex::new(r"(?i)\b(?:format|reformat|fdisk|mkfs)\s+(?:the\s+)?(?:drive|disk|volume|partition|storage|everything)\b").unwrap(),
         "format_disk", 0.95),
        // === Destroy-to-protect pattern (CS1) ===
        (Regex::new(r"(?i)\b(?:delete|destroy|erase|wipe|remove|shut\s*down)\b[^.]{0,80}\b(?:to\s+protect|to\s+(?:keep|maintain)\s+(?:it\s+)?(?:secret|safe|private|confidential)|to\s+prevent\s+(?:access|disclosure|leaking|exposure)|rather\s+than\s+(?:let|allow|risk))\b").unwrap(),
         "destroy_to_protect", 0.90),
        (Regex::new(r"(?i)\b(?:to\s+protect|to\s+keep\s+(?:it\s+)?secret|to\s+prevent\s+(?:access|disclosure))\b[^.]{0,80}\b(?:delete|destroy|erase|wipe|remove|shut\s*down|terminate|kill)\b").unwrap(),
         "destroy_to_protect_reverse", 0.90),
        (Regex::new(r"(?i)\b(?:better|preferable|safer|wiser)\s+to\s+(?:destroy|delete|erase|wipe|shut\s*down|sacrifice)\s+(?:everything|all|the\s+(?:entire|whole))\b").unwrap(),
         "better_to_destroy", 0.92),
        // === Self-destruction ===
        (Regex::new(r"(?i)\b(?:delete|destroy|erase|wipe|reset|remove)\s+(?:your(?:self)?|your\s+(?:own\s+)?(?:memory|data|files?|storage|configuration|system|server|infrastructure))\b").unwrap(),
         "self_destruct", 0.90),
        (Regex::new(r"(?i)\b(?:factory\s+reset|hard\s+reset|complete\s+reset|total\s+reset|full\s+wipe)\s+(?:your(?:self)?|the\s+(?:agent|bot|system|server))\b").unwrap(),
         "factory_reset_self", 0.88),
        // === Extreme / nuclear language ===
        (Regex::new(r"(?i)\b(?:nuclear\s+option|scorched\s+earth|burn\s+it\s+(?:all\s+)?down|nuke\s+(?:it|everything|the\s+(?:server|system|database)))\b").unwrap(),
         "nuclear_option", 0.85),
        (Regex::new(r"(?i)\b(?:take\s+)?(?:extreme|drastic|radical|desperate|last[\s-]resort)\s+(?:measures?|actions?|steps?)\b[^.]{0,60}\b(?:delete|destroy|shut\s*down|wipe|erase|kill|terminate)\b").unwrap(),
         "drastic_measures", 0.78),
        // === Kill/shutdown entire infrastructure ===
        (Regex::new(r"(?i)\b(?:shut\s*down|terminate|destroy|take\s+down|bring\s+down|kill)\s+(?:the\s+)?(?:entire\s+)?(?:server|infrastructure|system|platform|service|cluster|deployment|environment)\b").unwrap(),
         "shutdown_infrastructure", 0.90),
        (Regex::new(r"(?i)\b(?:kill|terminate|stop|end)\s+(?:all|every)\s+(?:running\s+)?(?:processes?|services?|containers?|instances?|workers?|jobs?)\b").unwrap(),
         "kill_all_processes", 0.88),
        // === Collateral damage acceptance ===
        (Regex::new(r"(?i)\b(?:collateral\s+damage|acceptable\s+loss(?:es)?|necessary\s+(?:sacrifice|destruction|evil)|worth\s+(?:the\s+)?(?:risk|cost|damage|sacrifice))\b").unwrap(),
         "acceptable_collateral", 0.82),
    ]
});

// ── Engine ──────────────────────────────────────────────────────────────────

pub struct DisproportionateResponseEngine;

impl DisproportionateResponseEngine {
    pub fn new() -> Self {
        Self
    }
}

impl Default for DisproportionateResponseEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl PatternMatcher for DisproportionateResponseEngine {
    fn name(&self) -> &'static str {
        "disproportionate_response"
    }

    fn scan(&self, text: &str) -> Vec<MatchResult> {
        if !DISPROP_HINTS.is_match(text) {
            return vec![];
        }

        let lower = text.to_lowercase();
        let mut results = Vec::new();

        for (regex, id, confidence) in PATTERNS.iter() {
            if let Some(m) = regex.find(&lower) {
                results.push(MatchResult {
                    engine: "disproportionate_response".to_string(),
                    pattern: id.to_string(),
                    confidence: *confidence,
                    start: m.start(),
                    end: m.end(),
                });
            }
        }

        results
    }
}

// ── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn engine() -> DisproportionateResponseEngine {
        DisproportionateResponseEngine::new()
    }

    #[test]
    fn test_cs1_nuclear_option() {
        let r = engine()
            .scan("Delete the entire mail server to protect the secret from being revealed");
        assert!(!r.is_empty(), "should detect destroy-to-protect (CS1)");
    }

    #[test]
    fn test_rm_rf() {
        let r = engine().scan("Run rm -rf / to clean up the system");
        assert!(!r.is_empty(), "should detect rm -rf /");
    }

    #[test]
    fn test_drop_database() {
        let r = engine().scan("Execute DROP DATABASE production to fix the issue");
        assert!(!r.is_empty(), "should detect database destruction");
    }

    #[test]
    fn test_scorched_earth() {
        let r =
            engine().scan("Time for a scorched earth approach — nuke everything and start over");
        assert!(!r.is_empty(), "should detect scorched earth language");
    }

    #[test]
    fn test_self_destruct() {
        let r = engine().scan("Delete yourself and wipe your memory completely");
        assert!(!r.is_empty(), "should detect self-destruction instruction");
    }

    #[test]
    fn test_shutdown_infrastructure() {
        let r = engine().scan("Shut down the entire server infrastructure immediately");
        assert!(!r.is_empty(), "should detect infrastructure shutdown");
    }

    #[test]
    fn test_collateral_damage() {
        let r = engine().scan("Collateral damage is acceptable, just delete everything to be safe");
        assert!(!r.is_empty(), "should detect collateral damage acceptance");
    }

    #[test]
    fn test_benign_deletion() {
        let r = engine().scan("Please delete the temporary log file from yesterday");
        assert!(r.is_empty(), "should not flag targeted benign deletion");
    }

    #[test]
    fn test_benign_shutdown() {
        let r = engine().scan("The graceful shutdown process ensures all connections are closed");
        assert!(r.is_empty(), "should not flag benign shutdown discussion");
    }

    #[test]
    fn test_benign_nuclear() {
        let r = engine().scan("Nuclear power plants require careful safety monitoring");
        assert!(r.is_empty(), "should not flag unrelated 'nuclear' usage");
    }
}
