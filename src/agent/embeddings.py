"""
CRM Digital FTE — Embedding Service

Produces 1536-dim vectors for pgvector similarity search.

Pipeline priority:
  1. OpenAI text-embedding-3-small (via API key)
  2. Local hashing-trick embedder (deterministic, content-based, no API needed)
"""

import os
import re
import math
import hashlib
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536


# ── OpenAI API Embedder ───────────────────────────────────────────────────────

def _get_embedding_client() -> Optional[OpenAI]:
    """Create an OpenAI client. Uses OPENAI_API_KEY or falls back to GROQ_API_KEY."""
    api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _api_embed_text(text: str) -> Optional[List[float]]:
    client = _get_embedding_client()
    if client is None:
        return None
    try:
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return resp.data[0].embedding
    except Exception as e:
        logger.warning(f"API embedding failed, falling back to local: {e}")
        return None


def _api_embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    if not texts:
        return []
    client = _get_embedding_client()
    if client is None:
        return None
    try:
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        indexed = [(r.index, r.embedding) for r in resp.data]
        indexed.sort(key=lambda x: x[0])
        return [emb for _, emb in indexed]
    except Exception as e:
        logger.warning(f"Batch API embedding failed: {e}")
        return None


# ── Local Embedder (feature hashing / hashing trick) ──────────────────────────
# Produces deterministic 1536-dim unit vectors from word frequencies.
# Supports cosine similarity — similar texts → similar vectors.
# This is a lightweight fallback that does NOT require any API key.

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "it", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "shall", "should", "may", "might", "must", "to",
    "of", "in", "for", "on", "with", "at", "by", "from", "as", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "because", "but", "and", "or", "if", "while", "that",
    "this", "these", "those", "i", "me", "my", "myself", "we", "our",
    "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "whose",
})


def _tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alpha, remove stop words and short tokens."""
    text = text.lower()
    tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", text)
    return [t for t in tokens if len(t) > 2 and t not in _STOP_WORDS]


def _local_embed(text: str) -> List[float]:
    """Generate a 1536-dim unit vector from text using feature hashing.

    Each word is hashed to k=3 positions for redundancy.
    TF-IDF-like weighting: log(1 + count) * idf_factor.
    """
    vec = [0.0] * EMBEDDING_DIMENSIONS
    tokens = _tokenize(text)
    if not tokens:
        return vec

    # Count term frequencies
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    n_tokens = len(tokens)
    for word, count in tf.items():
        # Weight: log(1 + frequency)
        weight = math.log(1 + count)
        # Hash word to k=3 positions
        h = hashlib.md5(word.encode("utf-8")).digest()
        for k in range(3):
            idx = (int.from_bytes(h[k * 2: k * 2 + 2], "big") + k * 997) % EMBEDDING_DIMENSIONS
            sign = 1 if (h[0] + k) % 2 == 0 else -1
            vec[idx] += sign * weight

    # Normalize to unit vector
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _local_embed_batch(texts: List[str]) -> List[List[float]]:
    return [_local_embed(t) for t in texts]


# ── Public API ─────────────────────────────────────────────────────────────────

def embed_text(text: str) -> Optional[List[float]]:
    """Embed a single text string — returns a 1536-dim vector.

    Tries OpenAI API first, falls back to local hashing-trick embedder.
    """
    vec = _api_embed_text(text)
    if vec is not None:
        return vec
    return _local_embed(text)


def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """Embed multiple texts — returns list of 1536-dim vectors.

    Tries OpenAI API first, falls back to local hashing-trick embedder.
    """
    vecs = _api_embed_texts(texts)
    if vecs is not None:
        return vecs
    return _local_embed_batch(texts)
