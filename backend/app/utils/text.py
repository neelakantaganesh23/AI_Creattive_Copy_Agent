"""Text helpers used by the repetition-fix agent and output validation."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_WORD_RE = re.compile(r"[a-z0-9']+")
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "built", "by", "for", "from", "in", "is",
        "it", "of", "on", "or", "that", "the", "this", "to", "with", "your", "you",
    }
)


def normalise(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower()))


def tokenise(text: str, *, drop_stopwords: bool = True) -> set[str]:
    tokens = set(_WORD_RE.findall(text.lower()))
    return tokens - _STOPWORDS if drop_stopwords else tokens


def sequence_similarity(left: str, right: str) -> float:
    """Character-level similarity in ``[0, 1]``."""
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, normalise(left), normalise(right)).ratio()


def jaccard_similarity(left: str, right: str) -> float:
    """Token-overlap similarity in ``[0, 1]``."""
    left_tokens, right_tokens = tokenise(left), tokenise(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def similarity(left: str, right: str) -> float:
    """Combined similarity score; the maximum of sequence and token overlap."""
    return max(sequence_similarity(left, right), jaccard_similarity(left, right))


def shared_phrases(left: str, right: str, *, min_words: int = 4) -> list[str]:
    """Contiguous word runs of ``min_words`` or more present in both texts."""
    left_words = normalise(left).split()
    right_normalised = normalise(right)
    found: list[str] = []
    for size in range(len(left_words), min_words - 1, -1):
        for start in range(0, len(left_words) - size + 1):
            phrase = " ".join(left_words[start : start + size])
            if phrase in right_normalised and not any(phrase in existing for existing in found):
                found.append(phrase)
    return found


def truncate(text: str, limit: int) -> str:
    """Trim to ``limit`` characters on a word boundary where possible."""
    text = text.strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rstrip()
    if " " in clipped:
        candidate = clipped.rsplit(" ", 1)[0].rstrip(" ,;:-")
        if len(candidate) >= limit * 0.6:
            return candidate
    return clipped


def slugify_title(brief: str, *, max_length: int = 70) -> str:
    """Derive a readable campaign title from the first sentence of a brief."""
    cleaned = " ".join(brief.strip().split())
    if not cleaned:
        return "Untitled campaign"
    first_sentence = re.split(r"(?<=[.!?])\s", cleaned)[0]
    return truncate(first_sentence, max_length) or "Untitled campaign"
