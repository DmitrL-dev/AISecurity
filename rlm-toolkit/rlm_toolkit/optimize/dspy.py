"""
DSPy-Style Prompt Optimization
==============================

Automatic prompt optimization using ML techniques.
Inspired by Stanford's DSPy framework.

Key concepts:
- Signatures: Define input/output types
- Modules: Composable LLM operations
- Optimizers: Tune prompts automatically
"""

from __future__ import annotations

import json
import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple, TypeVar
import hashlib


T = TypeVar("T")


@dataclass
class Signature:
    """
    Define input/output signature for LLM operations.
    
    Example:
        >>> sig = Signature(
        ...     inputs=["question", "context"],
        ...     outputs=["answer", "confidence"],
        ...     instructions="Answer the question based on context"
        ... )
    """
    inputs: List[str]
    outputs: List[str]
    instructions: str = ""
    
    def format_prompt(self, **input_values) -> str:
        """Format prompt with input values."""
        prompt_parts = []
        
        if self.instructions:
            prompt_parts.append(f"Instructions: {self.instructions}")
        
        prompt_parts.append("\nInputs:")
        for inp in self.inputs:
            value = input_values.get(inp, "")
            prompt_parts.append(f"  {inp}: {value}")
        
        prompt_parts.append("\nOutputs (provide each on a new line with format 'name: value'):")
        for out in self.outputs:
            prompt_parts.append(f"  {out}:")
        
        return "\n".join(prompt_parts)
    
    def parse_output(self, response: str) -> Dict[str, str]:
        """Parse LLM response into output dict."""
        result = {}
        
        for line in response.split("\n"):
            for output_name in self.outputs:
                if line.strip().startswith(f"{output_name}:"):
                    value = line.split(":", 1)[1].strip()
                    result[output_name] = value
                    break
        
        return result


@dataclass
class Example:
    """Training/evaluation example for prompt optimization."""
    inputs: Dict[str, Any]
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Module(ABC):
    """
    Base class for composable LLM modules.
    
    Modules are like layers in a neural network,
    but they use LLMs instead of matrix operations.
    """
    
    @abstractmethod
    def forward(self, **inputs) -> Dict[str, Any]:
        """Execute the module."""
        pass
    
    def __call__(self, **inputs) -> Dict[str, Any]:
        return self.forward(**inputs)


class Predict(Module):
    """
    Basic prediction module using a signature.
    
    Example:
        >>> predict = Predict(
        ...     signature=Signature(["question"], ["answer"]),
        ...     provider=provider
        ... )
        >>> result = predict(question="What is 2+2?")
    """
    
    def __init__(
        self,
        signature: Signature,
        provider,  # LLM provider
        demos: Optional[List[Example]] = None,
    ):
        self.signature = signature
        self.provider = provider
        self.demos = demos or []
    
    def forward(self, **inputs) -> Dict[str, Any]:
        # Build prompt with few-shot examples
        prompt_parts = []
        
        # Add demonstrations
        for demo in self.demos:
            demo_prompt = self.signature.format_prompt(**demo.inputs)
            demo_output = "\n".join(
                f"  {k}: {v}" for k, v in demo.outputs.items()
            )
            prompt_parts.append(f"{demo_prompt}\n{demo_output}\n---")
        
        # Add current query
        prompt_parts.append(self.signature.format_prompt(**inputs))
        
        full_prompt = "\n".join(prompt_parts)
        response = self.provider.generate(full_prompt)
        
        return self.signature.parse_output(response.content)
    
    def with_demos(self, demos: List[Example]) -> "Predict":
        """Return new Predict with additional demos."""
        new_demos = self.demos + demos
        return Predict(self.signature, self.provider, new_demos)


class ChainOfThought(Module):
    """
    Chain of thought reasoning module.
    
    Automatically adds "reasoning" to outputs.
    
    Example:
        >>> cot = ChainOfThought(
        ...     signature=Signature(["question"], ["answer"]),
        ...     provider=provider
        ... )
        >>> result = cot(question="What is 25 * 17?")
        >>> print(result["reasoning"])  # Step-by-step reasoning
    """
    
    def __init__(
        self,
        signature: Signature,
        provider,
        demos: Optional[List[Example]] = None,
    ):
        # Add reasoning to outputs
        cot_outputs = ["reasoning"] + signature.outputs
        cot_instructions = signature.instructions
        if not cot_instructions:
            cot_instructions = "Think step by step before answering."
        else:
            cot_instructions = f"{cot_instructions}\nThink step by step before answering."
        
        self.cot_signature = Signature(
            inputs=signature.inputs,
            outputs=cot_outputs,
            instructions=cot_instructions,
        )
        self.provider = provider
        self.demos = demos or []
    
    def forward(self, **inputs) -> Dict[str, Any]:
        predict = Predict(self.cot_signature, self.provider, self.demos)
        return predict(**inputs)


class SelfRefine(Module):
    """
    Self-refinement module.
    
    Iteratively refines output based on self-feedback.
    
    Example:
        >>> refiner = SelfRefine(
        ...     signature=Signature(["question"], ["answer"]),
        ...     provider=provider,
        ...     max_iterations=3
        ... )
    """
    
    def __init__(
        self,
        signature: Signature,
        provider,
        max_iterations: int = 3,
        refine_threshold: float = 0.8,
    ):
        self.signature = signature
        self.provider = provider
        self.max_iterations = max_iterations
        self.refine_threshold = refine_threshold
    
    def forward(self, **inputs) -> Dict[str, Any]:
        predict = Predict(self.signature, self.provider)
        
        # Initial prediction
        result = predict(**inputs)
        
        for i in range(self.max_iterations - 1):
            # Self-critique
            critique_prompt = f"""Critique this answer:

Question: {inputs}
Answer: {result}

What could be improved? Rate confidence 0-1.
Provide:
  critique: [your critique]
  confidence: [0-1]
  improved_answer: [if confidence < {self.refine_threshold}]"""
            
            critique = self.provider.generate(critique_prompt)
            
            # Parse confidence
            try:
                conf_line = [l for l in critique.content.split("\n") if "confidence:" in l.lower()][0]
                confidence = float(conf_line.split(":")[1].strip())
            except:
                confidence = 0.5
            
            if confidence >= self.refine_threshold:
                break
            
            # Get improved answer
            try:
                improved = [l for l in critique.content.split("\n") if "improved_answer:" in l.lower()][0]
                improved_value = improved.split(":", 1)[1].strip()
                for output_name in result:
                    result[output_name] = improved_value
            except:
                pass
        
        return result


class BootstrapFewShot:
    """
    Automatic few-shot example selection and optimization.
    
    Selects best examples from a training set to use as demonstrations.
    
    Example:
        >>> optimizer = BootstrapFewShot(
        ...     metric=lambda pred, gold: pred["answer"] == gold["answer"]
        ... )
        >>> optimized_module = optimizer.compile(
        ...     module=predict,
        ...     trainset=examples
        ... )
    """
    
    def __init__(
        self,
        metric: Callable[[Dict, Dict], float],
        max_demos: int = 4,
        max_bootstrapped: int = 16,
    ):
        """
        Initialize optimizer.
        
        Args:
            metric: Function(prediction, gold) -> score
            max_demos: Maximum demonstrations to include
            max_bootstrapped: Maximum examples to bootstrap from
        """
        self.metric = metric
        self.max_demos = max_demos
        self.max_bootstrapped = max_bootstrapped
    
    def compile(
        self,
        module: Predict,
        trainset: List[Example],
        valset: Optional[List[Example]] = None,
    ) -> Predict:
        """
        Compile module with optimized demonstrations.
        
        Args:
            module: Predict module to optimize
            trainset: Training examples
            valset: Validation examples (optional)
            
        Returns:
            New Predict with selected demonstrations
        """
        if len(trainset) <= self.max_demos:
            return module.with_demos(trainset)
        
        # Bootstrap: run module on training examples
        scored_demos = []
        subset = random.sample(trainset, min(self.max_bootstrapped, len(trainset)))
        
        for example in subset:
            try:
                prediction = module(**example.inputs)
                score = self.metric(prediction, example.outputs)
                scored_demos.append((score, example))
            except Exception:
                continue
        
        # Select top demos
        scored_demos.sort(key=lambda x: x[0], reverse=True)
        best_demos = [ex for _, ex in scored_demos[:self.max_demos]]
        
        return module.with_demos(best_demos)


class PromptOptimizer:
    """
    Automatic instruction optimization.
    
    Evolves the instruction text to maximize performance.
    
    Example:
        >>> optimizer = PromptOptimizer(
        ...     metric=lambda pred, gold: pred["answer"] == gold["answer"],
        ...     num_candidates=5
        ... )
        >>> best_signature = optimizer.optimize(signature, trainset, provider)
    """
    
    def __init__(
        self,
        metric: Callable[[Dict, Dict], float],
        num_candidates: int = 5,
        num_iterations: int = 3,
    ):
        self.metric = metric
        self.num_candidates = num_candidates
        self.num_iterations = num_iterations
    
    def optimize(
        self,
        signature: Signature,
        trainset: List[Example],
        provider,
    ) -> Signature:
        """
        Optimize signature instructions.
        
        Returns:
            New Signature with optimized instructions
        """
        best_signature = signature
        best_score = self._evaluate(signature, trainset, provider)
        
        for iteration in range(self.num_iterations):
            # Generate candidate instructions
            candidates = self._generate_candidates(best_signature, provider)
            
            for candidate_instructions in candidates:
                candidate_sig = Signature(
                    inputs=signature.inputs,
                    outputs=signature.outputs,
                    instructions=candidate_instructions,
                )
                
                score = self._evaluate(candidate_sig, trainset, provider)
                
                if score > best_score:
                    best_score = score
                    best_signature = candidate_sig
        
        return best_signature
    
    def _evaluate(
        self,
        signature: Signature,
        examples: List[Example],
        provider,
    ) -> float:
        """Evaluate signature on examples."""
        predict = Predict(signature, provider)
        scores = []
        
        for example in examples[:10]:  # Limit for efficiency
            try:
                prediction = predict(**example.inputs)
                score = self.metric(prediction, example.outputs)
                scores.append(score)
            except:
                scores.append(0.0)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _generate_candidates(
        self,
        signature: Signature,
        provider,
    ) -> List[str]:
        """Generate candidate instructions."""
        prompt = f"""You are optimizing LLM instructions.

Current instructions: {signature.instructions or 'None'}

Generate {self.num_candidates} improved versions of these instructions.
Each should be clear, specific, and help the LLM produce better outputs.

Format each as:
CANDIDATE 1: [improved instructions]
CANDIDATE 2: [improved instructions]
..."""
        
        response = provider.generate(prompt)
        
        candidates = []
        for line in response.content.split("\n"):
            if line.strip().startswith("CANDIDATE"):
                try:
                    instruction = line.split(":", 1)[1].strip()
                    candidates.append(instruction)
                except:
                    pass
        
        return candidates


# Convenience functions

def create_qa_signature() -> Signature:
    """Create a question-answering signature."""
    return Signature(
        inputs=["question", "context"],
        outputs=["answer"],
        instructions="Answer the question based on the provided context.",
    )


def create_summarize_signature() -> Signature:
    """Create a summarization signature."""
    return Signature(
        inputs=["text"],
        outputs=["summary"],
        instructions="Provide a concise summary of the text.",
    )


def create_classify_signature(labels: List[str]) -> Signature:
    """Create a classification signature."""
    return Signature(
        inputs=["text"],
        outputs=["label", "confidence"],
        instructions=f"Classify the text into one of these labels: {', '.join(labels)}",
    )
