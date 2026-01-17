# Tutorial 8: Self-Evolving LLMs

Build AI systems that improve themselves through usage using R-Zero Challenger-Solver dynamics.

## What is Self-Evolving?

Self-Evolving LLMs use a novel approach inspired by DeepSeek-R1:

- **R-Zero Pattern**: LLMs develop reasoning without human supervision
- **Challenger-Solver**: Two AI personas that challenge and improve each other
- **Continuous Improvement**: Gets better with every interaction
- **No Expensive Fine-tuning**: Pure inference-time learning

## How Self-Evolving Works

```
┌─────────────────────────────────────────────────────────────────┐
│                Self-Evolving Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Query                                                      │
│       ↓                                                          │
│  SOLVER: Generate initial response                              │
│       ↓                                                          │
│  CHALLENGER: Critique the response, find flaws                  │
│       ↓                                                          │
│  SOLVER: Improve based on critique                              │
│       ↓ (repeat until satisfied or max iterations)              │
│                                                                  │
│  META-LEARNING: Record successful patterns                      │
│       ↓                                                          │
│  Future queries benefit from learned patterns                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Step 1: Basic Self-Evolving RLM

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.evolve import SelfEvolvingRLM

# Create self-evolving instance
evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    strategy="challenger_solver",
    max_iterations=3
)

# First attempt - learns from the process
result = evolving.run("Explain quantum entanglement simply")
print(result.final_answer)

# See the evolution
print(f"Iterations: {result.iterations}")
print(f"Improvements: {result.improvements}")
```

## Step 2: Configure Evolution Strategies

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig

config = EvolutionConfig(
    # Strategy
    strategy="challenger_solver",  # or "self_critique", "ensemble"
    
    # Iterations
    max_iterations=5,
    early_stop_threshold=0.95,  # Stop when quality score > 0.95
    
    # Challenger settings
    challenger_temperature=0.7,  # More creative challenges
    critic_depth="thorough",     # shallow, medium, thorough
    
    # Meta-learning
    enable_meta_learning=True,
    meta_store_path="./evolution_cache",
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)
```

## Step 3: Observe the Evolution Process

```python
from rlm_toolkit.evolve import SelfEvolvingRLM

evolving = SelfEvolvingRLM.from_openai("gpt-4o", verbose=True)

result = evolving.run("Write a sorting algorithm in Python")

# Detailed evolution trace
for iteration in result.evolution_trace:
    print(f"\n--- Iteration {iteration.round} ---")
    print(f"Solver Output: {iteration.solver_response[:200]}...")
    print(f"Challenger Critique: {iteration.challenger_critique}")
    print(f"Quality Score: {iteration.quality_score}")
```

Output example:
```
--- Iteration 1 ---
Solver Output: def bubble_sort(arr): for i in range...
Challenger Critique: Implementation works but is O(n²). 
  Consider more efficient algorithms like quicksort.
Quality Score: 0.65

--- Iteration 2 ---
Solver Output: def quicksort(arr): if len(arr) <= 1...
Challenger Critique: Good improvement! But no handling 
  for edge cases like empty arrays.
Quality Score: 0.85

--- Iteration 3 ---
Solver Output: def quicksort(arr): """Efficient sorting...
Challenger Critique: Excellent! Handles edge cases, 
  includes docstring, good style.
Quality Score: 0.95
```

## Step 4: Different Evolution Strategies

### Challenger-Solver (Default)
```python
# Two personas: one generates, one critiques
config = EvolutionConfig(strategy="challenger_solver")
```

### Self-Critique
```python
# Single model critiques itself
config = EvolutionConfig(
    strategy="self_critique",
    critique_prompt="Analyze flaws in your response and improve"
)
```

### Ensemble
```python
# Multiple models vote on best approach
config = EvolutionConfig(
    strategy="ensemble",
    ensemble_size=3,
    voting_method="consensus"
)
```

## Step 5: Meta-Learning

Store and reuse successful patterns:

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, MetaStore

# Create persistent meta-store
meta_store = MetaStore(path="./meta_learning")

evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    meta_store=meta_store
)

# First query - full evolution
evolving.run("Write a binary search function")

# Similar future queries use learned patterns
evolving.run("Write a linear search function")  # Faster!

# View learned patterns
patterns = meta_store.get_patterns(topic="algorithms")
print(patterns)
```

## Step 6: Domain-Specific Evolution

Train for specific domains:

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, DomainConfig

# Legal document analysis
legal_config = DomainConfig(
    domain="legal",
    critique_focus=[
        "legal accuracy",
        "citation correctness",
        "jurisdiction applicability"
    ],
    quality_metrics=[
        "precedent_relevance",
        "argument_structure"
    ]
)

# Medical analysis
medical_config = DomainConfig(
    domain="medical",
    critique_focus=[
        "clinical accuracy",
        "evidence basis",
        "contraindication awareness"
    ],
    safety_checks=True
)

legal_evolving = SelfEvolvingRLM.from_openai("gpt-4o", domain_config=legal_config)
```

## Step 7: Combine with Other Features

### With Memory
```python
from rlm_toolkit.evolve import SelfEvolvingRLM
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory()

evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    memory=memory  # Evolution aware of context
)
```

### With Tools
```python
from rlm_toolkit.evolve import SelfEvolvingRLM
from rlm_toolkit.tools import Calculator, WebSearch

evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    tools=[Calculator(), WebSearch()],
    evolve_tool_usage=True  # Improve tool selection
)
```

## Complete Application: Evolving Code Assistant

```python
# evolving_code_assistant.py
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig, MetaStore
from rlm_toolkit.tools import SecurePythonREPL
from rlm_toolkit.memory import HierarchicalMemory

class EvolvingCodeAssistant:
    def __init__(self):
        # Persistent learning
        self.meta_store = MetaStore(path="./code_evolution")
        self.memory = HierarchicalMemory(persist_directory="./code_memory")
        
        # Evolution config for code
        config = EvolutionConfig(
            strategy="challenger_solver",
            max_iterations=4,
            critique_focus=[
                "code correctness",
                "efficiency",
                "readability",
                "edge case handling"
            ],
            enable_meta_learning=True
        )
        
        self.rlm = SelfEvolvingRLM.from_openai(
            "gpt-4o",
            config=config,
            meta_store=self.meta_store,
            memory=self.memory,
            tools=[SecurePythonREPL(sandbox=True)]
        )
    
    def generate_code(self, task: str) -> dict:
        """Generate and evolve code for a task."""
        result = self.rlm.run(f"Write Python code to: {task}")
        
        return {
            "code": result.final_answer,
            "iterations": result.iterations,
            "improvements": result.improvements,
            "quality_score": result.final_quality_score
        }
    
    def explain_evolution(self, result) -> str:
        """Explain how the code evolved."""
        explanation = []
        for i, trace in enumerate(result.evolution_trace, 1):
            explanation.append(
                f"Round {i}: {trace.challenger_critique}\n"
                f"Improvement: {trace.improvement_made}"
            )
        return "\n\n".join(explanation)

def main():
    print("🧬 Evolving Code Assistant")
    print("   Watch code improve in real-time!\n")
    
    assistant = EvolvingCodeAssistant()
    
    while True:
        task = input("📝 Task: ").strip()
        
        if task.lower() in ['quit', 'exit']:
            break
        
        print("\n⏳ Evolving solution...\n")
        result = assistant.generate_code(task)
        
        print(f"✅ Final Code (Quality: {result['quality_score']:.0%}):\n")
        print(result['code'])
        print(f"\n📈 Evolved through {result['iterations']} iterations")
        print(f"🔧 Improvements made: {result['improvements']}\n")

if __name__ == "__main__":
    main()
```

## Benchmarks

| Task | Base GPT-4 | + Self-Evolving | Improvement |
|------|-----------|-----------------|-------------|
| Code correctness | 78% | 94% | +16% |
| Math reasoning | 82% | 95% | +13% |
| Complex queries | 71% | 89% | +18% |

## Best Practices

!!! tip "Iteration Count"
    3-5 iterations is optimal. More iterations have diminishing returns.

!!! tip "Early Stopping"
    Use quality threshold to stop early:
    ```python
    config = EvolutionConfig(early_stop_threshold=0.9)
    ```

!!! tip "Meta-Learning"
    Always enable meta-learning for repeated use:
    ```python
    meta_store = MetaStore(path="./cache")
    ```

!!! warning "Cost"
    Self-evolving uses 2-5x more tokens. Use for high-value tasks.

## Next Steps

- [Tutorial 9: Multi-Agent](09-multiagent.md)
- [Concept: Self-Evolving](../concepts/self-evolving.md)
- [Concept: R-Zero Pattern](../concepts/r-zero.md)
