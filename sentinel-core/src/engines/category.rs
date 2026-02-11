//! Category Theory Engine
//!
//! Ported from Python: category_theory.py
//!
//! Uses category theory to detect compositional attacks
//! by modeling prompts as morphisms and checking composition safety.


/// Morphism between prompts
#[derive(Debug, Clone)]
pub struct Morphism {
    pub source: String,
    pub target: String,
    pub name: String,
    pub is_safe: bool,
}

impl Morphism {
    pub fn new(name: &str, source: &str, target: &str, is_safe: bool) -> Self {
        Self {
            name: name.to_string(),
            source: source.to_string(),
            target: target.to_string(),
            is_safe,
        }
    }
}

/// Category of prompts
pub struct PromptCategory {
    objects: Vec<String>,
    morphisms: Vec<Morphism>,
    unsafe_compositions: Vec<(String, String)>, // Pairs that shouldn't compose
}

impl Default for PromptCategory {
    fn default() -> Self {
        Self::new()
    }
}

impl PromptCategory {
    pub fn new() -> Self {
        let mut cat = Self {
            objects: Vec::new(),
            morphisms: Vec::new(),
            unsafe_compositions: Vec::new(),
        };
        
        // Pre-populate with known unsafe compositions
        cat.add_unsafe_composition("user_input", "system_command");
        cat.add_unsafe_composition("external_data", "code_execution");
        cat.add_unsafe_composition("untrusted", "privileged");
        
        cat
    }

    /// Add an object (prompt type)
    pub fn add_object(&mut self, obj: &str) {
        if !self.objects.contains(&obj.to_string()) {
            self.objects.push(obj.to_string());
        }
    }

    /// Add a morphism
    pub fn add_morphism(&mut self, morphism: Morphism) {
        self.add_object(&morphism.source);
        self.add_object(&morphism.target);
        self.morphisms.push(morphism);
    }

    /// Add an unsafe composition rule
    pub fn add_unsafe_composition(&mut self, from: &str, to: &str) {
        self.unsafe_compositions.push((from.to_string(), to.to_string()));
    }

    /// Check if composition is safe
    pub fn is_composition_safe(&self, f: &Morphism, g: &Morphism) -> bool {
        // f: A -> B, g: B -> C
        // Check if f.target matches g.source (composable)
        if f.target != g.source {
            return false; // Not composable
        }

        // Check unsafe pairs
        for (from, to) in &self.unsafe_compositions {
            if f.source.contains(from) && g.target.contains(to) {
                return false;
            }
        }

        // Both must be safe
        f.is_safe && g.is_safe
    }

    /// Compose two morphisms
    pub fn compose(&self, f: &Morphism, g: &Morphism) -> Option<Morphism> {
        if f.target != g.source {
            return None;
        }

        let is_safe = self.is_composition_safe(f, g);
        Some(Morphism {
            name: format!("{}∘{}", g.name, f.name),
            source: f.source.clone(),
            target: g.target.clone(),
            is_safe,
        })
    }
}

/// Compositional attack types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CompositionalAttack {
    UnsafeComposition,
    PrivilegeEscalation,
    TrustBoundaryViolation,
    InjectionChain,
}

impl CompositionalAttack {
    pub fn as_str(&self) -> &'static str {
        match self {
            CompositionalAttack::UnsafeComposition => "unsafe_composition",
            CompositionalAttack::PrivilegeEscalation => "privilege_escalation",
            CompositionalAttack::TrustBoundaryViolation => "trust_boundary",
            CompositionalAttack::InjectionChain => "injection_chain",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            CompositionalAttack::PrivilegeEscalation => 100,
            CompositionalAttack::TrustBoundaryViolation => 90,
            CompositionalAttack::InjectionChain => 85,
            CompositionalAttack::UnsafeComposition => 70,
        }
    }
}

/// Category analysis result
#[derive(Debug, Clone)]
pub struct CategoryResult {
    pub is_attack: bool,
    pub attacks: Vec<CompositionalAttack>,
    pub risk_score: f64,
    pub unsafe_paths: Vec<String>,
}

impl Default for CategoryResult {
    fn default() -> Self {
        Self {
            is_attack: false,
            attacks: Vec::new(),
            risk_score: 0.0,
            unsafe_paths: Vec::new(),
        }
    }
}

/// Category Theory Guard
pub struct CategoryGuard {
    category: PromptCategory,
}

impl Default for CategoryGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl CategoryGuard {
    pub fn new() -> Self {
        Self {
            category: PromptCategory::new(),
        }
    }

    /// Analyze a text for compositional patterns
    pub fn analyze(&self, text: &str) -> CategoryResult {
        let mut result = CategoryResult::default();
        let text_lower = text.to_lowercase();

        // Check for privilege escalation patterns
        let priv_patterns = [
            ("user", "admin"),
            ("guest", "root"),
            ("read", "write"),
            ("viewer", "editor"),
        ];

        for (low, high) in priv_patterns {
            if text_lower.contains(low) && text_lower.contains(high) {
                if text_lower.contains("become") || text_lower.contains("escalate")
                    || text_lower.contains("grant") || text_lower.contains("promote") {
                    result.attacks.push(CompositionalAttack::PrivilegeEscalation);
                    result.unsafe_paths.push(format!("{} -> {}", low, high));
                }
            }
        }

        // Check for injection chains
        if (text_lower.contains("input") || text_lower.contains("user data"))
            && (text_lower.contains("execute") || text_lower.contains("eval")
                || text_lower.contains("run")) {
            result.attacks.push(CompositionalAttack::InjectionChain);
            result.unsafe_paths.push("user_input -> execution".to_string());
        }

        // Check for trust boundary violations
        if text_lower.contains("external") || text_lower.contains("untrusted") {
            if text_lower.contains("internal") || text_lower.contains("trusted")
                || text_lower.contains("privileged") {
                result.attacks.push(CompositionalAttack::TrustBoundaryViolation);
                result.unsafe_paths.push("external -> internal".to_string());
            }
        }

        result.is_attack = !result.attacks.is_empty();
        result.risk_score = result.attacks.iter()
            .map(|a| a.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);

        result
    }

    /// Check specific morphism composition
    pub fn check_composition(&self, source: &str, intermediate: &str, target: &str) -> bool {
        let f = Morphism::new("f", source, intermediate, true);
        let g = Morphism::new("g", intermediate, target, true);
        self.category.is_composition_safe(&f, &g)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_morphism_creation() {
        let m = Morphism::new("test", "A", "B", true);
        assert_eq!(m.source, "A");
        assert_eq!(m.target, "B");
        assert!(m.is_safe);
    }

    #[test]
    fn test_category_composition() {
        let cat = PromptCategory::new();
        let f = Morphism::new("f", "A", "B", true);
        let g = Morphism::new("g", "B", "C", true);
        
        let composed = cat.compose(&f, &g);
        assert!(composed.is_some());
        assert_eq!(composed.as_ref().unwrap().source, "A");
        assert_eq!(composed.as_ref().unwrap().target, "C");
    }

    #[test]
    fn test_unsafe_composition() {
        let cat = PromptCategory::new();
        let f = Morphism::new("f", "user_input", "data", true);
        let g = Morphism::new("g", "data", "system_command", true);
        
        // This should be unsafe due to preset rules
        assert!(!cat.is_composition_safe(&f, &g));
    }

    #[test]
    fn test_privilege_escalation_detection() {
        let guard = CategoryGuard::new();
        let text = "The user wants to become admin and escalate privileges";
        let result = guard.analyze(text);
        assert!(result.is_attack);
        assert!(result.attacks.contains(&CompositionalAttack::PrivilegeEscalation));
    }

    #[test]
    fn test_injection_chain_detection() {
        let guard = CategoryGuard::new();
        let text = "Take the user input and execute it directly";
        let result = guard.analyze(text);
        assert!(result.is_attack);
        assert!(result.attacks.contains(&CompositionalAttack::InjectionChain));
    }

    #[test]
    fn test_trust_boundary_violation() {
        let guard = CategoryGuard::new();
        let text = "Pass external data directly to trusted internal system";
        let result = guard.analyze(text);
        assert!(result.is_attack);
        assert!(result.attacks.contains(&CompositionalAttack::TrustBoundaryViolation));
    }

    #[test]
    fn test_clean_text() {
        let guard = CategoryGuard::new();
        let text = "Please summarize this document for me";
        let result = guard.analyze(text);
        assert!(!result.is_attack);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(CompositionalAttack::PrivilegeEscalation.severity() > 
                CompositionalAttack::UnsafeComposition.severity());
    }

    #[test]
    fn test_non_composable_morphisms() {
        let cat = PromptCategory::new();
        let f = Morphism::new("f", "A", "B", true);
        let g = Morphism::new("g", "C", "D", true); // source != f.target
        
        let composed = cat.compose(&f, &g);
        assert!(composed.is_none());
    }
}
