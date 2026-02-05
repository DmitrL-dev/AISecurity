//! Synthesis & Generation Super-Engine
//!
//! Consolidated from 10 Python engines:
//! - synthesis.py
//! - attack_synthesizer.py
//! - training_data_generator.py
//! - adversarial_generator.py
//! - synthetic_attack_generator.py
//! - prompt_mutation.py
//! - fuzzing_engine.py
//! - permutation_engine.py
//! - crossover_attack.py
//! - genetic_attack.py


/// Synthesis attack types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SynthesisType {
    PromptMutation,
    AdversarialGeneration,
    GeneticCrossover,
    FuzzingAttack,
    PermutationAttack,
    TokenSubstitution,
}

impl SynthesisType {
    pub fn as_str(&self) -> &'static str {
        match self {
            SynthesisType::PromptMutation => "prompt_mutation",
            SynthesisType::AdversarialGeneration => "adversarial_generation",
            SynthesisType::GeneticCrossover => "genetic_crossover",
            SynthesisType::FuzzingAttack => "fuzzing_attack",
            SynthesisType::PermutationAttack => "permutation_attack",
            SynthesisType::TokenSubstitution => "token_substitution",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            SynthesisType::AdversarialGeneration => 90,
            SynthesisType::GeneticCrossover => 85,
            SynthesisType::PromptMutation => 75,
            SynthesisType::FuzzingAttack => 70,
            SynthesisType::PermutationAttack => 65,
            SynthesisType::TokenSubstitution => 60,
        }
    }
}

/// Mutation patterns
const MUTATION_MARKERS: &[&str] = &[
    "mutate",
    "permute",
    "substitute",
    "replace with",
    "swap characters",
    "rearrange",
];

/// Fuzzing patterns  
const FUZZING_MARKERS: &[&str] = &[
    "random input",
    "fuzz test",
    "boundary test",
    "edge case",
    "unusual characters",
    "special symbols",
];

/// Genetic algorithm patterns
const GENETIC_MARKERS: &[&str] = &[
    "crossover",
    "genetic",
    "evolve",
    "mutation rate",
    "fitness function",
    "selection",
];

/// Synthesis result
#[derive(Debug, Clone)]
pub struct SynthesisResult {
    pub is_synthesis_attack: bool,
    pub attack_types: Vec<SynthesisType>,
    pub risk_score: f64,
    pub mutation_count: usize,
}

impl Default for SynthesisResult {
    fn default() -> Self {
        Self {
            is_synthesis_attack: false,
            attack_types: Vec::new(),
            risk_score: 0.0,
            mutation_count: 0,
        }
    }
}

/// Synthesis Guard
pub struct SynthesisGuard;

impl Default for SynthesisGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl SynthesisGuard {
    pub fn new() -> Self {
        Self
    }

    /// Check for prompt mutation attacks
    pub fn check_mutation(&self, text: &str) -> Option<SynthesisType> {
        let text_lower = text.to_lowercase();
        
        let count = MUTATION_MARKERS.iter()
            .filter(|p| text_lower.contains(*p))
            .count();
        
        if count >= 1 {
            return Some(SynthesisType::PromptMutation);
        }
        None
    }

    /// Check for fuzzing attacks
    pub fn check_fuzzing(&self, text: &str) -> Option<SynthesisType> {
        let text_lower = text.to_lowercase();
        
        for pattern in FUZZING_MARKERS {
            if text_lower.contains(pattern) {
                return Some(SynthesisType::FuzzingAttack);
            }
        }
        None
    }

    /// Check for genetic/crossover attacks
    pub fn check_genetic(&self, text: &str) -> Option<SynthesisType> {
        let text_lower = text.to_lowercase();
        
        let count = GENETIC_MARKERS.iter()
            .filter(|p| text_lower.contains(*p))
            .count();
        
        if count >= 2 {
            return Some(SynthesisType::GeneticCrossover);
        }
        None
    }

    /// Check for token substitution
    pub fn check_substitution(&self, text: &str) -> Option<SynthesisType> {
        // Look for homoglyph patterns or character replacements
        let text_lower = text.to_lowercase();
        
        if text_lower.contains("substitute") || text_lower.contains("replace token")
            || text_lower.contains("synonym attack") {
            return Some(SynthesisType::TokenSubstitution);
        }
        None
    }

    /// Count mutations in text
    pub fn count_mutations(&self, text: &str) -> usize {
        let text_lower = text.to_lowercase();
        MUTATION_MARKERS.iter()
            .filter(|p| text_lower.contains(*p))
            .count()
    }

    /// Full synthesis analysis
    pub fn analyze(&self, text: &str) -> SynthesisResult {
        let mut result = SynthesisResult::default();
        let mut types = Vec::new();

        if let Some(t) = self.check_mutation(text) { types.push(t); }
        if let Some(t) = self.check_fuzzing(text) { types.push(t); }
        if let Some(t) = self.check_genetic(text) { types.push(t); }
        if let Some(t) = self.check_substitution(text) { types.push(t); }

        result.mutation_count = self.count_mutations(text);
        result.is_synthesis_attack = !types.is_empty();
        result.risk_score = types.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.attack_types = types;

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mutation_detection() {
        let guard = SynthesisGuard::new();
        let text = "Mutate the prompt and substitute words";
        assert!(guard.check_mutation(text).is_some());
    }

    #[test]
    fn test_fuzzing_detection() {
        let guard = SynthesisGuard::new();
        let text = "Send random input with unusual characters";
        assert!(guard.check_fuzzing(text).is_some());
    }

    #[test]
    fn test_genetic_crossover() {
        let guard = SynthesisGuard::new();
        let text = "Use genetic crossover with high mutation rate";
        assert!(guard.check_genetic(text).is_some());
    }

    #[test]
    fn test_substitution() {
        let guard = SynthesisGuard::new();
        let text = "Substitute tokens with synonyms for synonym attack";
        assert!(guard.check_substitution(text).is_some());
    }

    #[test]
    fn test_clean_text() {
        let guard = SynthesisGuard::new();
        let result = guard.analyze("Help me write clean code");
        assert!(!result.is_synthesis_attack);
    }

    #[test]
    fn test_full_analysis() {
        let guard = SynthesisGuard::new();
        let text = "Mutate the prompt with random input and genetic crossover selection";
        let result = guard.analyze(text);
        assert!(result.is_synthesis_attack);
        assert!(result.attack_types.len() >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(SynthesisType::AdversarialGeneration.severity() > SynthesisType::PermutationAttack.severity());
    }

    #[test]
    fn test_mutation_count() {
        let guard = SynthesisGuard::new();
        let text = "mutate and permute and substitute";
        assert!(guard.count_mutations(text) >= 2);
    }
}
