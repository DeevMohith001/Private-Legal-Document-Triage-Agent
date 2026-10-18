from typing import List
from pydantic import BaseModel, Field

class PageData(BaseModel):
    page_number: int
    text: str
    ocr_applied: bool
    char_count: int

class IngestResponse(BaseModel):
    document_id: str
    filename: str
    total_pages: int
    pages: List[PageData]

class DocumentHistoryItem(BaseModel):
    document_id: str
    filename: str
    total_pages: int
    digital_pages: int
    ocr_pages: int
    timestamp: str
    total_chars: int

class QueryRequest(BaseModel):
    document_id: str
    query: str

class Citation(BaseModel):
    page: int
    quote: str

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    explicit_terms: List[str] = Field(default_factory=list)
    potential_concerns: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    model_ready: bool = False

class HealthResponse(BaseModel):
    status: str = "ok"
    ocr_engine: str = "RapidOCR Ready"
