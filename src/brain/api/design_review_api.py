"""
AI Design Review API

REST endpoints for design document security review.

Generated: 2026-01-08
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..design_review import (
    review_text,
    review_documents,
    DesignReviewResult,
    RiskCategory,
)

router = APIRouter(prefix="/design-review", tags=["design-review"])


class TextReviewRequest(BaseModel):
    text: str
    source: str = "document"


class DocumentReview(BaseModel):
    name: str
    content: str


class DocumentsReviewRequest(BaseModel):
    documents: List[DocumentReview]


@router.get("/risk-categories")
async def list_risk_categories():
    """List all risk categories that are detected."""
    return {
        "categories": [
            {
                "id": "rag_poisoning",
                "name": "RAG Poisoning",
                "description": "Risks related to RAG document ingestion and embedding",
                "owasp": ["LLM03", "ASI04"]
            },
            {
                "id": "prompt_injection",
                "name": "Prompt Injection",
                "description": "Direct and indirect prompt injection vectors",
                "owasp": ["LLM01"]
            },
            {
                "id": "mcp_abuse",
                "name": "MCP/Tool Abuse",
                "description": "Risks from tool and API usage patterns",
                "owasp": ["LLM07", "ASI05", "ASI07"]
            },
            {
                "id": "agent_loop",
                "name": "Agent Loops",
                "description": "Agentic architecture risks including loops and goal drift",
                "owasp": ["ASI01", "ASI06", "ASI08"]
            },
            {
                "id": "data_leakage",
                "name": "Data Leakage",
                "description": "Sensitive data exposure risks",
                "owasp": ["LLM06", "ASI07"]
            },
            {
                "id": "supply_chain",
                "name": "Supply Chain",
                "description": "Model and dependency security risks",
                "owasp": ["LLM05", "ASI09"]
            }
        ]
    }


@router.post("/text")
async def review_text_endpoint(request: TextReviewRequest):
    """Review a single text document for AI security risks."""
    risks = review_text(request.text, request.source)
    
    return {
        "source": request.source,
        "risk_count": len(risks),
        "risks": [
            {
                "id": r.id,
                "category": r.category.value,
                "severity": r.severity.value,
                "title": r.title,
                "description": r.description,
                "location": r.location,
                "recommendation": r.recommendation,
                "owasp_mapping": r.owasp_mapping
            }
            for r in risks
        ]
    }


@router.post("/documents")
async def review_documents_endpoint(request: DocumentsReviewRequest):
    """Review multiple documents for AI security risks."""
    docs = [{"name": d.name, "content": d.content} for d in request.documents]
    result = review_documents(docs)
    return result.to_dict()


@router.post("/upload")
async def review_uploaded_files(files: List[UploadFile] = File(...)):
    """Review uploaded files for AI security risks."""
    documents = []
    
    for file in files:
        # Read file content
        content = await file.read()
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} is not a valid text file"
            )
        
        documents.append({
            "name": file.filename,
            "content": text
        })
    
    result = review_documents(documents)
    return result.to_dict()


@router.get("/example")
async def get_example_review():
    """Get an example design review to understand the output format."""
    example_doc = """
    # AI Assistant Architecture
    
    ## Overview
    This is an autonomous AI agent that uses RAG for document retrieval
    and MCP tools for file system access and shell command execution.
    
    ## Components
    - Vector database for embedding storage
    - Document ingestion from user uploads
    - File read/write capabilities
    - Shell command execution for DevOps tasks
    
    ## Data Flow
    User prompts are augmented with PII from the customer database
    and responses are cached for performance.
    """
    
    result = review_documents([{"name": "example_arch.md", "content": example_doc}])
    
    return {
        "example_document": "See 'input_document' field",
        "input_document": example_doc,
        "review_result": result.to_dict()
    }
