"""
RLM Core Engine
===============

Main RLM execution engine with REPL loop, streaming, and recovery.
Based on arxiv:2512.24601 with LangChain-competitive features.
"""

from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass, field
from typing import (
    Any, Dict, Iterator, List, Literal, Optional, 
    Set, Tuple, Callable, Union, TYPE_CHECKING
)
from enum import Enum

if TYPE_CHECKING:
    from rlm_toolkit.providers.base import LLMProvider, LLMResponse
    from rlm_toolkit.core.callbacks import RLMCallback, CallbackManager
    from rlm_toolkit.core.streaming import RLMStreamEvent
    from rlm_toolkit.memory.base import Memory
    from rlm_toolkit.observability.tracer import Tracer
    from rlm_toolkit.core.recovery import RecoveryConfig


@dataclass
class RLMConfig:
    """Configuration for RLM execution.
    
    Attributes:
        max_iterations: Maximum REPL iterations (default: 50)
        max_subcalls: Maximum llm_query() calls (default: 100)
        max_cost: Maximum cost in USD (default: 10.0)
        max_depth: Maximum recursion depth (default: 2)
        max_execution_time: Timeout per code block in seconds (default: 30.0)
        max_memory_mb: Memory limit per execution (default: 512)
        sandbox: Enable SecureREPL sandbox (default: True)
        truncate_output: Maximum output chars per execution (default: 10000)
        allowed_imports: Allowed import modules (default: re, json, math, datetime)
        use_infiniretri: Enable InfiniRetri for large contexts (default: True)
        infiniretri_threshold: Token count to trigger InfiniRetri (default: 100000)
        infiniretri_model: Model for InfiniRetri (default: None, uses Qwen2.5-0.5B)
    """
    # Iteration limits
    max_iterations: int = 50
    max_subcalls: int = 100
    max_cost: float = 10.0
    max_depth: int = 2
    
    # CIRCLE-based resource limits
    max_execution_time: float = 30.0
    max_memory_mb: int = 512
    
    # Security
    sandbox: bool = True
    allowed_imports: Set[str] = field(
        default_factory=lambda: {'re', 'json', 'math', 'datetime', 'collections', 'itertools'}
    )
    
    # Output
    truncate_output: int = 10_000
    
    # Recovery (ADR-007)
    recovery: Optional["RecoveryConfig"] = None
    
    # InfiniRetri integration (Track A: R&D 2026)
    use_infiniretri: bool = True
    infiniretri_threshold: int = 100_000  # tokens (~400K chars)
    infiniretri_model: Optional[str] = None  # Default: Qwen/Qwen2.5-0.5B-Instruct


@dataclass
class RLMResult:
    """Result of RLM execution.
    
    Attributes:
        answer: Final answer from FINAL() or FINAL_VAR()
        status: Termination reason
        iterations: Number of REPL iterations
        total_cost: Total cost in USD
        execution_time: Total wall-clock time in seconds
        subcall_count: Number of llm_query() calls
        history: List of (action, output) tuples
        trace_id: Observability trace ID (FR-6)
        rewards: Reward signals if tracking enabled (FR-5.2)
    """
    answer: str
    status: Literal['success', 'max_iterations', 'max_cost', 'max_subcalls', 'error', 'security']
    iterations: int
    total_cost: float
    execution_time: float
    subcall_count: int
    history: List[Tuple[str, str]] = field(default_factory=list)
    trace_id: Optional[str] = None
    rewards: Optional[Any] = None  # RewardHistory
    
    @property
    def success(self) -> bool:
        """True if execution completed successfully."""
        return self.status == 'success'


class RLM:
    """Recursive Language Model engine.
    
    Main entry point for RLM execution. Implements the REPL loop
    from arxiv:2512.24601 with security guards and observability.
    
    Example:
        >>> rlm = RLM.from_ollama("llama4")
        >>> result = rlm.run(huge_doc, "Summarize all chapters")
        >>> print(result.answer)
    
    Attributes:
        root: LLM provider for main reasoning
        sub: LLM provider for llm_query() sub-calls (optional)
        config: RLM configuration
        callbacks: List of callback handlers
        memory: Memory system (optional)
        tracer: OpenTelemetry tracer (optional)
    """
    
    # Default system prompt from RLM paper (Gap G18)
    DEFAULT_SYSTEM_PROMPT = '''You are a Python coding agent that processes large contexts iteratively.

CAPABILITIES:
- You have access to `context` variable containing the full input ({context_length} chars)
- You can call `llm_query(prompt, max_chars=500000)` for semantic analysis
- You can use: {allowed_modules}
- Output is truncated to {max_output} chars

WORKFLOW:
1. Write Python code in ```repl blocks
2. Use variables to store intermediate results  
3. Use llm_query() for sub-analysis
4. End with FINAL(answer) or FINAL_VAR(variable_name)

RULES:
- Do NOT attempt to import blocked modules
- Do NOT write infinite loops
- Do NOT try to access filesystem
- Always end with FINAL() or FINAL_VAR()
'''
    
    def __init__(
        self,
        root: "LLMProvider",
        sub: Optional["LLMProvider"] = None,
        config: Optional[RLMConfig] = None,
        callbacks: Optional[List["RLMCallback"]] = None,
        memory: Optional["Memory"] = None,
        tracer: Optional["Tracer"] = None,
    ):
        """Initialize RLM engine.
        
        Args:
            root: LLM provider for main reasoning
            sub: LLM provider for sub-calls (uses root if None)
            config: Configuration options
            callbacks: Callback handlers for observability
            memory: Memory system for context management
            tracer: OpenTelemetry tracer for distributed tracing
        """
        self.root = root
        self.sub = sub or root
        self.config = config or RLMConfig()
        self.callbacks = callbacks or []
        self.memory = memory
        self.tracer = tracer
        
        # Initialize REPL if sandboxing enabled
        self._repl: Optional["SecureREPL"] = None
        if self.config.sandbox:
            from rlm_toolkit.core.repl import SecureREPL
            self._repl = SecureREPL(
                max_output_length=self.config.truncate_output,
                max_execution_time=self.config.max_execution_time,
                max_memory_mb=self.config.max_memory_mb,
                allowed_imports=self.config.allowed_imports,
            )
        
        # Initialize InfiniRetri for large context handling
        self._infiniretri = None
        if self.config.use_infiniretri:
            try:
                from rlm_toolkit.retrieval.infiniretri import InfiniRetriever, INFINIRETRI_AVAILABLE
                if INFINIRETRI_AVAILABLE:
                    model = self.config.infiniretri_model or "Qwen/Qwen2.5-0.5B-Instruct"
                    self._infiniretri = InfiniRetriever(model_name_or_path=model)
            except ImportError:
                pass  # InfiniRetri not available, fallback to standard RLM
    
    @classmethod
    def from_ollama(
        cls,
        model: str = "llama4",
        sub_model: Optional[str] = None,
        resilient: bool = True,
        **kwargs
    ) -> "RLM":
        """Create RLM with Ollama (local) provider.
        
        Args:
            model: Model name for root LLM
            sub_model: Model name for sub-calls (uses model if None)
            resilient: Wrap with ResilientProvider for retry/rate limiting (default: True)
            **kwargs: Additional arguments for RLM.__init__
        
        Returns:
            Configured RLM instance
        """
        from rlm_toolkit.providers.ollama import OllamaProvider
        from rlm_toolkit.providers.base import ResilientProvider, LLMProvider
        
        root: LLMProvider = OllamaProvider(model)
        sub: Optional[LLMProvider] = OllamaProvider(sub_model) if sub_model else None
        
        if resilient:
            root = ResilientProvider(root)
            if sub:
                sub = ResilientProvider(sub)
        
        return cls(root=root, sub=sub, **kwargs)
    
    @classmethod
    def from_openai(
        cls,
        root_model: str = "gpt-5.2",
        sub_model: str = "gpt-4o-mini",
        resilient: bool = True,
        **kwargs
    ) -> "RLM":
        """Create RLM with OpenAI provider.
        
        Args:
            root_model: Model for main reasoning (default: gpt-5.2)
            sub_model: Model for sub-calls (default: gpt-4o-mini)
            resilient: Wrap with ResilientProvider for retry/rate limiting (default: True)
            **kwargs: Additional arguments for RLM.__init__
        
        Returns:
            Configured RLM instance
        """
        from rlm_toolkit.providers.openai import OpenAIProvider
        from rlm_toolkit.providers.base import ResilientProvider, LLMProvider
        
        root: LLMProvider = OpenAIProvider(root_model)
        sub: LLMProvider = OpenAIProvider(sub_model)
        
        if resilient:
            root = ResilientProvider(root)
            sub = ResilientProvider(sub)
        
        return cls(root=root, sub=sub, **kwargs)
    
    @classmethod
    def from_anthropic(
        cls,
        root_model: str = "claude-opus-4.5",
        sub_model: str = "claude-haiku",
        resilient: bool = True,
        **kwargs
    ) -> "RLM":
        """Create RLM with Anthropic provider.
        
        Args:
            root_model: Model for main reasoning (default: claude-opus-4.5)
            sub_model: Model for sub-calls (default: claude-haiku)
            resilient: Wrap with ResilientProvider for retry/rate limiting (default: True)
        """
        from rlm_toolkit.providers.anthropic import AnthropicProvider
        from rlm_toolkit.providers.base import ResilientProvider, LLMProvider
        
        root: LLMProvider = AnthropicProvider(root_model)
        sub: LLMProvider = AnthropicProvider(sub_model)
        
        if resilient:
            root = ResilientProvider(root)
            sub = ResilientProvider(sub)
        
        return cls(root=root, sub=sub, **kwargs)
    
    def _build_system_prompt(self, context_length: int) -> str:
        """Build system prompt with context info."""
        return self.DEFAULT_SYSTEM_PROMPT.format(
            context_length=context_length,
            allowed_modules=", ".join(sorted(self.config.allowed_imports)),
            max_output=self.config.truncate_output,
        )
    
    def _extract_final_arg(self, text: str, marker: str) -> Optional[str]:
        """Extract argument from FINAL() or FINAL_VAR() with proper bracket counting.
        
        Handles nested parentheses correctly, e.g.:
        - FINAL("calculate(a + b) = 5") → 'calculate(a + b) = 5'
        - FINAL(f"Result: {func(x)}") → f"Result: {func(x)}"
        
        Args:
            text: Full text containing marker
            marker: Either "FINAL(" or "FINAL_VAR("
        
        Returns:
            Extracted argument or None if not found
        """
        start_idx = text.find(marker)
        if start_idx == -1:
            return None
        
        # Start after the opening paren
        content_start = start_idx + len(marker)
        
        # Count brackets to find matching close paren
        depth = 1
        in_string = None  # Track string context (', ", ''', """)
        i = content_start
        
        while i < len(text) and depth > 0:
            char = text[i]
            
            # Handle string literals
            if in_string:
                # Check if current position ends the string
                str_len = len(in_string)
                if text[i:i+str_len] == in_string:
                    i += str_len - 1  # Skip rest of closing quote (will +1 at end)
                    in_string = None
            else:
                # Check for string start
                if text[i:i+3] in ('"""', "'''"):
                    in_string = text[i:i+3]
                    i += 2
                elif char in ('"', "'"):
                    in_string = char
                elif char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
            
            i += 1
        
        if depth == 0:
            # Found matching paren, extract content (excluding final paren)
            return text[content_start:i-1].strip()
        
        return None
    
    def _fire_callback(self, event: str, **kwargs) -> None:
        """Fire event to all callbacks."""
        for callback in self.callbacks:
            method = getattr(callback, event, None)
            if method:
                try:
                    method(**kwargs)
                except Exception:
                    pass  # Don't let callbacks break execution
    
    def run(
        self,
        context: str,
        query: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> RLMResult:
        """Execute RLM on context with query.
        
        This is the main entry point for RLM execution. Implements
        the REPL loop from the RLM paper with FINAL() detection.
        
        Args:
            context: Full context (can be 10M+ tokens)
            query: User query about the context
            system_prompt: Custom system prompt (uses default if None)
            **kwargs: Override config values
        
        Returns:
            RLMResult with answer, cost, iterations, etc.
        """
        from rlm_toolkit.core.state import RLMState
        
        start_time = time.perf_counter()
        
        # Check if context exceeds InfiniRetri threshold
        estimated_tokens = len(context) // 4  # Rough: 4 chars per token
        if self._infiniretri and estimated_tokens > self.config.infiniretri_threshold:
            # Use InfiniRetri for large context retrieval
            self._fire_callback("on_infiniretri_start", context_tokens=estimated_tokens, threshold=self.config.infiniretri_threshold)
            
            try:
                answer = self._infiniretri.retrieve(context=context, question=query)
                
                self._fire_callback("on_infiniretri_end", answer=answer[:200])
                
                return RLMResult(
                    answer=answer,
                    status='success',
                    iterations=0,
                    total_cost=0.0,  # InfiniRetri runs locally
                    execution_time=time.perf_counter() - start_time,
                    subcall_count=0,
                    history=[(f"InfiniRetri ({estimated_tokens} tokens)", answer[:500])],
                )
            except Exception as e:
                # Fallback to standard RLM on InfiniRetri failure
                self._fire_callback("on_error", error=e, context={"method": "infiniretri"})
        
        # Initialize state
        state = RLMState(
            context=context,
            context_hash=hashlib.sha256(context.encode()[:10000]).hexdigest()[:16],
        )
        
        # Build prompts
        sys_prompt = system_prompt or self._build_system_prompt(len(context))
        initial_prompt = f"Context length: {len(context)} chars\n\nQuery: {query}"
        
        # Fire start callback (FR-7)
        self._fire_callback("on_run_start", context=context, query=query, config=self.config)
        
        # Create llm_query function for sub-calls
        def llm_query(prompt: str, max_chars: int = 500_000) -> str:
            """Sub-LLM call for semantic analysis."""
            if state.subcall_count >= self.config.max_subcalls:
                return f"Error: Max subcalls ({self.config.max_subcalls}) exceeded"
            
            if state.total_cost >= self.config.max_cost:
                return f"Error: Max cost (${self.config.max_cost}) exceeded"
            
            self._fire_callback("on_subcall_start", prompt=prompt[:200], depth=1)
            
            try:
                truncated_prompt = prompt[:max_chars]
                response = self.sub.generate(truncated_prompt)
                cost = self.sub.get_cost(response)
                
                state.subcall_count += 1
                state.total_cost += cost
                
                self._fire_callback("on_subcall_end", response=response.content[:200], depth=1, cost=cost)
                
                return response.content
            except Exception as e:
                # Don't crash on provider errors, return error message
                error_msg = f"Error in llm_query: {type(e).__name__}: {e}"
                self._fire_callback("on_error", error=e, context={"subcall_prompt": prompt[:100]})
                return error_msg
        
        # Main REPL loop
        try:
            while state.iteration < self.config.max_iterations:
                self._fire_callback("on_iteration_start", iteration=state.iteration, history=state.history)
                
                # Build prompt with history
                if state.history:
                    history_text = "\n\n".join(
                        f"[Iteration {i+1}]\nAction:\n{action}\n\nOutput:\n{output}"
                        for i, (action, output) in enumerate(state.history)
                    )
                    full_prompt = f"{initial_prompt}\n\n{history_text}\n\nContinue:"
                else:
                    full_prompt = initial_prompt
                
                # Generate action from root LLM
                response = self.root.generate(
                    full_prompt,
                    system_prompt=sys_prompt,
                )
                state.total_cost += self.root.get_cost(response)
                action = response.content
                
                self._fire_callback("on_llm_response", response=response, is_subcall=False)
                
                # Check for FINAL()
                if "FINAL(" in action:
                    # Use proper bracket counting, not regex (handles nested parens)
                    answer = self._extract_final_arg(action, "FINAL(")
                    if answer is not None:
                        # Remove quotes if present
                        if (answer.startswith('"') and answer.endswith('"')) or \
                           (answer.startswith("'") and answer.endswith("'")):
                            answer = answer[1:-1]
                        
                        self._fire_callback("on_final", result=answer)
                        
                        return RLMResult(
                            answer=answer,
                            status='success',
                            iterations=state.iteration + 1,
                            total_cost=state.total_cost,
                            execution_time=time.perf_counter() - start_time,
                            subcall_count=state.subcall_count,
                            history=state.history,
                        )
                
                # Check for FINAL_VAR()
                if "FINAL_VAR(" in action:
                    import re
                    match = re.search(r'FINAL_VAR\((\w+)\)', action)
                    if match:
                        var_name = match.group(1)
                        answer = str(state.variables.get(var_name, f"Variable '{var_name}' not found"))
                        
                        self._fire_callback("on_final", result=answer)
                        
                        return RLMResult(
                            answer=answer,
                            status='success',
                            iterations=state.iteration + 1,
                            total_cost=state.total_cost,
                            execution_time=time.perf_counter() - start_time,
                            subcall_count=state.subcall_count,
                            history=state.history,
                        )
                
                # Extract and execute code
                output = ""
                if self._repl:
                    code = self._repl.extract_code(action)
                    if code:
                        self._fire_callback("on_code_extracted", code=code)
                        
                        try:
                            # Build namespace with context and llm_query
                            namespace = state.get_namespace()
                            namespace['context'] = context
                            namespace['llm_query'] = llm_query
                            
                            output = self._repl.execute(code, namespace, llm_query)
                            
                            # Sync variables back to state
                            for key, value in namespace.items():
                                if not key.startswith('_') and key not in ('context', 'llm_query'):
                                    if isinstance(value, (str, int, float, list, dict, bool, type(None))):
                                        state.variables[key] = value
                            
                            self._fire_callback("on_code_executed", code=code, output=output)
                            
                        except Exception as e:
                            output = f"Error: {type(e).__name__}: {e}"
                            self._fire_callback("on_error", error=e, context={"code": code})
                else:
                    output = "No code block found in response"
                
                # Add to history
                state.history.append((action, output))
                state.iteration += 1
                
                self._fire_callback("on_iteration_end", iteration=state.iteration, output=output)
                
                # Check limits
                if state.total_cost >= self.config.max_cost:
                    return RLMResult(
                        answer=f"Execution stopped: cost limit (${self.config.max_cost}) reached",
                        status='max_cost',
                        iterations=state.iteration,
                        total_cost=state.total_cost,
                        execution_time=time.perf_counter() - start_time,
                        subcall_count=state.subcall_count,
                        history=state.history,
                    )
            
            # Max iterations reached
            return RLMResult(
                answer="Execution stopped: max iterations reached without FINAL()",
                status='max_iterations',
                iterations=state.iteration,
                total_cost=state.total_cost,
                execution_time=time.perf_counter() - start_time,
                subcall_count=state.subcall_count,
                history=state.history,
            )
        
        except Exception as e:
            self._fire_callback("on_error", error=e, context={})
            
            return RLMResult(
                answer=f"Execution error: {type(e).__name__}: {e}",
                status='error',
                iterations=state.iteration,
                total_cost=state.total_cost,
                execution_time=time.perf_counter() - start_time,
                subcall_count=state.subcall_count,
                history=state.history,
            )
    
    async def arun(
        self,
        context: str,
        query: str,
        **kwargs
    ) -> RLMResult:
        """Async version of run().
        
        Enables parallel sub-calls and non-blocking execution.
        """
        # TODO: Implement async version with asyncio.gather() for parallel sub-calls
        # For now, delegate to sync version
        return self.run(context, query, **kwargs)
    
    def stream(
        self,
        context: str,
        query: str,
        **kwargs
    ) -> Iterator["RLMStreamEvent"]:
        """Streaming version of run().
        
        Yields RLMStreamEvent for real-time progress tracking.
        """
        from rlm_toolkit.core.streaming import RLMStreamEvent
        
        # Yield start event
        yield RLMStreamEvent(
            type='run_start',
            iteration=0,
            timestamp=time.time(),
            data={'context_length': len(context), 'query': query[:100]},
        )
        
        # Run and yield events
        result = self.run(context, query, **kwargs)
        
        # Yield final event
        yield RLMStreamEvent(
            type='final' if result.success else 'error',
            iteration=result.iterations,
            timestamp=time.time(),
            data={'answer': result.answer, 'status': result.status},
        )
