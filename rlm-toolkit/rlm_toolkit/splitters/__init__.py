"""
Text Splitters
==============

Text splitting strategies for chunking documents.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
import re


class TextSplitter(ABC):
    """Base class for text splitters."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        length_function: Optional[Any] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function or len
    
    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks."""
        pass
    
    def split_documents(self, documents: List[Any]) -> List[Any]:
        """Split a list of documents."""
        from rlm_toolkit.loaders import Document
        
        result = []
        for doc in documents:
            chunks = self.split_text(doc.content)
            for i, chunk in enumerate(chunks):
                metadata = doc.metadata.copy()
                metadata["chunk"] = i
                result.append(Document(chunk, metadata))
        return result


class CharacterTextSplitter(TextSplitter):
    """Split text by character count."""
    
    def __init__(
        self,
        separator: str = "\n\n",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.separator = separator
    
    def split_text(self, text: str) -> List[str]:
        splits = text.split(self.separator)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for split in splits:
            split_length = self.length_function(split)
            
            if current_length + split_length > self.chunk_size and current_chunk:
                chunks.append(self.separator.join(current_chunk))
                
                # Keep overlap
                while current_length > self.chunk_overlap and current_chunk:
                    removed = current_chunk.pop(0)
                    current_length -= self.length_function(removed) + len(self.separator)
            
            current_chunk.append(split)
            current_length += split_length + len(self.separator)
        
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))
        
        return chunks


class RecursiveCharacterTextSplitter(TextSplitter):
    """Recursively split text using multiple separators."""
    
    def __init__(
        self,
        separators: Optional[List[str]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.separators = separators or ["\n\n", "\n", " ", ""]
    
    def split_text(self, text: str) -> List[str]:
        return self._split_text(text, self.separators)
    
    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        final_chunks = []
        
        # Find the appropriate separator
        separator = separators[-1]
        new_separators = []
        
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break
        
        # Split by separator
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)
        
        # Process splits
        good_splits = []
        for split in splits:
            if self.length_function(split) < self.chunk_size:
                good_splits.append(split)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                
                if new_separators:
                    other_chunks = self._split_text(split, new_separators)
                    final_chunks.extend(other_chunks)
                else:
                    final_chunks.append(split)
        
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)
        
        return final_chunks
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        merged = []
        current = []
        total = 0
        
        for split in splits:
            length = self.length_function(split)
            
            if total + length > self.chunk_size and current:
                merged.append(separator.join(current))
                
                while total > self.chunk_overlap and current:
                    removed = current.pop(0)
                    total -= self.length_function(removed) + len(separator)
            
            current.append(split)
            total += length + len(separator)
        
        if current:
            merged.append(separator.join(current))
        
        return merged


class TokenTextSplitter(TextSplitter):
    """Split text by token count."""
    
    def __init__(
        self,
        encoding_name: str = "cl100k_base",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.encoding_name = encoding_name
        self._tokenizer = None
    
    def _get_tokenizer(self):
        if self._tokenizer is None:
            try:
                import tiktoken
                self._tokenizer = tiktoken.get_encoding(self.encoding_name)
            except ImportError:
                raise ImportError("tiktoken required. pip install tiktoken")
        return self._tokenizer
    
    def split_text(self, text: str) -> List[str]:
        tokenizer = self._get_tokenizer()
        tokens = tokenizer.encode(text)
        
        chunks = []
        i = 0
        
        while i < len(tokens):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            i += self.chunk_size - self.chunk_overlap
        
        return chunks


class MarkdownTextSplitter(TextSplitter):
    """Split markdown by headers."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.headers = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
    
    def split_text(self, text: str) -> List[str]:
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = self.length_function(line)
            
            # Check if it's a header
            is_header = any(line.startswith(h[0] + " ") for h in self.headers)
            
            if is_header and current_chunk:
                # Start new chunk on header
                if current_length > 0:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
            
            if current_length + line_length > self.chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += line_length + 1
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks


class CodeTextSplitter(TextSplitter):
    """Split code by functions and classes."""
    
    LANGUAGE_SEPARATORS = {
        "python": ["\nclass ", "\ndef ", "\n\n", "\n"],
        "javascript": ["\nfunction ", "\nconst ", "\nlet ", "\nvar ", "\n\n", "\n"],
        "typescript": ["\nfunction ", "\nconst ", "\nlet ", "\ninterface ", "\ntype ", "\nclass ", "\n\n", "\n"],
        "java": ["\npublic class ", "\nprivate class ", "\npublic static ", "\nprivate static ", "\n\n", "\n"],
        "go": ["\nfunc ", "\ntype ", "\n\n", "\n"],
        "rust": ["\nfn ", "\nstruct ", "\nimpl ", "\npub fn ", "\n\n", "\n"],
    }
    
    def __init__(
        self,
        language: str = "python",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.language = language
        self.separators = self.LANGUAGE_SEPARATORS.get(language, ["\n\n", "\n"])
    
    def split_text(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            separators=self.separators,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return splitter.split_text(text)


class HTMLTextSplitter(TextSplitter):
    """Split HTML by tags."""
    
    def __init__(
        self,
        headers_to_split_on: Optional[List[str]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.headers = headers_to_split_on or ["h1", "h2", "h3", "div", "section"]
    
    def split_text(self, text: str) -> List[str]:
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(text, "html.parser")
            chunks = []
            
            for header in self.headers:
                for element in soup.find_all(header):
                    content = element.get_text(separator="\n", strip=True)
                    if content and self.length_function(content) > 0:
                        if self.length_function(content) <= self.chunk_size:
                            chunks.append(content)
                        else:
                            # Sub-split large chunks
                            splitter = CharacterTextSplitter(
                                chunk_size=self.chunk_size,
                                chunk_overlap=self.chunk_overlap,
                            )
                            chunks.extend(splitter.split_text(content))
            
            return chunks if chunks else [soup.get_text(separator="\n", strip=True)]
        except ImportError:
            # Fallback to simple splitting
            splitter = CharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            return splitter.split_text(text)


class LatexTextSplitter(TextSplitter):
    """Split LaTeX by sections."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.separators = [
            "\\chapter{",
            "\\section{",
            "\\subsection{",
            "\\subsubsection{",
            "\\begin{enumerate}",
            "\\begin{itemize}",
            "\\begin{description}",
            "\n\n",
            "\n",
        ]
    
    def split_text(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            separators=self.separators,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return splitter.split_text(text)


class SentenceTextSplitter(TextSplitter):
    """Split text by sentences."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
    
    def split_text(self, text: str) -> List[str]:
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = self.length_function(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                
                # Keep overlap
                while current_length > self.chunk_overlap and current_chunk:
                    removed = current_chunk.pop(0)
                    current_length -= self.length_function(removed) + 1
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks


class SemanticTextSplitter(TextSplitter):
    """Split text semantically using embeddings."""
    
    def __init__(
        self,
        embedding_function: Any,
        breakpoint_threshold: float = 0.5,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self._embedding_function = embedding_function
        self.breakpoint_threshold = breakpoint_threshold
    
    def split_text(self, text: str) -> List[str]:
        # First split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if len(sentences) <= 1:
            return [text] if text.strip() else []
        
        # Get embeddings for sentences
        embeddings = self._embedding_function.embed_documents(sentences)
        
        # Calculate cosine similarities between consecutive sentences
        import numpy as np
        
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
            )
            similarities.append(sim)
        
        # Find breakpoints where similarity is below threshold
        chunks = []
        current_chunk = [sentences[0]]
        
        for i, sim in enumerate(similarities):
            if sim < self.breakpoint_threshold:
                # New chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i + 1]]
            else:
                current_chunk.append(sentences[i + 1])
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
