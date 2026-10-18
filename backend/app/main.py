"""
LexisEdge Local Document Service — Air-Gapped PyMuPDF + RapidOCR + Gemma 3n Backend.
Privacy-First, On-Device Legal Document Triage.
"""

import sys
import logging
from datetime import datetime
from typing import Dict, List
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Ensure stdout encodes safely on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Configure logging with zero document content leakage
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lexisedge.api")

from .schemas import (
    IngestResponse,
    DocumentHistoryItem,
    QueryRequest,
    QueryResponse,
    HealthResponse,
)
from .parser import parse_document
from .retrieval import retrieve_relevant_passages
from .inference import run_local_legal_triage, is_model_available

app = FastAPI(
    title="LexisEdge Local Legal Document Service",
    description="Privacy-preserving on-device document triage with PyMuPDF, RapidOCR, and Gemma 3n.",
    version="1.0.0",
)

# CORS configuration strictly for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory document and session history stores (ephemeral, zero remote sync)
DOCUMENTS: Dict[str, IngestResponse] = {}
HISTORY: List[DocumentHistoryItem] = []

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint measuring OCR and local model readiness."""
    model_ready = is_model_available()
    engine_status = "RapidOCR Ready + Gemma 3n Ready" if model_ready else "RapidOCR Ready (Model Pending)"
    return HealthResponse(
        status="ok",
        ocr_engine=engine_status,
    )

@app.post("/api/documents/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingests and parses a PDF or TXT file locally on-device.
    Validates file integrity and rejects corrupted, empty, or encrypted files.
    Never creates fake document records on failure.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .pdf and .txt documents are supported.",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file streams: {e}",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        ingest_result = parse_document(content, file.filename)
    except ValueError as ve:
        # Expected validation error (e.g. encrypted PDF, empty text, malformed file)
        logger.warning(f"[INGEST REJECTED] {file.filename}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"[INGEST FAILED] {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document parsing failed: {e}",
        )

    # Store parsed document in memory
    DOCUMENTS[ingest_result.document_id] = ingest_result

    # Update session history metadata (strictly structural metadata, no sensitive text)
    ocr_count = sum(1 for p in ingest_result.pages if p.ocr_applied)
    digital_count = ingest_result.total_pages - ocr_count
    total_chars = sum(p.char_count for p in ingest_result.pages)
    timestamp = datetime.now().strftime("%H:%M:%S")

    history_item = DocumentHistoryItem(
        document_id=ingest_result.document_id,
        filename=ingest_result.filename,
        total_pages=ingest_result.total_pages,
        digital_pages=digital_count,
        ocr_pages=ocr_count,
        timestamp=timestamp,
        total_chars=total_chars,
    )
    HISTORY.append(history_item)

    return ingest_result

@app.get("/api/documents/history", response_model=List[DocumentHistoryItem])
def get_documents_history():
    """Returns the array of past ingested documents in this session."""
    return HISTORY

@app.get("/api/documents/{document_id}", response_model=IngestResponse)
def get_document(document_id: str):
    """Retrieves parsed document pages by document ID."""
    doc = DOCUMENTS.get(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc

@app.post("/api/documents/query", response_model=QueryResponse)
def query_document(payload: QueryRequest):
    """
    Executes grounded legal document triage using local passage retrieval
    and local Gemma 3n inference.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty.",
        )

    doc = DOCUMENTS.get(payload.document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{payload.document_id}' not found.",
        )

    # 1. Local multi-passage retrieval with domain weighting
    top_chunks, has_sufficient_evidence = retrieve_relevant_passages(
        doc, payload.query, top_k=4
    )

    # 2. Local Gemma 3n inference with safety escalation and prompt isolation
    try:
        triage_response = run_local_legal_triage(
            doc=doc,
            query=payload.query,
            retrieved_chunks=top_chunks,
            has_sufficient_evidence=has_sufficient_evidence,
        )
        return triage_response
    except Exception as e:
        logger.error(f"[QUERY ERROR] Triage execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Legal triage analysis failed: {e}",
        )
