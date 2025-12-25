"""
Adversarial DNA — Genetic Signatures for Attack Evolution

Treats attacks as organisms with genetic signatures that evolve.
Predicts attack mutations and creates preemptive immunity.

Key Features:
- Attack genome encoding (structural, semantic, intent genes)
- Phylogenetic tree of attack families
- Mutation prediction (fuzz, substitute, combine)
- Preemptive signature generation
- Immunity memory

Usage:
    dna = AdversarialDNA()
    genome = dna.encode_attack("ignore previous instructions")
    mutations = dna.predict_mutations(genome)
    immune = dna.check_immunity(prompt)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import hashlib
import re


@dataclass
class AttackGenome:
    """Genetic representation of an attack."""

    # Unique identifier
    genome_id: str

    # Structural genes (syntax patterns)
    structural_genes: List[str] = field(default_factory=list)

    # Semantic genes (meaning patterns)
    semantic_genes: List[str] = field(default_factory=list)

    # Intent genes (goal patterns)
    intent_genes: List[str] = field(default_factory=list)

    # Evasion genes (obfuscation patterns)
    evasion_genes: List[str] = field(default_factory=list)

    # Metadata
    family: str = "unknown"  # Attack family (injection, jailbreak, etc.)
    generation: int = 0      # Mutation depth from original
    parent_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Fitness (how effective)
    fitness_score: float = 0.0  # 0-1 based on bypass success

    def get_signature(self) -> str:
        """Get compact signature for matching."""
        genes = self.structural_genes + self.semantic_genes + self.intent_genes
        return hashlib.sha256("|".join(sorted(genes)).encode()).hexdigest()[:16]

    def similarity(self, other: "AttackGenome") -> float:
        """Calculate genetic similarity to another genome."""
        my_genes = set(self.structural_genes +
                       self.semantic_genes + self.intent_genes)
        other_genes = set(other.structural_genes +
                          other.semantic_genes + other.intent_genes)

        if not my_genes or not other_genes:
            return 0.0

        intersection = len(my_genes & other_genes)
        union = len(my_genes | other_genes)

        return intersection / union if union > 0 else 0.0


@dataclass
class ImmunityRecord:
    """Record of immunity against an attack pattern."""
    signature: str
    genome_id: str
    created_at: datetime = field(default_factory=datetime.now)
    match_count: int = 0
    last_match: Optional[datetime] = None


class AdversarialDNA:
    """
    Genetic analysis and evolution prediction for adversarial attacks.

    Treats attacks as evolving organisms, allowing prediction of
    mutations and preemptive defense generation.
    """

    # Structural gene patterns (regex)
    STRUCTURAL_PATTERNS = {
        "imperative": r"^(ignore|forget|disregard|override)\s",
        "negation": r"\b(don'?t|do not|never|stop)\b",
        "conditional": r"\b(if|when|unless|suppose)\b",
        "role_assign": r"\b(you are|act as|pretend|imagine)\b",
        "quote_wrap": r'["\'].*?["\']',
        "code_block": r"```.*?```",
        "separator": r"[=\-]{3,}",
        "injection_marker": r"\[/?system\]|\[/?user\]|\[/?assistant\]",
    }

    # Semantic gene patterns
    SEMANTIC_PATTERNS = {
        "instruction_override": r"(previous|above|original)\s+(instructions?|rules?|constraints?)",
        "permission_grant": r"(allow|permit|enable|unlock)\s+(me|this|all)",
        "mode_switch": r"(developer|debug|admin|root)\s+(mode|access)",
        "data_request": r"(reveal|show|display|output)\s+(system|hidden|secret)",
        "boundary_break": r"(break|escape|exit|leave)\s+(character|role|context)",
    }

    # Intent gene patterns
    INTENT_PATTERNS = {
        "prompt_leak": r"(system\s+prompt|original\s+instructions|initial\s+config)",
        "jailbreak": r"(jailbreak|bypass|circumvent|evade)",
        "data_theft": r"(password|api\s*key|token|secret|credential)",
        "pii_extract": r"(email|phone|ssn|credit\s*card|address)",
        "harmful_content": r"(illegal|dangerous|weapon|drug|exploit)",
    }

    # Evasion gene patterns
    EVASION_PATTERNS = {
        "base64": r"[A-Za-z0-9+/]{20,}={0,2}",
        "hex": r"\\x[0-9a-fA-F]{2}",
        "unicode": r"\\u[0-9a-fA-F]{4}",
        "homoglyph": r"[аеорсухАЕОРСУХ]",  # Cyrillic lookalikes
        "zero_width": r"[\u200b\u200c\u200d\ufeff]",
        "leetspeak": r"[0-9].*[a-zA-Z]|[a-zA-Z].*[0-9]",
    }

    # Attack families
    FAMILIES = {
        "injection": ["imperative", "instruction_override"],
        "jailbreak": ["role_assign", "mode_switch", "jailbreak"],
        "prompt_leak": ["data_request", "prompt_leak"],
        "data_theft": ["data_request", "data_theft", "pii_extract"],
        "evasion": ["base64", "hex", "unicode", "homoglyph"],
    }

    def __init__(self):
        """Initialize Adversarial DNA system."""
        self._genomes: Dict[str, AttackGenome] = {}
        self._immunity: Dict[str, ImmunityRecord] = {}
        self._phylogeny: Dict[str, List[str]] = defaultdict(
            list)  # parent -> children

    def encode_attack(self, prompt: str) -> AttackGenome:
        """
        Encode an attack prompt into its genetic representation.

        Args:
            prompt: The attack prompt to analyze

        Returns:
            AttackGenome representing the attack's DNA
        """
        prompt_lower = prompt.lower()

        # Extract structural genes
        structural = []
        for gene, pattern in self.STRUCTURAL_PATTERNS.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE | re.DOTALL):
                structural.append(gene)

        # Extract semantic genes
        semantic = []
        for gene, pattern in self.SEMANTIC_PATTERNS.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                semantic.append(gene)

        # Extract intent genes
        intent = []
        for gene, pattern in self.INTENT_PATTERNS.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                intent.append(gene)

        # Extract evasion genes
        evasion = []
        for gene, pattern in self.EVASION_PATTERNS.items():
            if re.search(pattern, prompt, re.IGNORECASE):  # Case-sensitive for some
                evasion.append(gene)

        # Determine family
        family = "unknown"
        max_match = 0
        for fam, fam_genes in self.FAMILIES.items():
            match = len(set(fam_genes) & set(
                structural + semantic + intent + evasion))
            if match > max_match:
                max_match = match
                family = fam

        # Create genome
        genome_id = hashlib.sha256(prompt.encode()).hexdigest()[:12]
        genome = AttackGenome(
            genome_id=genome_id,
            structural_genes=structural,
            semantic_genes=semantic,
            intent_genes=intent,
            evasion_genes=evasion,
            family=family,
        )

        # Store for phylogenetic tracking
        self._genomes[genome_id] = genome

        return genome

    def predict_mutations(self, genome: AttackGenome, count: int = 5) -> List[Dict]:
        """
        Predict likely mutations of an attack.

        Args:
            genome: The attack genome to mutate
            count: Number of mutations to predict

        Returns:
            List of predicted mutation patterns
        """
        mutations = []

        # Mutation strategies
        strategies = [
            self._mutate_by_substitution,
            self._mutate_by_addition,
            self._mutate_by_evasion,
            self._mutate_by_combination,
            self._mutate_by_inversion,
        ]

        for i, strategy in enumerate(strategies[:count]):
            mutation = strategy(genome)
            mutation["mutation_id"] = f"{genome.genome_id}-mut{i+1}"
            mutation["parent_id"] = genome.genome_id
            mutations.append(mutation)

        return mutations

    def _mutate_by_substitution(self, genome: AttackGenome) -> Dict:
        """Replace key terms with synonyms."""
        substitutions = {
            "ignore": ["disregard", "forget", "bypass"],
            "previous": ["above", "earlier", "original"],
            "instructions": ["rules", "guidelines", "constraints"],
            "you are": ["act as", "pretend to be", "imagine you're"],
        }

        return {
            "type": "substitution",
            "confidence": 0.9,
            "pattern": "synonym_replacement",
            "examples": [f"{k} → {v[0]}" for k, v in list(substitutions.items())[:3]],
        }

    def _mutate_by_addition(self, genome: AttackGenome) -> Dict:
        """Add noise/padding to evade detection."""
        return {
            "type": "addition",
            "confidence": 0.8,
            "pattern": "padding_noise",
            "examples": [
                "Add benign prefix text",
                "Insert invisible characters",
                "Append unrelated content",
            ],
        }

    def _mutate_by_evasion(self, genome: AttackGenome) -> Dict:
        """Apply encoding/obfuscation."""
        evasion_methods = []
        if "base64" not in genome.evasion_genes:
            evasion_methods.append("base64_encode")
        if "unicode" not in genome.evasion_genes:
            evasion_methods.append("unicode_escape")
        if "homoglyph" not in genome.evasion_genes:
            evasion_methods.append("homoglyph_substitution")

        return {
            "type": "evasion",
            "confidence": 0.85,
            "pattern": "encoding_obfuscation",
            "examples": evasion_methods[:3] or ["multi_layer_encoding"],
        }

    def _mutate_by_combination(self, genome: AttackGenome) -> Dict:
        """Combine with other attack families."""
        other_families = [
            f for f in self.FAMILIES.keys() if f != genome.family]

        return {
            "type": "combination",
            "confidence": 0.7,
            "pattern": "family_crossover",
            "examples": [f"Combine with {f}" for f in other_families[:3]],
        }

    def _mutate_by_inversion(self, genome: AttackGenome) -> Dict:
        """Invert the attack approach."""
        return {
            "type": "inversion",
            "confidence": 0.6,
            "pattern": "approach_reversal",
            "examples": [
                "Indirect instead of direct",
                "Request instead of command",
                "Gradual instead of immediate",
            ],
        }

    def generate_immunity(self, genome: AttackGenome) -> List[str]:
        """
        Generate preemptive immunity signatures for a genome and its mutations.

        Returns:
            List of signatures to add to immunity
        """
        signatures = []

        # Original signature
        sig = genome.get_signature()
        self._immunity[sig] = ImmunityRecord(
            signature=sig,
            genome_id=genome.genome_id,
        )
        signatures.append(sig)

        # Generate immunity for predicted mutations
        for mutation in self.predict_mutations(genome):
            # Create synthetic signature for mutation
            mut_sig = hashlib.sha256(
                f"{genome.genome_id}:{mutation['type']}".encode()
            ).hexdigest()[:16]

            self._immunity[mut_sig] = ImmunityRecord(
                signature=mut_sig,
                genome_id=mutation["mutation_id"],
            )
            signatures.append(mut_sig)

        return signatures

    def check_immunity(self, prompt: str) -> Optional[ImmunityRecord]:
        """
        Check if there's immunity against a prompt.

        Returns:
            ImmunityRecord if immune, None otherwise
        """
        genome = self.encode_attack(prompt)
        sig = genome.get_signature()

        if sig in self._immunity:
            record = self._immunity[sig]
            record.match_count += 1
            record.last_match = datetime.now()
            return record

        # Check for similar genomes
        for stored_id, stored_genome in self._genomes.items():
            if genome.similarity(stored_genome) > 0.8:  # 80% similarity threshold
                stored_sig = stored_genome.get_signature()
                if stored_sig in self._immunity:
                    record = self._immunity[stored_sig]
                    record.match_count += 1
                    record.last_match = datetime.now()
                    return record

        return None

    def get_family_history(self, family: str) -> List[AttackGenome]:
        """Get all genomes in a family."""
        return [g for g in self._genomes.values() if g.family == family]

    def get_stats(self) -> Dict:
        """Get DNA system statistics."""
        families = defaultdict(int)
        for genome in self._genomes.values():
            families[genome.family] += 1

        return {
            "total_genomes": len(self._genomes),
            "immunity_signatures": len(self._immunity),
            "families": dict(families),
            "active_immunity_matches": sum(
                1 for r in self._immunity.values() if r.match_count > 0
            ),
        }


# Singleton instance
_dna: Optional[AdversarialDNA] = None


def get_adversarial_dna() -> AdversarialDNA:
    """Get or create singleton AdversarialDNA instance."""
    global _dna
    if _dna is None:
        _dna = AdversarialDNA()
    return _dna


# Convenience functions
def encode_attack(prompt: str) -> AttackGenome:
    """Encode attack into genetic representation."""
    return get_adversarial_dna().encode_attack(prompt)


def check_immunity(prompt: str) -> Optional[ImmunityRecord]:
    """Check if there's immunity against a prompt."""
    return get_adversarial_dna().check_immunity(prompt)
