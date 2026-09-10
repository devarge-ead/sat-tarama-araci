"""Shared advanced text-similarity helpers used by batch and manual search."""

from __future__ import annotations

import difflib

# Values that mean "no CAS number" and must be ignored during matching.
INVALID_CAS = {"", "na", "n/a", "n.a.", "-", "?"}


def is_valid_cas(value: str) -> bool:
    """Return True when the CAS value carries real data."""
    return value.strip().lower() not in INVALID_CAS


def item_similarity(a: str, b: str) -> float:
    """Advanced text similarity (0-100) combining sequence and token matching."""
    a = a.strip().lower()
    b = b.strip().lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    seq = difflib.SequenceMatcher(None, a, b).ratio() * 100.0
    token = difflib.SequenceMatcher(None, " ".join(sorted(a.split())),
                                    " ".join(sorted(b.split()))).ratio() * 100.0
    return max(seq, token)