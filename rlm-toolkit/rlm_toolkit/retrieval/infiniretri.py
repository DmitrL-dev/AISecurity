"""
InfiniRetri Integration for RLM-Toolkit
========================================

Attention-based infinite context retrieval using the InfiniRetri algorithm.
Reference: arXiv:2502.12962

This module wraps the official infini-retri package to provide seamless
integration with RLM-Toolkit pipelines.
"""

from typing import Any, Dict, List, Optional, Union
import os

try:
    from infini_retri import InfiniRetri as _InfiniRetri
    INFINIRETRI_AVAILABLE = True
except ImportError:
    INFINIRETRI_AVAILABLE = False
    _InfiniRetri = None


class InfiniRetriever:
    """
    Attention-based infinite context retrieval.
    
    Uses the LLM's own attention mechanism to retrieve relevant information
    from contexts of unlimited length, without external embeddings or RAG.
    
    Key features:
    - 100% accuracy on Needle-In-a-Haystack up to 1M+ tokens
    - Works with any Transformer-based LLM
    - Training-free method
    - Caches sentence-level token IDs (not KV states)
    
    Example:
        >>> from rlm_toolkit.retrieval import InfiniRetriever
        >>> retriever = InfiniRetriever("Qwen/Qwen2.5-0.5B-Instruct")
        >>> response = retriever.retrieve(
        ...     context=large_document,
        ...     question="What is the main finding?"
        ... )
    """
    
    def __init__(
        self,
        model_name_or_path: Optional[str] = None,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        window_length: int = 1024,
        topk: int = 300,
        answer_length: int = 8,
        device: Optional[str] = None,
    ):
        """
        Initialize InfiniRetriever.
        
        Args:
            model_name_or_path: HuggingFace model name or local path
            model: Pre-loaded model (alternative to model_name_or_path)
            tokenizer: Pre-loaded tokenizer (required if model is provided)
            window_length: Context window size during retrieval (< model max)
            topk: Number of top sentences to cache
            answer_length: Expected answer token length
            device: Device to use (auto-detected if None)
        """
        if not INFINIRETRI_AVAILABLE:
            raise ImportError(
                "infini-retri package not found. "
                "Install with: pip install infini-retri"
            )
        
        self.window_length = window_length
        self.topk = topk
        self.answer_length = answer_length
        self.device = device or ("cuda" if self._cuda_available() else "cpu")
        
        # Initialize InfiniRetri
        if model is not None and tokenizer is not None:
            self._ir = _InfiniRetri(model, tokenizer)
        elif model_name_or_path:
            self._ir = _InfiniRetri(name_or_path=model_name_or_path)
        else:
            raise ValueError(
                "Must provide either model_name_or_path or (model, tokenizer)"
            )
    
    def _cuda_available(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def retrieve(
        self,
        context: str,
        question: str,
        prompt: Optional[str] = None,
        window_length: Optional[int] = None,
        topk: Optional[int] = None,
        answer_length: Optional[int] = None,
    ) -> str:
        """
        Retrieve answer from context using attention-based retrieval.
        
        Args:
            context: The full context text (can be millions of tokens)
            question: The question to answer
            prompt: Custom prompt template (uses default if None)
            window_length: Override default window_length
            topk: Override default topk
            answer_length: Override default answer_length
            
        Returns:
            Generated answer string
        """
        # Use instance defaults if not overridden
        wl = window_length or self.window_length
        tk = topk or self.topk
        al = answer_length or self.answer_length
        
        # Default prompt template
        if prompt is None:
            prompt = (
                "Read the document and answer the question. "
                "Be concise in your answer.\n\n"
                "{context}\n\n"
                "Question:\n\n{question}\n\n"
                "Answer:"
            )
        
        response = self._ir.generate(
            context=context,
            question=question,
            prompt=prompt,
            window_length=wl,
            topk=tk,
            answer_length=al,
        )
        
        return response
    
    def batch_retrieve(
        self,
        context: str,
        questions: List[str],
        **kwargs
    ) -> List[str]:
        """
        Answer multiple questions from the same context.
        
        Args:
            context: The full context text
            questions: List of questions to answer
            **kwargs: Additional arguments passed to retrieve()
            
        Returns:
            List of answers
        """
        return [
            self.retrieve(context=context, question=q, **kwargs)
            for q in questions
        ]


class InfiniRetriRLM:
    """
    RLM augmented with InfiniRetri for infinite context processing.
    
    Combines RLM's recursive processing with InfiniRetri's attention-based
    retrieval for optimal handling of extremely long contexts.
    
    This is the recommended approach for:
    - Documents > 1M tokens
    - Multi-hop reasoning over large corpora
    - Needle-in-a-haystack retrieval tasks
    """
    
    def __init__(
        self,
        model_name_or_path: str,
        use_infiniretri: bool = True,
        infiniretri_threshold: int = 100_000,  # tokens
        **kwargs
    ):
        """
        Initialize InfiniRetri-augmented RLM.
        
        Args:
            model_name_or_path: Model to use
            use_infiniretri: Whether to enable InfiniRetri
            infiniretri_threshold: Token count above which to use InfiniRetri
            **kwargs: Additional arguments for InfiniRetriever
        """
        self.model_name = model_name_or_path
        self.use_infiniretri = use_infiniretri
        self.threshold = infiniretri_threshold
        
        if use_infiniretri:
            self.retriever = InfiniRetriever(
                model_name_or_path=model_name_or_path,
                **kwargs
            )
        else:
            self.retriever = None
    
    def run(
        self,
        context: str,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process context and answer query.
        
        Automatically uses InfiniRetri for contexts above threshold.
        
        Args:
            context: Input context
            query: Question or task
            **kwargs: Additional arguments
            
        Returns:
            Dict with 'answer' and 'metadata'
        """
        # Estimate token count (rough: 4 chars per token)
        estimated_tokens = len(context) // 4
        
        if self.use_infiniretri and estimated_tokens > self.threshold:
            # Use InfiniRetri for large contexts
            answer = self.retriever.retrieve(
                context=context,
                question=query,
                **kwargs
            )
            method = "infiniretri"
        else:
            # Use standard RLM for smaller contexts
            # TODO: Integrate with core RLM
            answer = f"[Standard RLM processing for {estimated_tokens} tokens]"
            method = "rlm"
        
        return {
            "answer": answer,
            "metadata": {
                "method": method,
                "estimated_tokens": estimated_tokens,
                "threshold": self.threshold,
            }
        }


# Convenience factory function
def create_infinite_retriever(
    model: str = "Qwen/Qwen2.5-0.5B-Instruct",
    **kwargs
) -> InfiniRetriever:
    """
    Create an InfiniRetriever with sensible defaults.
    
    Args:
        model: Model name or path (default: Qwen2.5-0.5B for efficiency)
        **kwargs: Additional arguments for InfiniRetriever
        
    Returns:
        Configured InfiniRetriever instance
    """
    return InfiniRetriever(model_name_or_path=model, **kwargs)
