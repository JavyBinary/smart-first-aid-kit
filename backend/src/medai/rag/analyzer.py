"""Text analysis, tokenization, and morphology for MedAI BM25 search."""

from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod

import pymorphy3

__all__ = [
    "MorphAnalyzer",
    "SimpleAnalyzer",
    "TextAnalyzer",
    "normalize_text",
]

_TOKEN = re.compile(r"[a-zа-я0-9]+(?:-[a-zа-я0-9]+)*")


def normalize_text(text: str) -> str:
    """NFC normalization, case folding, whitespace collapse, and 'ё' -> 'е' equivalence."""
    folded = unicodedata.normalize("NFC", text).casefold().replace("ё", "е")
    return " ".join(folded.split())


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _TOKEN.finditer(normalize_text(text)))


class TextAnalyzer(ABC):
    @abstractmethod
    def terms(self, text: str) -> tuple[str, ...]:
        """Return normalized index terms in original appearance order."""


class SimpleAnalyzer(TextAnalyzer):
    """Simple lowercase word tokens without morphology for tests and baselines."""

    def terms(self, text: str) -> tuple[str, ...]:
        return _tokens(text)


class MorphAnalyzer(TextAnalyzer):
    """Russian lemmatization using pymorphy3 for queries and documents.

    Hyphenated terms (e.g. 'но-шпа') are preserved whole.
    """

    def __init__(self) -> None:
        self._morph = pymorphy3.MorphAnalyzer()
        self._cache: dict[str, str] = {}

    def terms(self, text: str) -> tuple[str, ...]:
        return tuple(self._normal_form(token) for token in _tokens(text))

    def _normal_form(self, token: str) -> str:
        cached = self._cache.get(token)
        if cached is not None:
            return cached

        if "-" in token:
            self._cache[token] = token
            return token

        try:
            parsed = self._morph.parse(token)[0]
            normal_form = parsed.normal_form
            res = normalize_text(normal_form) or token
        except (IndexError, ValueError):
            res = token

        self._cache[token] = res
        return res
