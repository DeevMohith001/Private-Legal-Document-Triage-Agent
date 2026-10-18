"""
Tests for Document Parsing, Validation, OCR Fallback, and Log Privacy.
"""

import logging
import pytest
from backend.app.parser import parse_document

def test_successful_txt_ingestion(sample_lease_txt):
    """Test 2: Successful TXT ingestion with page structure."""
    res = parse_document(sample_lease_txt, "lease_sample.txt")
    assert res.document_id.startswith("doc_")
    assert res.filename == "lease_sample.txt"
    assert res.total_pages >= 1
    assert len(res.pages) >= 1
    assert "RESIDENTIAL LEASE AGREEMENT" in res.pages[0].text
    assert res.pages[0].char_count > 100
    assert not res.pages[0].ocr_applied

def test_successful_pdf_ingestion(sample_lease_pdf):
    """Test 1: Successful PDF ingestion with digital text preservation."""
    res = parse_document(sample_lease_pdf, "contract.pdf")
    assert res.document_id.startswith("doc_")
    assert res.total_pages == 2
    assert len(res.pages) == 2
    assert res.pages[0].page_number == 1
    assert "RESIDENTIAL LEASE AGREEMENT - PAGE 1" in res.pages[0].text
    assert res.pages[1].page_number == 2
    assert "RESIDENTIAL LEASE AGREEMENT - PAGE 2" in res.pages[1].text
    assert not res.pages[0].ocr_applied
    assert not res.pages[1].ocr_applied

def test_empty_file_handling():
    """Test 3: Empty file must be cleanly rejected with descriptive error."""
    with pytest.raises(ValueError, match="empty"):
        parse_document(b"", "empty.pdf")

def test_corrupt_file_handling():
    """Test 3: Corrupt or malformed PDF raises an error, never silent success."""
    corrupt_bytes = b"%PDF-1.4 completely broken content not a valid stream"
    with pytest.raises(ValueError, match="Malformed or corrupt"):
        parse_document(corrupt_bytes, "broken.pdf")

def test_encrypted_pdf_handling(encrypted_pdf):
    """Test 4: Password-protected PDF must be detected and rejected safely."""
    with pytest.raises(ValueError, match="Password-protected"):
        parse_document(encrypted_pdf, "encrypted.pdf")

def test_ocr_fallback_handling(scanned_ocr_pdf):
    """Test 5: Image-based scanned PDF triggers local RapidOCR fallback."""
    res = parse_document(scanned_ocr_pdf, "scanned_notice.pdf")
    assert res.total_pages == 1
    # Page must have OCR flag set to True
    assert res.pages[0].ocr_applied is True
    # RapidOCR should detect the text from the rendered image
    extracted = res.pages[0].text.upper()
    assert "NOTICE" in extracted or "VACATE" in extracted

def test_empty_extracted_text_handling():
    """Test 6: PDF with blank pages and no text raises clean error."""
    import pymupdf as fitz
    doc = fitz.open()
    doc.new_page()  # completely blank page
    blank_bytes = doc.tobytes()
    doc.close()

    with pytest.raises(ValueError, match="no extractable text"):
        parse_document(blank_bytes, "blank.pdf")

def test_no_sensitive_document_content_in_logs(sample_lease_pdf, caplog):
    """Test 19: Privacy guarantee - document content is NOT emitted to logs."""
    caplog.set_level(logging.DEBUG)
    res = parse_document(sample_lease_pdf, "private_agreement.pdf")
    
    # Verify that private text does not appear in captured log records
    for record in caplog.records:
        assert "Jane Smith" not in record.message
        assert "789 Pine Avenue" not in record.message
        assert "security deposit of $1,800" not in record.message
