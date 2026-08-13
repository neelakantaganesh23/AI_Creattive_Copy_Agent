"""Tolerant JSON extraction for model output (§13).

Models occasionally wrap JSON in prose or code fences. ``parse_json_object``
performs a single deterministic repair attempt before giving up; the caller is
responsible for the (at most one) model-side repair round trip.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


class JSONRepairFailed(ValueError):
    """Raised when a payload cannot be coerced into a JSON object."""


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse ``raw`` into a dict, repairing common model formatting mistakes."""
    if not raw or not raw.strip():
        raise JSONRepairFailed("The model returned an empty response.")

    for candidate in _candidates(raw):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]

    raise JSONRepairFailed("The model response did not contain a JSON object.")


def _candidates(raw: str) -> list[str]:
    text = raw.strip()
    candidates = [text]

    fenced = _FENCE_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1).strip())

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    # Same candidates again with trailing commas stripped.
    return candidates + [_TRAILING_COMMA_RE.sub(r"\1", item) for item in candidates]
