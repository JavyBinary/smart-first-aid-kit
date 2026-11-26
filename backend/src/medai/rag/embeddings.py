"""Dense vector embedding providers and cosine similarity for Hybrid RAG."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import Protocol

from medai.rag.analyzer import normalize_text

__all__ = [
    "EmbeddingProvider",
    "LocalCharNgramEmbedder",
    "cosine_similarity",
]

DEFAULT_DIM = 384


class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]: ...


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute cosine similarity between two L2-normalized or arbitrary vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalCharNgramEmbedder:
    """Deterministic local dense embedder based on signed hashed character n-grams.

    Works offline without external models or downloads while capturing
    morphological stems, fuzzy spelling variants, and multi-word context.
    """

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        normalized = normalize_text(text)
        if not normalized:
            return vec

        tokens = normalized.split()
        features: list[tuple[str, float]] = []

        for tok in tokens:
            # Whole-token stem signal
            features.append((f"w:{tok}", 2.0))
            padded = f"^{tok}$"
            if len(padded) >= 3:
                for i in range(len(padded) - 2):
                    features.append((f"3:{padded[i : i + 3]}", 1.0))
            if len(padded) >= 4:
                for i in range(len(padded) - 3):
                    features.append((f"4:{padded[i : i + 4]}", 1.2))

        for i in range(len(tokens) - 1):
            features.append((f"bi:{tokens[i]}_{tokens[i + 1]}", 1.5))

        for feat, weight in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            raw = int.from_bytes(digest, "big")
            bucket = raw % self._dim
            sign = 1.0 if ((raw >> 8) & 1) == 0 else -1.0
            vec[bucket] += sign * weight

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [round(v / norm, 6) for v in vec]
        return vec

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]
