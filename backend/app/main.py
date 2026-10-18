import sys
import re
from datetime import datetime
from typing import Dict, List, Tuple
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Ensure stdout encodes safely on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .schemas import (
    IngestResponse,
    DocumentHistoryItem,
    QueryRequest,
    QueryResponse,
    Citation,
    HealthResponse,
)
from .parser import parse_document

app = FastAPI(
    title="LexisEdge Local Document Service",
    description="Air-gapped PyMuPDF + RapidOCR local backend.",
    version="1.0.0",
)

# CORS configuration for local desktop frontend
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

# In-memory document and session history stores
DOCUMENTS: Dict[str, IngestResponse] = {}
HISTORY: List[DocumentHistoryItem] = []

STOP_WORDS = {
    "what", "is", "the", "a", "an", "and", "or", "in", "on", "of", "for", "to",
    "with", "at", "by", "from", "are", "be", "this", "that", "it", "as", "any"
}

def safe_print(text: str = ""):
    """Safe print ensuring no encoding exceptions on Windows consoles."""
    try:
        print(text)
    except Exception:
        enc = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"))

def print_session_history_table():
    """Prints a clean summary table of past and current documents processed in this session."""
    safe_print("+---------------------------------------------------------------------------------------+")
    safe_print("| INGESTION SESSION HISTORY                                                             |")
    safe_print("+----------------------+------------+-------+---------+-----+------------+-------------+")
    safe_print("| Document ID          | Filename   | Pages | Digital | OCR | Characters | Ingested At |")
    safe_print("+----------------------+------------+-------+---------+-----+------------+-------------+")
    for item in HISTORY:
        fn = item.filename if len(item.filename) <= 10 else (item.filename[:8] + "..")
        chars_str = f"{item.total_chars:,}"
        safe_print(
            f"| {item.document_id:<20} | {fn:<10} | {item.total_pages:<5} | {item.digital_pages:<7} | "
            f"{item.ocr_pages:<3} | {chars_str:<10} | {item.timestamp:<11} |"
        )
    safe_print("+----------------------+------------+-------+---------+-----+------------+-------------+\n")

def retrieve_top_passages(doc: IngestResponse, query_str: str) -> Tuple[int, str]:
    """
    Performs local keyword-overlap search across parsed document pages.
    Returns (page_number, matching_quote).
    """
    query_tokens = [w.lower() for w in re.findall(r"\w+", query_str) if w.lower() not in STOP_WORDS]
    if not query_tokens:
        query_tokens = [w.lower() for w in re.findall(r"\w+", query_str)]

    best_score = -1
    best_page = 1
    best_quote = ""

    for page in doc.pages:
        text = page.text
        if not text:
            continue

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [line.strip() for line in text.split("\n") if line.strip()]

        for para in paragraphs:
            para_lower = para.lower()
            score = sum(1 for token in query_tokens if token in para_lower)
            if score > best_score:
                best_score = score
                best_page = page.page_number
                best_quote = para[:240].strip()
                if len(para) > 240:
                    best_quote += "..."

    if not best_quote and doc.pages:
        first_page = doc.pages[0]
        best_page = first_page.page_number
        best_quote = first_page.text[:200].strip() + "..."

    return best_page, best_quote

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", ocr_engine="RapidOCR Ready")

@app.post("/api/documents/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .pdf and .txt documents are supported.",
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        ingest_result = parse_document(content, file.filename)
        DOCUMENTS[ingest_result.document_id] = ingest_result

        # Update in-memory session history
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

        # Print session history table in terminal
        print_session_history_table()

        return ingest_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {e}",
        )

@app.get("/api/documents/history", response_model=List[DocumentHistoryItem])
def get_documents_history():
    """Returns the array of all past ingested documents in this session."""
    return HISTORY

@app.get("/api/documents/{document_id}", response_model=IngestResponse)
def get_document(document_id: str):
    doc = DOCUMENTS.get(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc

@app.post("/api/documents/query", response_model=QueryResponse)
def query_document(payload: QueryRequest):
    doc = DOCUMENTS.get(payload.document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{payload.document_id}' not found.",
        )

    best_page, best_quote = retrieve_top_passages(doc, payload.query)

    return QueryResponse(
        answer=f"Gemma model not yet loaded. Top matching passage retrieved from page {best_page}.",
        citations=[Citation(page=best_page, quote=best_quote)],
        explicit_terms=[],
        potential_concerns=[],
        uncertainties=[],
        model_ready=False,
    )
