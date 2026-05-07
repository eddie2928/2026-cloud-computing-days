"""2A-5: Semantic similarity fallback using local sentence-transformers.
Used when Bedrock is unavailable or over token cap.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

_COSINE_THRESHOLD = float(os.environ.get("SEMANTIC_THRESHOLD", "0.85"))
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def cosine_similarity(a, b) -> float:
    import numpy as np
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b) + 1e-10)
    return float(np.dot(a_norm, b_norm))


def check_semantic_leak(prompt: str, reference_code: str) -> tuple[bool, float]:
    """Return (is_leak, similarity_score). is_leak=True if score >= threshold."""
    model = _get_model()
    embeddings = model.encode([prompt, reference_code])
    score = cosine_similarity(embeddings[0], embeddings[1])
    return score >= _COSINE_THRESHOLD, score
