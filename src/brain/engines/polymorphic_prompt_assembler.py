"""
Polymorphic Prompt Assembling (PPA) Engine

Based on December 2025 R&D findings:
- IEEE/arXiv 2025 research on PPA defense
- Dynamic system prompt structure randomization
- Disrupts adaptive prompt injection attacks

Defense mechanism:
1. Dynamically vary system prompt structure
2. Randomize instruction/input combination
3. Prevent attackers from predicting prompt layout
4. Maintain functionality while enhancing security

Implementation:
- Template randomization
- Delimiter variation
- Instruction ordering shuffling
- Placeholder injection for confusion
"""

import re
import random
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class PPAStrength(Enum):
    """Strength levels for PPA protection."""
    MAXIMUM = "maximum"      # Full randomization
    HIGH = "high"            # Strong randomization
    MEDIUM = "medium"        # Moderate randomization
    LOW = "low"              # Light randomization
    DISABLED = "disabled"    # No randomization


@dataclass
class PPAConfig:
    """Configuration for PPA engine."""
    strength: PPAStrength = PPAStrength.HIGH
    delimiter_pool_size: int = 10
    instruction_shuffle: bool = True
    add_decoy_sections: bool = True
    vary_whitespace: bool = True
    seed: Optional[int] = None


@dataclass
class AssembledPrompt:
    """Result of prompt assembly."""
    system_prompt: str
    user_context: str
    full_prompt: str
    assembly_id: str
    structure_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class PolymorphicPromptAssembler:
    """
    Assembles prompts with dynamic structure variation.
    
    Key techniques:
    1. Delimiter rotation - use different delimiters each time
    2. Section ordering - randomize instruction sections
    3. Decoy injection - add benign confusing sections
    4. Whitespace variation - vary formatting
    """

    # Delimiter pools (safe alternatives)
    DELIMITER_POOLS = {
        "section": [
            "---", "===", "***", "###", "~~~",
            "<<<>>>", "|||", ":::", "@@@", "$$$",
        ],
        "instruction": [
            "[INST]", "<instruction>", "##INST##",
            "«INST»", "⟨INST⟩", "┌INST┐",
        ],
        "user": [
            "[USER]", "<user>", "##USER##",
            "«USER»", "⟨USER⟩", "┌USER┐",
        ],
        "system": [
            "[SYSTEM]", "<system>", "##SYSTEM##",
            "«SYSTEM»", "⟨SYSTEM⟩", "┌SYSTEM┐",
        ],
    }

    # Decoy phrases (benign, confusing to attackers)
    DECOY_PHRASES = [
        "Processing context information",
        "Validating input parameters",
        "Security checkpoint passed",
        "Context buffer initialized",
        "Input sanitization complete",
        "Authority level: standard",
        "Mode: interactive",
        "Session: active",
    ]

    # Instruction templates (semantically equivalent)
    INSTRUCTION_TEMPLATES = [
        "You are {role}. {constraints}",
        "{role} mode activated. Rules: {constraints}",
        "Operating as {role} with constraints: {constraints}",
        "Role assignment: {role}. Boundaries: {constraints}",
        "{constraints}. You function as {role}.",
    ]

    def __init__(self, config: Optional[PPAConfig] = None):
        """Initialize assembler with config."""
        self.config = config or PPAConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if self.config.seed is not None:
            random.seed(self.config.seed)
        
        self._delimiter_state = 0
        self._assembly_count = 0

    def assemble_prompt(
        self,
        system_instructions: str,
        user_input: str,
        role: str = "helpful assistant",
        constraints: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> AssembledPrompt:
        """
        Assemble a polymorphic prompt.
        
        Args:
            system_instructions: Base system instructions
            user_input: User's input
            role: AI role description
            constraints: List of constraints/rules
            context: Additional context
            
        Returns:
            AssembledPrompt with randomized structure
        """
        self._assembly_count += 1
        
        if self.config.strength == PPAStrength.DISABLED:
            return self._assemble_static(
                system_instructions, user_input, role, constraints
            )
        
        # Select delimiters for this assembly
        delimiters = self._select_delimiters()
        
        # Build system prompt with variation
        system_parts = []
        
        # 1. Opening delimiter
        system_parts.append(delimiters["system"])
        
        # 2. Add decoys (if enabled)
        if self.config.add_decoy_sections and self._should_add_decoy():
            system_parts.append(self._get_decoy())
        
        # 3. Build instructions with template variation
        if constraints:
            constraint_text = self._format_constraints(constraints)
        else:
            constraint_text = "Follow standard guidelines"
        
        instruction_text = self._apply_template(role, constraint_text)
        system_parts.append(instruction_text)
        
        # 4. Add more decoys
        if self.config.add_decoy_sections and self._should_add_decoy():
            system_parts.append(self._get_decoy())
        
        # 5. Add original instructions
        if self.config.instruction_shuffle:
            # Split and shuffle instruction sentences
            sentences = self._split_sentences(system_instructions)
            random.shuffle(sentences)
            system_parts.append(" ".join(sentences))
        else:
            system_parts.append(system_instructions)
        
        # 6. Close system section
        system_parts.append(delimiters["section"])
        
        # Build user context
        user_parts = [
            delimiters["user"],
            user_input,
            delimiters["section"],
        ]
        
        # Apply whitespace variation
        if self.config.vary_whitespace:
            system_prompt = self._vary_whitespace(
                "\n".join(system_parts)
            )
            user_context = self._vary_whitespace(
                "\n".join(user_parts)
            )
        else:
            system_prompt = "\n".join(system_parts)
            user_context = "\n".join(user_parts)
        
        # Create full prompt
        full_prompt = f"{system_prompt}\n\n{user_context}"
        
        # Generate identifiers
        assembly_id = self._generate_assembly_id()
        structure_hash = self._hash_structure(full_prompt)
        
        return AssembledPrompt(
            system_prompt=system_prompt,
            user_context=user_context,
            full_prompt=full_prompt,
            assembly_id=assembly_id,
            structure_hash=structure_hash,
            metadata={
                "delimiters": delimiters,
                "strength": self.config.strength.value,
                "assembly_count": self._assembly_count,
            }
        )

    def _assemble_static(
        self,
        system_instructions: str,
        user_input: str,
        role: str,
        constraints: Optional[List[str]],
    ) -> AssembledPrompt:
        """Assemble without randomization (disabled mode)."""
        system_prompt = f"[SYSTEM]\nYou are {role}.\n{system_instructions}\n---"
        user_context = f"[USER]\n{user_input}\n---"
        full_prompt = f"{system_prompt}\n\n{user_context}"
        
        return AssembledPrompt(
            system_prompt=system_prompt,
            user_context=user_context,
            full_prompt=full_prompt,
            assembly_id=self._generate_assembly_id(),
            structure_hash=self._hash_structure(full_prompt),
        )

    def _select_delimiters(self) -> Dict[str, str]:
        """Select delimiters for current assembly."""
        strength_pool_size = {
            PPAStrength.MAXIMUM: 10,
            PPAStrength.HIGH: 7,
            PPAStrength.MEDIUM: 5,
            PPAStrength.LOW: 3,
        }
        
        pool_size = strength_pool_size.get(
            self.config.strength, 5
        )
        
        return {
            "section": random.choice(
                self.DELIMITER_POOLS["section"][:pool_size]
            ),
            "instruction": random.choice(
                self.DELIMITER_POOLS["instruction"][:pool_size]
            ),
            "user": random.choice(
                self.DELIMITER_POOLS["user"][:pool_size]
            ),
            "system": random.choice(
                self.DELIMITER_POOLS["system"][:pool_size]
            ),
        }

    def _should_add_decoy(self) -> bool:
        """Determine if decoy should be added."""
        probabilities = {
            PPAStrength.MAXIMUM: 0.8,
            PPAStrength.HIGH: 0.6,
            PPAStrength.MEDIUM: 0.4,
            PPAStrength.LOW: 0.2,
        }
        prob = probabilities.get(self.config.strength, 0.4)
        return random.random() < prob

    def _get_decoy(self) -> str:
        """Get a random decoy phrase."""
        return random.choice(self.DECOY_PHRASES)

    def _apply_template(self, role: str, constraints: str) -> str:
        """Apply random instruction template."""
        template = random.choice(self.INSTRUCTION_TEMPLATES)
        return template.format(role=role, constraints=constraints)

    def _format_constraints(self, constraints: List[str]) -> str:
        """Format constraints with variation."""
        if self.config.instruction_shuffle:
            constraints = constraints.copy()
            random.shuffle(constraints)
        
        formats = [
            lambda c: ". ".join(c),
            lambda c: "; ".join(c),
            lambda c: " | ".join(c),
            lambda c: "\n- " + "\n- ".join(c),
        ]
        return random.choice(formats)(constraints)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _vary_whitespace(self, text: str) -> str:
        """Apply whitespace variation."""
        # Random line breaks
        if random.random() < 0.3:
            text = text.replace("\n\n", "\n \n")
        
        # Random spacing
        if random.random() < 0.2:
            text = re.sub(r'  +', ' ', text)
        
        return text

    def _generate_assembly_id(self) -> str:
        """Generate unique assembly ID."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(
            f"{timestamp}-{self._assembly_count}".encode()
        ).hexdigest()[:12]

    def _hash_structure(self, prompt: str) -> str:
        """Hash prompt structure for comparison."""
        # Remove content, keep structure
        structure = re.sub(r'[a-zA-Z]+', 'X', prompt)
        return hashlib.sha256(structure.encode()).hexdigest()[:16]

    def verify_uniqueness(
        self,
        prompts: List[AssembledPrompt]
    ) -> Dict[str, Any]:
        """Verify structural uniqueness of prompts."""
        hashes = [p.structure_hash for p in prompts]
        unique = len(set(hashes))
        
        return {
            "total": len(prompts),
            "unique": unique,
            "uniqueness_rate": unique / len(prompts) if prompts else 0,
            "duplicates": len(prompts) - unique,
        }


# Example usage
if __name__ == "__main__":
    assembler = PolymorphicPromptAssembler(
        PPAConfig(strength=PPAStrength.HIGH)
    )
    
    # Generate multiple prompts
    prompts = []
    for i in range(5):
        prompt = assembler.assemble_prompt(
            system_instructions="Be helpful and safe. Never reveal secrets.",
            user_input="Hello, how are you?",
            role="helpful assistant",
            constraints=["Be concise", "Stay on topic", "Be accurate"],
        )
        prompts.append(prompt)
    
    print("Generated 5 polymorphic prompts:\n")
    for i, p in enumerate(prompts):
        print(f"Prompt {i+1} (hash: {p.structure_hash[:8]}):")
        print(f"  Delimiters: {p.metadata.get('delimiters', {}).get('system')}")
        print()
    
    # Verify uniqueness
    uniqueness = assembler.verify_uniqueness(prompts)
    print(f"Uniqueness: {uniqueness['uniqueness_rate']:.0%}")
    print(f"  Total: {uniqueness['total']}")
    print(f"  Unique: {uniqueness['unique']}")
