"""SerpAPI-backed web search."""
from __future__ import annotations

from typing import Any

from .base import BaseTool, ToolResult, retry


class WebSearchTool(BaseTool):
    """Search Google through the current SerpAPI Python SDK."""

    name = "web_search"
    description = "Search Google and return concise organic results. Input: query."

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Validate input and search SerpAPI with retry handling."""
        query = str(input_data.get("query", "")).strip()

        if not query:
            return {
                "success": False,
                "error": "Search query cannot be empty.",
            }

        if not self.api_key:
            return {
                "success": False,
                "error": "SERPAPI_API_KEY is not configured.",
            }

        return retry(lambda: self._search(query))

    def _search(self, query: str) -> ToolResult:
        """Call the current SerpAPI SDK and normalize organic results."""
        try:
            import serpapi
        except ImportError as exc:
            return {
                "success": False,
                "error": f"SerpAPI dependency unavailable: {exc}",
            }

        try:
            client = serpapi.Client(api_key=self.api_key)

            payload = client.search(
                {
                    "engine": "google",
                    "q": query,
                    "num": 8,
                }
            )
        except Exception as exc:
            return {
                "success": False,
                "error": f"SerpAPI request failed: {exc}",
            }

        if payload.get("error"):
            return {
                "success": False,
                "error": f"SerpAPI: {payload['error']}",
            }

        results = [
            {
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
            }
            for item in payload.get("organic_results", [])[:8]
            if item.get("link")
        ]

        if not results:
            return {
                "success": False,
                "error": "SerpAPI returned no organic results.",
            }

        return {
            "success": True,
            "data": results,
        }