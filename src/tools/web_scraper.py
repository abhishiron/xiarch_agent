"""Single-page Apify Website Content Crawler integration."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .base import BaseTool, ToolResult, retry


class WebScraperTool(BaseTool):
    """Scrape one public webpage through Apify."""

    name = "web_scraper"
    description = "Scrape one public website URL into Markdown. Input: url."
    actor_id = "aYG0l9s7dbB7j3gbS"

    def __init__(self, api_token: str) -> None:
        self.api_token = api_token

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Validate scraper input and invoke the crawler."""
        url = str(input_data.get("url", "")).strip()
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {
                "success": False,
                "error": "Provide a valid public http(s) URL.",
            }

        if input_data.get("simulate_failure"):
            return {
                "success": False,
                "error": "Simulated scraper failure for recovery demonstration.",
            }

        if not self.api_token:
            return {
                "success": False,
                "error": "APIFY_API_TOKEN is not configured.",
            }

        return retry(lambda: self._crawl(url))

    def _crawl(self, url: str) -> ToolResult:
        """Run the Apify Website Content Crawler and retrieve Markdown."""
        try:
            from apify_client import ApifyClient
        except ImportError as exc:
            return {
                "success": False,
                "error": f"Apify dependency unavailable: {exc}",
            }

        try:
            client = ApifyClient(self.api_token)

            # Do not add wait_secs or timeout_secs here:
            # your installed Apify client does not support those arguments.
            run = client.actor(self.actor_id).call(
                run_input={
                    "startUrls": [{"url": url}],
                    "maxCrawlPages": 1,
                    "crawlerType": "playwright:adaptive",
                    "saveMarkdown": True,
                    "removeCookieWarnings": True,
                    "blockMedia": True,
                    "respectRobotsTxtFile": True,
                    "proxyConfiguration": {
                        "useApifyProxy": True,
                    },
                }
            )

            if run is None:
                return {
                    "success": False,
                    "error": "Crawler did not finish with a result.",
                }

            # Compatible with old dict-style and newer object-style responses.
            if isinstance(run, dict):
                dataset_id = run.get("defaultDatasetId")
            else:
                dataset_id = getattr(run, "default_dataset_id", None)

            if not dataset_id:
                return {
                    "success": False,
                    "error": "Crawler returned no default dataset.",
                }

            dataset = client.dataset(dataset_id)

            if hasattr(dataset, "iterate_items"):
                items = list(dataset.iterate_items())
            else:
                items = list(dataset.list_items().items)

        except Exception as exc:
            return {
                "success": False,
                "error": f"Apify crawler request failed: {exc}",
            }

        content = next(
            (
                item.get("markdown")
                or item.get("text")
                or item.get("content")
                for item in items
                if item
            ),
            "",
        )

        if not isinstance(content, str) or not content.strip():
            return {
                "success": False,
                "error": "Crawler returned no readable page content.",
            }

        return {
            "success": True,
            "data": {
                "url": url,
                "content": content[:3000],
            },
        }