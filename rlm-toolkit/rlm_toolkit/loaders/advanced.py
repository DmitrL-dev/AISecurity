"""
Advanced Document Loaders
=========================

Advanced loaders for complex documents with OCR, tables, and images.
Alternatives to LlamaParse.
"""

from typing import Any, Dict, List, Optional
from rlm_toolkit.loaders import Document, BaseLoader


class UnstructuredLoader(BaseLoader):
    """
    Load documents using Unstructured.io library.
    
    Supports:
    - PDF with OCR, tables, images
    - Word, PowerPoint, Excel
    - HTML, Markdown, emails
    - Automatic element detection
    
    Example:
        >>> loader = UnstructuredLoader("complex_report.pdf", strategy="hi_res")
        >>> docs = loader.load()
    """
    
    def __init__(
        self,
        path: str,
        strategy: str = "auto",  # "auto", "fast", "hi_res"
        extract_tables: bool = True,
        extract_images: bool = False,
        chunking_strategy: Optional[str] = None,  # "by_title", "by_page"
        max_characters: int = 1500,
    ):
        """
        Initialize UnstructuredLoader.
        
        Args:
            path: Path to document
            strategy: Extraction strategy
                - "auto": Choose based on document
                - "fast": Quick extraction, may miss some elements
                - "hi_res": High resolution with OCR for scanned PDFs
            extract_tables: Extract and format tables
            extract_images: Extract image captions/descriptions
            chunking_strategy: Optional chunking ("by_title", "by_page")
            max_characters: Max characters per chunk
        """
        self.path = path
        self.strategy = strategy
        self.extract_tables = extract_tables
        self.extract_images = extract_images
        self.chunking_strategy = chunking_strategy
        self.max_characters = max_characters
    
    def load(self) -> List[Document]:
        try:
            from unstructured.partition.auto import partition
            from unstructured.chunking.title import chunk_by_title
            from unstructured.chunking.basic import chunk_elements
            
            # Partition document into elements
            elements = partition(
                filename=self.path,
                strategy=self.strategy,
                include_page_breaks=True,
            )
            
            # Apply chunking if requested
            if self.chunking_strategy == "by_title":
                elements = chunk_by_title(
                    elements,
                    max_characters=self.max_characters,
                )
            elif self.chunking_strategy:
                elements = chunk_elements(
                    elements,
                    max_characters=self.max_characters,
                )
            
            # Convert to documents
            docs = []
            for i, element in enumerate(elements):
                element_type = type(element).__name__
                
                # Skip images if not requested
                if not self.extract_images and element_type == "Image":
                    continue
                
                # Format tables specially
                if element_type == "Table" and self.extract_tables:
                    content = f"[TABLE]\n{element.text}\n[/TABLE]"
                else:
                    content = element.text
                
                metadata = {
                    "source": self.path,
                    "element_type": element_type,
                    "element_index": i,
                }
                
                # Add page number if available
                if hasattr(element, "metadata") and element.metadata:
                    if hasattr(element.metadata, "page_number"):
                        metadata["page"] = element.metadata.page_number
                
                if content.strip():
                    docs.append(Document(content, metadata))
            
            return docs
            
        except ImportError:
            raise ImportError(
                "unstructured library required. Install with:\n"
                "  pip install 'unstructured[all-docs]'\n"
                "For hi_res PDF processing, also install:\n"
                "  pip install 'unstructured[pdf]'"
            )


class PDFParserLoader(BaseLoader):
    """
    Advanced PDF loader using multiple backends for best results.
    
    Tries in order:
    1. PyMuPDF (fitz) - fast, good for most PDFs
    2. pdfplumber - excellent for tables
    3. Unstructured - for OCR/scanned documents
    4. pypdf - fallback
    
    Example:
        >>> loader = PDFParserLoader("scanned_document.pdf", use_ocr=True)
        >>> docs = loader.load()
    """
    
    def __init__(
        self,
        path: str,
        use_ocr: bool = False,
        extract_tables: bool = True,
        extract_images: bool = False,
    ):
        self.path = path
        self.use_ocr = use_ocr
        self.extract_tables = extract_tables
        self.extract_images = extract_images
    
    def _try_pymupdf(self) -> Optional[List[Document]]:
        """Try PyMuPDF (fastest, high quality)."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(self.path)
            pages = []
            
            for i, page in enumerate(doc):
                text = page.get_text()
                
                # Extract tables if requested
                if self.extract_tables:
                    tables = page.find_tables()
                    for table in tables:
                        text += "\n\n[TABLE]\n"
                        for row in table.extract():
                            text += " | ".join([str(c) if c else "" for c in row]) + "\n"
                        text += "[/TABLE]\n"
                
                pages.append(Document(text, {
                    "source": self.path,
                    "page": i,
                    "total_pages": len(doc),
                    "extractor": "pymupdf",
                }))
            
            doc.close()
            return pages
        except ImportError:
            return None
        except Exception:
            return None
    
    def _try_unstructured_ocr(self) -> Optional[List[Document]]:
        """Try Unstructured with OCR for scanned documents."""
        try:
            from unstructured.partition.pdf import partition_pdf
            
            elements = partition_pdf(
                filename=self.path,
                strategy="hi_res",
                infer_table_structure=self.extract_tables,
            )
            
            return [Document(
                "\n\n".join([e.text for e in elements if e.text]),
                {"source": self.path, "extractor": "unstructured_ocr"}
            )]
        except ImportError:
            return None
        except Exception:
            return None
    
    def load(self) -> List[Document]:
        # If OCR requested, try Unstructured first
        if self.use_ocr:
            result = self._try_unstructured_ocr()
            if result:
                return result
        
        # Otherwise, try PyMuPDF first
        result = self._try_pymupdf()
        if result:
            return result
        
        # Fallback to pdfplumber (already in PDFLoader)
        from rlm_toolkit.loaders import PDFLoader
        return PDFLoader(self.path).load()


class DocumentIntelligenceLoader(BaseLoader):
    """
    Load documents using Azure Document Intelligence (Form Recognizer).
    
    Best for:
    - Complex forms
    - Invoices and receipts
    - ID documents
    - Custom document types
    
    Example:
        >>> loader = DocumentIntelligenceLoader(
        ...     "invoice.pdf",
        ...     model_id="prebuilt-invoice"
        ... )
        >>> docs = loader.load()
    """
    
    def __init__(
        self,
        path: str,
        model_id: str = "prebuilt-document",
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        import os
        self.path = path
        self.model_id = model_id
        self.endpoint = endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    def load(self) -> List[Document]:
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
            
            client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key),
            )
            
            with open(self.path, "rb") as f:
                poller = client.begin_analyze_document(self.model_id, f)
                result = poller.result()
            
            # Extract text content
            content = result.content
            
            # Extract tables
            tables_text = []
            for table in result.tables:
                table_text = "\n[TABLE]\n"
                current_row = 0
                row_cells = []
                
                for cell in table.cells:
                    if cell.row_index != current_row:
                        if row_cells:
                            table_text += " | ".join(row_cells) + "\n"
                        row_cells = []
                        current_row = cell.row_index
                    row_cells.append(cell.content)
                
                if row_cells:
                    table_text += " | ".join(row_cells) + "\n"
                table_text += "[/TABLE]\n"
                tables_text.append(table_text)
            
            full_content = content + "\n\n" + "\n".join(tables_text)
            
            return [Document(full_content, {
                "source": self.path,
                "extractor": "azure_document_intelligence",
                "model": self.model_id,
            })]
            
        except ImportError:
            raise ImportError(
                "Azure Document Intelligence SDK required:\n"
                "  pip install azure-ai-formrecognizer"
            )
