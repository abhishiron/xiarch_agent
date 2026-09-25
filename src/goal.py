"""Deterministic extraction of a company name from a natural-language goal.

No LLM call here on purpose: this is the one piece of input parsing that has
to keep working even when Groq itself is unavailable (rate-limited,
misconfigured), and a bare company name is by far the most common
invocation, so a small heuristic is more reliable than a network round trip.
"""
from __future__ import annotations

import re

_TRAILING_COMPANY = re.compile(
    r"(?:for|about|on|regarding|into)\s+"
    r"([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)*)\s*[.!?]?\s*$"
)

_LEADING_VERB_COMPANY = re.compile(
    # (?i:...) scopes case-insensitivity to just the verb; a bare re.IGNORECASE
    # flag on the whole pattern would also fold [A-Z] to match lowercase,
    # defeating the capitalization check that's meant to stop the match at
    # the company name's boundary.
    r"^(?i:research|analyze|analyse|investigate|profile)\s+"
    r"([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)*)"
)


def extract_company(goal: str) -> str:
    """Pull a company name out of a free-form goal.

    Handles phrasing like "Create a competitive landscape brief for Stripe."
    (the assignment's own example) and "Research Adyen". Falls back to
    treating the whole input as the company name, so a bare name such as
    "Stripe" still works unchanged.
    """
    goal = goal.strip()

    match = _TRAILING_COMPANY.search(goal)
    if match:
        return match.group(1).strip().rstrip(".")

    match = _LEADING_VERB_COMPANY.match(goal)
    if match:
        return match.group(1).strip().rstrip(".")

    return goal
