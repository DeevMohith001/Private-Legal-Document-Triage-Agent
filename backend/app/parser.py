import sys
import time
import uuid
import logging
from typing import List, Optional
import pymupdf as fitz
from rapidocr_onnxruntime import RapidOCR
from .schemas import PageData, IngestResponse

# Ensure stdout encodes safely on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def safe_print(text: str = ""):
    """Safe print ensuring no encoding exceptions on Windows consoles."""
    try:
        print(text)
    except Exception:
        enc = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"))

logger = logging.getLogger("lexisedge.parser")
logging.basicConfig(level=logging.INFO, format="%(message)s")

_ocr_engine: Optional[RapidOCR] = None

def get_ocr_engine() -> RapidOCR:
    global _ocr_engine
    if _ocr_engine is None:
        logger.info("[INIT] Initializing RapidOCR ONNX runtime...")
        _ocr_engine = RapidOCR()
    return _ocr_engine

def parse_document(file_bytes: bytes, filename: str) -> IngestResponse:
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_size_kb = len(file_bytes) / 1024
    pages: List[PageData] = []
    filename_lower = filename.lower()

    print("\n" + "=" * 80)
    print(f"[*] INGESTING DOCUMENT: {filename}")
    print(f"[*] Size: {file_size_kb:.1f} KB | Document ID: {doc_id}")
    print("=" * 80)

    if filename_lower.endswith(".txt"):
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

        char_count = len(text)
        word_count = len(text.split())
        print(f"[Page 1/1] Plain text document ({char_count} characters, {word_count} words)")

        pages.append(
            PageData(
                page_number=1,
                text=text.strip(),
                ocr_applied=False,
                char_count=char_count,
            )
        )
    else:
        # PDF Document Parsing via PyMuPDF
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(pdf_doc)
        print(f"[*] Total Pages Detected: {total_pages}\n")

        ocr_engine = None

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = pdf_doc.load_page(page_idx)

            # 1. Native digital text extraction
            native_text = page.get_text().strip()
            char_count = len(native_text)

            if char_count >= 20:
                word_count = len(native_text.split())
                print(f"[Page {page_num}/{total_pages}] Digital text found ({char_count} characters, {word_count} words)")
                pages.append(
                    PageData(
                        page_number=page_num,
                        text=native_text,
                        ocr_applied=False,
                        char_count=char_count,
                    )
                )
            else:
                # 2. Negligible text -> RapidOCR Fallback
                if ocr_engine is None:
                    ocr_engine = get_ocr_engine()

                print("=" * 80)
                print(f"[OCR TRIGGERED] Page {page_num}/{total_pages}")
                print("-> Processing raster image with RapidOCR...")

                start_time = time.perf_counter()
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")

                ocr_results, _ = ocr_engine(img_bytes)
                elapsed = time.perf_counter() - start_time

                if ocr_results:
                    extracted_lines = [item[1] for item in ocr_results if len(item) > 1 and item[1]]
                    ocr_text = "\n".join(extracted_lines).strip()
                    block_count = len(ocr_results)
                else:
                    ocr_text = ""
                    block_count = 0

                sample_text = (ocr_text[:120] + "...") if len(ocr_text) > 120 else (ocr_text or "[No text detected]")
                print(f"-> OCR Completed in {elapsed:.2f}s | Detected {block_count} text blocks")
                print(f'-> Sample extracted: "{sample_text}"')
                print("=" * 80)

                pages.append(
                    PageData(
                        page_number=page_num,
                        text=ocr_text,
                        ocr_applied=True,
                        char_count=len(ocr_text),
                    )
                )

        pdf_doc.close()

    total_pages = len(pages)
    ocr_count = sum(1 for p in pages if p.ocr_applied)
    digital_count = total_pages - ocr_count

    # Ready-to-Feed LLM Context Payload Output
    safe_print("\n" + "=" * 80)
    safe_print(">>> LLM CONTEXT PAYLOAD READY (Ready to feed to Local Gemma)")
    safe_print("=" * 80)
    safe_print("<<<DOCUMENT_METADATA>>>")
    safe_print(f"Document ID : {doc_id}")
    safe_print(f"Filename    : {filename}")
    safe_print(f"Total Pages : {total_pages}")
    safe_print(f"Parse Mode  : {digital_count} Native / {ocr_count} RapidOCR\n")
    safe_print("<<<EXTRACTED_CONTENT_BLOCKS>>>")
    for p in pages:
        safe_print(f"--- [PAGE {p.page_number}] ---")
        safe_print(p.text if p.text else "[EMPTY PAGE]")
        safe_print()
    safe_print("<<<END_CONTEXT_PAYLOAD>>>")
    safe_print("=" * 80 + "\n")

    return IngestResponse(
        document_id=doc_id,
        filename=filename,
        total_pages=total_pages,
        pages=pages,
    )
