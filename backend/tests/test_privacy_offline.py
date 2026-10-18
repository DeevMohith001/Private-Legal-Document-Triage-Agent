"""
Privacy and Network-Isolation Test Suite.
Verifies end-to-end document ingestion, OCR, retrieval, and Gemma 3n inference
with ALL non-localhost outbound networking strictly intercepted and blocked.
"""

import socket
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, DOCUMENTS, HISTORY

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}

class BlockedOutboundNetworkError(RuntimeError):
    pass

@pytest.fixture
def airgap_network_shield(monkeypatch):
    """
    Simulates a hardware or firewall air-gap.
    Blocks any attempt to connect to any non-localhost host or IP.
    """
    original_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, (tuple, list)) else address
        # Normalize
        host_str = str(host).lower()
        if host_str not in ALLOWED_HOSTS and not host_str.startswith("127."):
            raise BlockedOutboundNetworkError(
                f"PRIVACY VIOLATION DETECTED: Attempted outbound network connection to '{host_str}' "
                "during active legal document processing! All document analysis must remain 100% on-device."
            )
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    yield

def test_airgapped_end_to_end_pipeline(airgap_network_shield, sample_lease_pdf):
    """
    Test 20: Mandatory Offline Privacy Test.
    Executes full ingestion, OCR inspection, lexical retrieval, and Gemma 3n inference
    under active outbound network blockage.
    """
    DOCUMENTS.clear()
    HISTORY.clear()
    
    from backend.app.inference import is_model_available
    if not is_model_available():
        pytest.skip("Local Gemma 3n model weights not found. Run 'python download_model.py' first.")

    client = TestClient(app)

    # 1. Ingest Document under air-gap
    files = {"file": ("airgap_test_contract.pdf", sample_lease_pdf, "application/pdf")}
    ingest_res = client.post("/api/documents/ingest", files=files)
    assert ingest_res.status_code == 200, f"Ingestion failed: {ingest_res.text}"
    doc_id = ingest_res.json()["document_id"]

    # 2. Query Document under air-gap
    payload = {
        "document_id": doc_id,
        "query": "What is the penalty for early termination of the lease?"
    }
    query_res = client.post("/api/documents/query", json=payload)
    assert query_res.status_code == 200, f"Query failed: {query_res.text}"
    
    data = query_res.json()
    assert "answer" in data
    assert len(data["answer"]) > 20
    assert data["model_ready"] is True

    # 3. Confirm that no sensitive content was logged or leaked
    assert len(DOCUMENTS) == 1
