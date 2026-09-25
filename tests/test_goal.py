"""extract_company handles both a bare name and the assignment's own example
phrasing ("Create a competitive landscape brief for Stripe."), deterministically
and without any LLM call.
"""
from __future__ import annotations

from src.goal import extract_company


def test_bare_company_name_passes_through():
    assert extract_company("Stripe") == "Stripe"


def test_multi_word_bare_company_name_passes_through():
    assert extract_company("Bank of America") == "Bank of America"


def test_assignment_example_phrasing():
    assert extract_company("Create a competitive landscape brief for Stripe.") == "Stripe"


def test_trailing_about_phrasing():
    assert extract_company("Give me a competitive analysis about Adyen") == "Adyen"


def test_leading_verb_phrasing():
    assert extract_company("Research Stripe") == "Stripe"


def test_leading_verb_phrasing_multi_word():
    assert extract_company("Research JPMorgan Chase") == "JPMorgan Chase"


def test_leading_verb_case_insensitive_but_name_stays_capitalized():
    # A regression check for a real bug caught during development: a bare
    # re.IGNORECASE on the whole pattern also folds [A-Z] to match lowercase,
    # which would let the match run past the company name into the rest of
    # the sentence. Scoped (?i:...) on just the verb avoids that.
    assert extract_company("analyze Stripe's roadmap") == "Stripe's"
