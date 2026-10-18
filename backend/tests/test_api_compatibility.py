"""
Tests for FastAPI Endpoints and Strict Compatibility with Existing Frontend API Client.
"""

import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, DOCUMENTS, HISTORY

@pytest.fixture
def client():
    # Clear in-memory state before each test
    DOCUMENTS.clear()
    HISTORY.clear()
    return TestClient(app)

def test_api_health_check(client):
    """Verifies GET /api/health response format expected by checkBackendPing in frontend."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ocr_engine" in data
    assert "RapidOCR" in data["ocr_engine"]

def test_api_ingest_txt_file(client, sample_lease_txt):
    """Verifies POST /api/documents/ingest with plain text."""
    files = {"file": ("lease.txt", sample_lease_txt, "text/plain")}
    response = client.post("/api/documents/ingest", files=files)
    assert response.status_code == 200
    data = response.json()
    
    # Check exact contract expected by frontend IngestResponse
    assert "document_id" in data
    assert data["filename"] == "lease.txt"
    assert data["total_pages"] >= 1
    assert isinstance(data["pages"], list)
    assert len(data["pages"]) >= 1
    p0 = data["pages"][0]
    assert "page_number" in p0
    assert "text" in p0
    assert "ocr_applied" in p0
    assert "char_count" in p0

def test_api_ingest_pdf_file(client, sample_lease_pdf):
    """Verifies POST /api/documents/ingest with PDF."""
    files = {"file": ("agreement.pdf", sample_lease_pdf, "application/pdf")}
    response = client.post("/api/documents/ingest", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_pages"] == 2
    assert len(data["pages"]) == 2

def test_api_ingest_empty_file_rejected(client):
    """Test 18: No fake success on empty file upload."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    response = client.post("/api/documents/ingest", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
    # Confirm no fake document record was created in store
    assert len(DOCUMENTS) == 0

def test_api_ingest_encrypted_file_rejected(client, encrypted_pdf):
    """Test 18: Encrypted PDF returns clean 400 Bad Request, no fake document created."""
    files = {"file": ("locked.pdf", encrypted_pdf, "application/pdf")}
    response = client.post("/api/documents/ingest", files=files)
    assert response.status_code == 400
    assert "password-protected" in response.json()["detail"].lower()
    assert len(DOCUMENTS) == 0

def test_api_get_document_by_id(client, sample_lease_pdf):
    """Verifies GET /api/documents/{document_id}."""
    files = {"file": ("agreement.pdf", sample_lease_pdf, "application/pdf")}
    ingest_res = client.post("/api/documents/ingest", files=files).json()
    doc_id = ingest_res["document_id"]

    response = client.get(f"/api/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["document_id"] == doc_id

    # Non-existent document returns 404
    missing_res = client.get("/api/documents/non_existent_123")
    assert missing_res.status_code == 404

def test_api_documents_history(client, sample_lease_pdf):
    """Verifies GET /api/documents/history."""
    files = {"file": ("history_test.pdf", sample_lease_pdf, "application/pdf")}
    client.post("/api/documents/ingest", files=files)

    response = client.get("/api/documents/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    item = history[0]
    assert item["filename"] == "history_test.pdf"
    assert item["total_pages"] == 2
    assert "digital_pages" in item
    assert "ocr_pages" in item
    assert "timestamp" in item

def test_api_query_document(client, sample_lease_pdf):
    """Verifies POST /api/documents/query matches frontend QueryResponse contract."""
    files = {"file": ("agreement.pdf", sample_lease_pdf, "application/pdf")}
    ingest_res = client.post("/api/documents/ingest", files=files).json()
    doc_id = ingest_res["document_id"]

    payload = {
        "document_id": doc_id,
        "query": "What is the notice period for lease termination?"
    }
    response = client.post("/api/documents/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify exact QueryResponse schema fields expected by frontend ResultView
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert "explicit_terms" in data
    assert "potential_concerns" in data
    assert "uncertainties" in data
    assert "model_ready" in data

    if len(data["citations"]) > 0:
        c0 = data["citations"][0]
        assert "page" in c0
        assert "quote" in c0
        assert isinstance(c0["page"], int)
        assert isinstance(c0["quote"], str)
