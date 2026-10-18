"""
Tests for Passage Retrieval, Provenance, Page Attribution, and Citation Verification.
"""

import pytest
from backend.app.parser import parse_document
from backend.app.retrieval import retrieve_relevant_passages, chunk_page_text
from backend.app.citations import (
    verify_single_citation,
    ground_citations_from_retrieval,
    Citation,
)

def test_passage_retrieval_for_answered_question(sample_lease_pdf):
    """Test 7: Retrieve passages for a question directly answered in the text."""
    doc = parse_document(sample_lease_pdf, "contract.pdf")
    query = "What is the notice period for termination?"
    chunks, has_evidence = retrieve_relevant_passages(doc, query, top_k=3)
    
    assert has_evidence is True
    assert len(chunks) > 0
    # Top chunk should mention termination and 30 days notice
    top_text = chunks[0].text.lower()
    assert "terminate" in top_text or "notice" in top_text or "30 days" in top_text

def test_correct_page_attribution(sample_lease_pdf):
    """Test 8: Ensure retrieved chunks accurately attribute content to page 1 vs page 2."""
    doc = parse_document(sample_lease_pdf, "contract.pdf")
    
    # Query answered strictly on Page 1 (parties/termination)
    q1 = "Who is the Tenant and what is the Pine Avenue premises address?"
    chunks1, _ = retrieve_relevant_passages(doc, q1, top_k=1)
    assert chunks1[0].page_number == 1
    
    # Query answered strictly on Page 2 (security deposit / governing law)
    q2 = "What law governs this agreement and what is the deposit?"
    chunks2, _ = retrieve_relevant_passages(doc, q2, top_k=1)
    assert chunks2[0].page_number == 2

def test_exact_quotation_validation(sample_lease_pdf):
    """Test 9: Verifies genuine verbatim quotation from source text."""
    doc = parse_document(sample_lease_pdf, "contract.pdf")
    
    valid_citation = Citation(
        page=1,
        quote="Either party may terminate with 30 days written notice."
    )
    verified = verify_single_citation(valid_citation, doc)
    assert verified is not None
    assert verified.page == 1
    assert "30 days written notice" in verified.quote

def test_question_absent_from_document(sample_lease_pdf):
    """Test 10: Topic completely absent from the document returns insufficient evidence."""
    doc = parse_document(sample_lease_pdf, "contract.pdf")
    query = "What are the equity stock options and vesting schedule for employees?"
    chunks, has_evidence = retrieve_relevant_passages(doc, query, min_score_threshold=1.5)
    
    # Document contains no mention of stock options or vesting
    grounded_citations = ground_citations_from_retrieval(
        model_citations=[],
        retrieved_chunks=chunks,
        doc=doc,
        has_sufficient_evidence=has_evidence,
    )
    assert grounded_citations == []

def test_fabricated_citation_rejected(sample_lease_pdf):
    """Test 13: A fabricated or hallucinated quote is strictly rejected."""
    doc = parse_document(sample_lease_pdf, "contract.pdf")
    
    fake_citation = Citation(
        page=1,
        quote="The landlord shall pay a penalty of $50,000 upon default."
    )
    verified = verify_single_citation(fake_citation, doc)
    assert verified is None, "Fabricated quote must be rejected!"

def test_misattributed_page_number_corrected(sample_lease_pdf):
    """Test 8 & 13: A quote that is on Page 2 but claimed to be Page 1 gets corrected."""
    doc = parse_document(sample_lease_pdf, "contract.pdf")
    
    # Text actually on Page 2
    misattributed_citation = Citation(
        page=1,  # Claimed page 1
        quote="A security deposit of $1,800 is held in escrow."
    )
    corrected = verify_single_citation(misattributed_citation, doc)
    assert corrected is not None
    assert corrected.page == 2  # Must be corrected to page 2!
