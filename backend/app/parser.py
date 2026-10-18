"""
Local document ingestion pipeline with PyMuPDF and RapidOCR fallback.
Privacy-First: Zero document content is emitted to console or logs.
"""

import sys
import uuid
import logging
from typing import List, Optional, Any
import pymupdf as fitz
from .schemas import PageData, IngestResponse

# Graceful RapidOCR import to ensure module can be imported even if OCR dependencies are pending
try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPID_OCR = True
except ImportError:
    RapidOCR = None  # type: ignore
    HAS_RAPID_OCR = False

# Logger setup with no sensitive data leaking
logger = logging.getLogger("lexisedge.parser")

_ocr_engine: Optional[Any] = None

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
MAX_PAGE_COUNT = 100                    # 100 pages max to prevent resource exhaustion
MIN_CHAR_COUNT_FOR_DIGITAL = 20        # Threshold under which OCR fallback triggers
TXT_CHUNK_LINE_COUNT = 50              # Chunks text files into 50-line pages (matches frontend Viewer.tsx)

def get_ocr_engine() -> Any:
    """Lazy initialization of local RapidOCR ONNX runtime."""
    global _ocr_engine
    if not HAS_RAPID_OCR:
        raise RuntimeError(
            "RapidOCR is not installed in the active Python environment. "
            "To enable OCR for scanned documents, install rapidocr-onnxruntime."
        )
    if _ocr_engine is None:
        logger.info("[OCR] Initializing RapidOCR ONNX engine locally...")
        _ocr_engine = RapidOCR()
    return _ocr_engine

def parse_document(file_bytes: bytes, filename: str) -> IngestResponse:
    """
    Parses a PDF or plain text document on-device.
    Validates file integrity, page counts, and encryption.
    Performs OCR fallback for scanned or image-based pages.
    Guarantees no document text is logged or leaked.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size ({len(file_bytes) / (1024*1024):.1f} MB) exceeds maximum allowed limit (25 MB)."
        )

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    filename_lower = filename.lower()
    pages: List[PageData] = []

    if filename_lower.endswith(".txt"):
        try:
            full_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            full_text = file_bytes.decode("latin-1", errors="replace")

        stripped_full = full_text.strip()
        if not stripped_full:
            raise ValueError("Plain text document contains no extractable content.")

        # Chunk text file into 50-line pages to match frontend Viewer.tsx pagination
        raw_lines = full_text.splitlines()
        if not raw_lines:
            raw_lines = [full_text]

        chunk_size = TXT_CHUNK_LINE_COUNT
        page_chunks = [
            "\n".join(raw_lines[i : i + chunk_size])
            for i in range(0, len(raw_lines), chunk_size)
        ]
        if not page_chunks:
            page_chunks = [full_text]

        for idx, chunk_text in enumerate(page_chunks):
            p_num = idx + 1
            pages.append(
                PageData(
                    page_number=p_num,
                    text=chunk_text,
                    ocr_applied=False,
                    char_count=len(chunk_text),
                )
            )

    elif filename_lower.endswith(".pdf"):
        try:
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Malformed or corrupt PDF document: {e}")

        try:
            if pdf_doc.is_encrypted or pdf_doc.needs_pass:
                raise ValueError("Password-protected PDF files cannot be processed without authorization.")

            total_pdf_pages = len(pdf_doc)
            if total_pdf_pages == 0:
                raise ValueError("PDF document contains no pages.")

            if total_pdf_pages > MAX_PAGE_COUNT:
                raise ValueError(
                    f"PDF page count ({total_pdf_pages}) exceeds maximum allowed limit ({MAX_PAGE_COUNT} pages)."
                )

            ocr_engine = None

            for page_idx in range(total_pdf_pages):
                page_num = page_idx + 1
                try:
                    page = pdf_doc.load_page(page_idx)
                except Exception as e:
                    logger.warning(f"[PARSE] Error loading PDF page {page_num}: {e}")
                    pages.append(
                        PageData(
                            page_number=page_num,
                            text="",
                            ocr_applied=False,
                            char_count=0,
                        )
                    )
                    continue

                # 1. Native digital text extraction
                native_text = page.get_text().strip()
                char_count = len(native_text)

                if char_count >= MIN_CHAR_COUNT_FOR_DIGITAL:
                    pages.append(
                        PageData(
                            page_number=page_num,
                            text=native_text,
                            ocr_applied=False,
                            char_count=char_count,
                        )
                    )
                else:
                    # 2. Negligible native text -> RapidOCR Fallback
                    if ocr_engine is None:
                        ocr_engine = get_ocr_engine()

                    try:
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        ocr_results, _ = ocr_engine(img_bytes)

                        if ocr_results:
                            extracted_lines = [
                                item[1] for item in ocr_results if len(item) > 1 and item[1]
                            ]
                            ocr_text = "\n".join(extracted_lines).strip()
                        else:
                            ocr_text = ""
                    except Exception as ocr_err:
                        logger.warning(f"[OCR] OCR processing error on page {page_num}: {ocr_err}")
                        ocr_text = ""

                    pages.append(
                        PageData(
                            page_number=page_num,
                            text=ocr_text,
                            ocr_applied=True,
                            char_count=len(ocr_text),
                        )
                    )
        finally:
            pdf_doc.close()

    else:
        raise ValueError("Unsupported file format. Only .pdf and .txt documents are supported.")

    # Validate that document has at least some extractable characters
    total_chars = sum(p.char_count for p in pages)
    if total_chars == 0:
        raise ValueError(
            "Document parsing produced no extractable text. Document appears empty or unreadable."
        )

    # Privacy-conscious logging: Log only structural metadata, NEVER document text
    ocr_count = sum(1 for p in pages if p.ocr_applied)
    digital_count = len(pages) - ocr_count
    logger.info(
        f"[INGEST COMPLETE] ID: {doc_id} | Pages: {len(pages)} ({digital_count} digital, {ocr_count} OCR) | Characters: {total_chars:,}"
    )

    return IngestResponse(
        document_id=doc_id,
        filename=filename,
        total_pages=len(pages),
        pages=pages,
    )
