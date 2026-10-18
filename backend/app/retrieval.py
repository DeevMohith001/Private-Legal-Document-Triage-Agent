"""
Local passage retrieval and evidence grounding engine.
Chunks documents at paragraph and sentence boundaries with full provenance.
Uses a fast, deterministic BM25-style scoring algorithm with legal token weighting.
"""

import re
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from .schemas import IngestResponse, PageData

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}

# Domain-specific legal terminology expansion for contract triage
LEGAL_SYNONYM_MAP: Dict[str, List[str]] = {
    "termination": ["terminate", "terminating", "cancellation", "cancel", "rescind", "expiry", "expire", "notice"],
    "notice": ["notice", "written notice", "days", "advance notice", "calendar days", "prior to"],
    "liability": ["liability", "liable", "indemnity", "indemnify", "damages", "losses", "harmless", "breach"],
    "indemnity": ["indemnity", "indemnify", "hold harmless", "defend", "damages", "losses"],
    "renewal": ["renewal", "renew", "automatic renewal", "extension", "extend", "rolling", "subsequent term"],
    "penalty": ["penalty", "fine", "liquidated damages", "interest", "forfeit", "forfeiture", "charge"],
    "payment": ["rent", "fee", "payment", "salary", "remuneration", "compensation", "deposit", "invoice"],
    "confidential": ["confidential", "confidentiality", "proprietary", "non-disclosure", "nda", "trade secret"],
    "jurisdiction": ["jurisdiction", "governing law", "dispute", "arbitration", "courts", "venue"],
    "address": ["address", "premises", "property", "location", "situated", "street", "avenue", "suite"],
    "parties": ["parties", "landlord", "tenant", "lessor", "lessee", "employer", "employee", "contractor"],
}

@dataclass
class RetrievedChunk:
    chunk_id: str
    page_number: int
    text: str
    score: float

def tokenize(text: str) -> List[str]:
    """Extracts lowercased alphanumeric tokens from text."""
    return [w.lower() for w in re.findall(r"\b[A-Za-z0-9_'-]+\b", text)]

def chunk_page_text(page_num: int, text: str) -> List[RetrievedChunk]:
    """
    Chunks a single page text into semantic paragraphs and clauses.
    Preserves exact verbatim text for quotation verification.
    """
    if not text or not text.strip():
        return []

    chunks: List[RetrievedChunk] = []
    # Split primarily on paragraphs (double newlines) or numbered clauses
    raw_paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not raw_paras:
        raw_paras = [p.strip() for p in text.split("\n") if p.strip()]

    chunk_idx = 1
    for para in raw_paras:
        # If a single paragraph is very long (> 700 chars), split at sentence boundaries
        if len(para) > 700:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current_sentence_group = []
            current_len = 0
            for s in sentences:
                s_strip = s.strip()
                if not s_strip:
                    continue
                current_sentence_group.append(s_strip)
                current_len += len(s_strip)
                if current_len >= 400:
                    chunk_str = " ".join(current_sentence_group)
                    chunks.append(
                        RetrievedChunk(
                            chunk_id=f"p{page_num}_c{chunk_idx}",
                            page_number=page_num,
                            text=chunk_str,
                            score=0.0,
                        )
                    )
                    chunk_idx += 1
                    current_sentence_group = []
                    current_len = 0
            if current_sentence_group:
                chunk_str = " ".join(current_sentence_group)
                chunks.append(
                    RetrievedChunk(
                        chunk_id=f"p{page_num}_c{chunk_idx}",
                        page_number=page_num,
                        text=chunk_str,
                        score=0.0,
                    )
                )
                chunk_idx += 1
        else:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"p{page_num}_c{chunk_idx}",
                    page_number=page_num,
                    text=para,
                    score=0.0,
                )
            )
            chunk_idx += 1

    return chunks

def retrieve_relevant_passages(
    doc: IngestResponse,
    query_str: str,
    top_k: int = 4,
    min_score_threshold: float = 0.5,
) -> Tuple[List[RetrievedChunk], bool]:
    """
    Performs BM25-inspired local lexical retrieval across all document chunks.
    Expands legal queries with relevant terms.
    Returns:
        (top_chunks, has_sufficient_evidence)
    """
    # 1. Collect all chunks across document pages
    all_chunks: List[RetrievedChunk] = []
    for page in doc.pages:
        all_chunks.extend(chunk_page_text(page.page_number, page.text))

    if not all_chunks:
        return [], False

    # 2. Extract and expand query tokens
    raw_query_tokens = [w for w in tokenize(query_str) if w not in STOP_WORDS]
    if not raw_query_tokens:
        raw_query_tokens = tokenize(query_str)

    query_tokens = set(raw_query_tokens)
    # Add domain synonyms
    for qt in raw_query_tokens:
        if qt in LEGAL_SYNONYM_MAP:
            query_tokens.update(LEGAL_SYNONYM_MAP[qt])

    # 3. Calculate document-wide statistics for BM25
    total_docs = len(all_chunks)
    chunk_token_lists = [tokenize(c.text) for c in all_chunks]
    avg_dl = sum(len(tl) for tl in chunk_token_lists) / max(1, total_docs)

    # Document frequency per token
    doc_freq: Dict[str, int] = {}
    for tl in chunk_token_lists:
        unique_tokens = set(tl)
        for t in unique_tokens:
            doc_freq[t] = doc_freq.get(t, 0) + 1

    # BM25 parameters
    k1 = 1.2
    b = 0.75

    scored_chunks: List[RetrievedChunk] = []
    query_lower = query_str.lower().strip()

    for idx, chunk in enumerate(all_chunks):
        t_list = chunk_token_lists[idx]
        doc_len = len(t_list)
        if doc_len == 0:
            continue

        score = 0.0
        # Calculate term frequencies in chunk
        tf_dict: Dict[str, int] = {}
        for t in t_list:
            tf_dict[t] = tf_dict.get(t, 0) + 1

        for qt in query_tokens:
            if qt in tf_dict:
                tf = tf_dict[qt]
                df = doc_freq.get(qt, 1)
                # Standard BM25 IDF
                idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
                # BM25 TF formula
                tf_norm = (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / avg_dl)))
                score += idf * tf_norm

        # Boost if chunk contains exact phrase or title matches
        chunk_lower = chunk.text.lower()
        if len(query_lower) > 5 and query_lower in chunk_lower:
            score += 4.0

        # Boost section headings like "Section", "Clause", "Termination", etc.
        for qt in raw_query_tokens:
            if re.search(rf"\b(section|clause|article)\b.*\b{re.escape(qt)}\b", chunk_lower):
                score += 2.0

        if score > 0:
            chunk.score = score
            scored_chunks.append(chunk)

    # 4. Sort by relevance descending
    scored_chunks.sort(key=lambda c: c.score, reverse=True)

    if not scored_chunks:
        # Fallback to first page chunk if available, but flag as low confidence
        first_chunk = all_chunks[0]
        first_chunk.score = 0.1
        return [first_chunk], False

    best_score = scored_chunks[0].score
    has_sufficient_evidence = best_score >= min_score_threshold

    # Take top_k passages, avoiding duplicate identical paragraphs
    top_chunks: List[RetrievedChunk] = []
    seen_texts = set()
    for sc in scored_chunks:
        simplified = " ".join(sc.text.split()[:15])
        if simplified in seen_texts:
            continue
        seen_texts.add(simplified)
        top_chunks.append(sc)
        if len(top_chunks) >= top_k:
            break

    return top_chunks, has_sufficient_evidence
