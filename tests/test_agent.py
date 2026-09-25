"""Regression tests for source-relevance filtering.

These guard against a real bug found during review: `_first_source_url` used
to contain `"stripe.com" in url or url`, a boolean-logic slip where the
trailing `or url` made the check true for *any* non-empty URL. Combined with
search queries that included the word "official", this caused the agent to
scrape generic dictionary/government pages (e.g. Merriam-Webster's definition
of "official") instead of the researched company's own site, and to cite
those pages as report sources. The fix must also generalize beyond Stripe.
"""
from __future__ import annotations

import logging

from src.agent import Agent
from src.planner import Planner


def _make_agent() -> Agent:
    logger = logging.getLogger("test_agent")
    logger.addHandler(logging.NullHandler())
    planner = Planner(api_key="test-key", logger=logger)
    return Agent(tools={}, planner=planner, llm_api_key="test-key", logger=logger)


STRIPE_SEARCH_RESULTS = [
    {
        "title": "OFFICIAL Definition & Meaning",
        "snippet": "one who holds or is invested with an office",
        "url": "https://www.merriam-webster.com/dictionary/official",
    },
    {
        "title": "Stripe accelerates international expansion",
        "snippet": "Stripe is a suite of payment APIs for internet businesses",
        "url": "https://stripe.com/newsroom/news/stripe-expansion",
    },
]


def test_first_source_url_skips_irrelevant_dictionary_hit():
    agent = _make_agent()
    agent.memory = [{"action": "web_search", "observation": STRIPE_SEARCH_RESULTS}]

    assert agent._first_source_url("Stripe") == "https://stripe.com/newsroom/news/stripe-expansion"


def test_sections_sources_excludes_irrelevant_results():
    agent = _make_agent()
    agent.memory = [{"action": "web_search", "observation": STRIPE_SEARCH_RESULTS}]

    urls = [item["url"] for item in agent._sections("Stripe")["sources"]]

    assert "https://stripe.com/newsroom/news/stripe-expansion" in urls
    assert "https://www.merriam-webster.com/dictionary/official" not in urls


def test_first_source_url_generalizes_to_other_companies():
    agent = _make_agent()
    agent.memory = [
        {
            "action": "web_search",
            "observation": [
                {
                    "title": "Adyen payments platform",
                    "snippet": "Adyen is a global payments company",
                    "url": "https://www.adyen.com/about",
                },
                {
                    "title": "Unrelated dictionary entry",
                    "snippet": "definition text",
                    "url": "https://dictionary.example.com/word",
                },
            ],
        }
    ]

    assert agent._first_source_url("Adyen") == "https://www.adyen.com/about"
