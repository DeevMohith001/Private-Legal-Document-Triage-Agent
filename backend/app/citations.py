"""
Citation validation and ground-truth verification engine.
Ensures every citation strictly corresponds to an actual document page
and verbatim source text. Corrects or rejects hallucinated quotes.
"""

import re
from typing import List, Optional
from .schemas import Citation, IngestResponse
from .retrieval import RetrievedChunk

def normalize_text_for_matching(text: str) -> str:
    """
    Normalizes typographic variances (smart quotes, em-dashes, irregular whitespace)
    for reliable quotation matching while preserving verbatim integrity.
    """
    if not text:
        return ""
    # Replace curly quotes and apostrophes
    s = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("—", "-").replace("–", "-")
    # Collapse multiple whitespaces and linebreaks into single spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()

def extract_verbatim_slice(needle: str, haystack: str) -> Optional[str]:
    """
    Locates the needle inside haystack using normalized comparison,
    and returns the exact verbatim slice from the original haystack.
    """
    norm_needle = normalize_text_for_matching(needle)
    if not norm_needle or len(norm_needle) < 10:
        return None

    norm_haystack = normalize_text_for_matching(haystack)
    if norm_needle in norm_haystack:
        # Check if direct verbatim match exists
        clean_needle = needle.strip().strip('"').strip("'")
        if clean_needle in haystack:
            return clean_needle

        # Search for first and last token in original haystack
        tokens = needle.split()
        if len(tokens) >= 3:
            first_three = " ".join(tokens[:3])
            last_three = " ".join(tokens[-3:])
            pos_start = haystack.lower().find(first_three.lower())
            if pos_start != -1:
                pos_end = haystack.lower().find(last_three.lower(), pos_start)
                if pos_end != -1:
                    return haystack[pos_start : pos_end + len(last_three)].strip()

        # Fallback to returning clean needle if normalized found
        return clean_needle

    # If needle is longer than 50 chars, check if a significant prefix matches
    if len(norm_needle) > 50:
        prefix = norm_needle[:40]
        if prefix in norm_haystack:
            words = needle.split()[:10]
            prefix_orig = " ".join(words)
            idx = haystack.lower().find(prefix_orig.lower())
            if idx != -1:
                end_idx = min(len(haystack), idx + len(needle) + 30)
                return haystack[idx:end_idx].strip()

    return None

def verify_single_citation(
    citation: Citation,
    doc: IngestResponse
) -> Optional[Citation]:
    """
    Verifies a citation against the stored document pages.
    - Validates page boundary.
    - Validates verbatim quote presence.
    - Corrects page attribution if quote exists on another page.
    - Rejects if quote does not exist anywhere in document.
    """
    if not citation.quote or len(citation.quote.strip()) < 8:
        return None

    clean_quote = citation.quote.strip().strip('"').strip("'")

    # 1. Check stated page first
    target_page = next((p for p in doc.pages if p.page_number == citation.page), None)
    if target_page and target_page.text:
        verbatim = extract_verbatim_slice(clean_quote, target_page.text)
        if verbatim:
            # Bound quote length for crisp UI card display while preserving exact verbatim source text
            display_quote = verbatim[:220].strip()
            return Citation(page=citation.page, quote=display_quote)

    # 2. Check all other pages to correct misattributed page numbers
    for page in doc.pages:
        if page.page_number == citation.page or not page.text:
            continue
        verbatim = extract_verbatim_slice(clean_quote, page.text)
        if verbatim:
            display_quote = verbatim[:220].strip()
            if len(verbatim) > 220:
                display_quote += "..."
            # Corrected to actual page where text resides
            return Citation(page=page.page_number, quote=display_quote)

    # 3. Not found anywhere -> rejected as unverified hallucination
    return None

def ground_citations_from_retrieval(
    model_citations: List[Citation],
    retrieved_chunks: List[RetrievedChunk],
    doc: IngestResponse,
    has_sufficient_evidence: bool,
    max_citations: int = 3,
) -> List[Citation]:
    """
    Constructs a verified, deduplicated list of citations.
    Prioritizes verified model citations; falls back to top retrieved source chunks.
    If the document lacks sufficient evidence, returns an empty list.
    """
    if not has_sufficient_evidence or not retrieved_chunks:
        return []

    verified_list: List[Citation] = []
    seen_quotes = set()

    # 1. Verify model-provided citations
    for mc in model_citations:
        verified = verify_single_citation(mc, doc)
        if verified:
            q_key = normalize_text_for_matching(verified.quote[:50])
            if q_key not in seen_quotes:
                seen_quotes.add(q_key)
                verified_list.append(verified)
                if len(verified_list) >= max_citations:
                    break

    # 2. If model citations were invalid or insufficient, ground with top retrieved chunks
    if not verified_list and retrieved_chunks:
        for chunk in retrieved_chunks:
            if not chunk.text or chunk.score < 0.5:
                continue
            chunk_page = next((p for p in doc.pages if p.page_number == chunk.page_number), None)
            if not chunk_page:
                continue

            clean_text = chunk.text.strip()
            # If longer than 220 chars, slice at clean sentence/space boundary
            if len(clean_text) > 220:
                cut_idx = clean_text[:220].rfind(". ")
                if cut_idx != -1 and cut_idx > 60:
                    quote_candidate = clean_text[:cut_idx + 1].strip()
                else:
                    cut_space = clean_text[:220].rfind(" ")
                    quote_candidate = clean_text[:cut_space].strip() if cut_space > 60 else clean_text[:220].strip()
            else:
                quote_candidate = clean_text

            q_key = normalize_text_for_matching(quote_candidate[:50])
            if q_key not in seen_quotes:
                seen_quotes.add(q_key)
                verified_list.append(Citation(page=chunk.page_number, quote=quote_candidate))
                if len(verified_list) >= max_citations:
                    break

    return verified_list
