"""Offline unit tests: integrations are mocked and no API keys are needed."""
from __future__ import annotations

import sys
import types

from src.tools.llm_analyzer import LLMAnalyzerTool
from src.tools.report_writer import ReportWriterTool
from src.tools.web_scraper import WebScraperTool
from src.tools.web_search import WebSearchTool


def test_web_search_returns_results(monkeypatch):
    class FakeClient:
        def __init__(self, api_key): pass
        def search(self, _params):
            return {"organic_results": [{"title": "Stripe", "snippet": "Payments", "link": "https://stripe.com"}]}
    monkeypatch.setitem(sys.modules, "serpapi", types.SimpleNamespace(Client=FakeClient))
    result = WebSearchTool("key").execute({"query": "Stripe overview"})
    assert result["success"] and result["data"][0]["url"] == "https://stripe.com"


def test_web_search_handles_empty_query():
    result = WebSearchTool("key").execute({"query": "  "})
    assert not result["success"] and "empty" in result["error"].lower()


def test_web_scraper_returns_content(monkeypatch):
    class FakeActor:
        def call(self, **_kwargs): return {"defaultDatasetId": "dataset"}
    class FakeDataset:
        def iterate_items(self): return iter([{"markdown": "# Official positioning"}])
    class FakeClient:
        def __init__(self, _token): pass
        def actor(self, _id): return FakeActor()
        def dataset(self, _id): return FakeDataset()
    monkeypatch.setitem(sys.modules, "apify_client", types.SimpleNamespace(ApifyClient=FakeClient))
    result = WebScraperTool("token").execute({"url": "https://example.com"})
    assert result == {"success": True, "data": {"url": "https://example.com", "content": "# Official positioning"}}


def test_web_scraper_handles_invalid_url():
    result = WebScraperTool("token").execute({"url": "not-a-url"})
    assert not result["success"] and "valid" in result["error"].lower()


def test_llm_analyzer_summarizes(monkeypatch):
    class FakeCompletions:
        def create(self, **_kwargs):
            message = types.SimpleNamespace(content="Concise summary")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])
    class FakeChat:
        completions = FakeCompletions()
    class FakeGroq:
        def __init__(self, api_key): self.chat = FakeChat()

    import src.utils.groq_client as groq_client_module
    monkeypatch.setattr(groq_client_module, "Groq", FakeGroq)

    result = LLMAnalyzerTool("key").execute({"task": "summarize", "content": "Evidence"})
    assert result["success"] and result["data"]["analysis"] == "Concise summary"


def test_report_writer_creates_files(tmp_path):
    result = ReportWriterTool(tmp_path).execute({"company": "Stripe", "sections": {"overview": "A company", "sources": []}})
    assert result["success"]
    assert (tmp_path / "stripe_report.md").exists()
    assert (tmp_path / "stripe_report.json").exists()


def test_scraper_simulated_failure_is_explicit():
    result = WebScraperTool("token").execute({"url": "https://example.com", "simulate_failure": True})
    assert not result["success"] and "simulated" in result["error"].lower()
