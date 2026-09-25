"""LLM-driven goal decomposition with enforced research-step ordering."""
from __future__ import annotations

from typing import Any

from .utils.groq_client import GroqLLM


class Planner:
    """Creates a company-specific plan while enforcing required tool order."""

    expected_tools = [
        "web_search",
        "web_search",
        "web_scraper",
        "web_search",
        "llm_analyzer",
        "report_writer",
    ]

    def __init__(self, api_key: str, logger: Any) -> None:
        self.llm = GroqLLM(api_key)
        self.logger = logger

    def decompose(self, company: str) -> list[dict[str, Any]]:
        prompt = f"""Create a six-step research plan for {company}.

Return a JSON object with a "plan" list. Use this exact tool order:
1. web_search: company overview and products
2. web_search: main competitors
3. web_scraper: official company website
4. web_search: recent developments
5. llm_analyzer: synthesize evidence
6. report_writer: create final report

Each item requires step_number, description, suggested_tool, and reasoning.
"""

        try:
            response = self.llm.generate_json(prompt)
            plan = response.get("plan", [])

            if self._is_valid(plan):
                self.logger.info(
                    "[PLANNER] Decomposed goal into %s steps.",
                    len(plan),
                )
                return plan

            raise ValueError("Planner returned an invalid tool sequence.")

        except Exception as exc:
            self.logger.warning(
                "[PLANNER] Using deterministic fallback plan: %s",
                exc,
            )
            return self._fallback(company)

    def _is_valid(self, plan: Any) -> bool:
        return (
            isinstance(plan, list)
            and len(plan) == 6
            and [step.get("suggested_tool") for step in plan]
            == self.expected_tools
        )

    @staticmethod
    def _fallback(company: str) -> list[dict[str, Any]]:
        return [
            {
                "step_number": 1,
                "description": f"Research {company} overview and products",
                "suggested_tool": "web_search",
                "reasoning": "Establish company facts and offerings.",
            },
            {
                "step_number": 2,
                "description": f"Identify {company} competitors",
                "suggested_tool": "web_search",
                "reasoning": "Build the competitor landscape.",
            },
            {
                "step_number": 3,
                "description": f"Scrape {company} official positioning",
                "suggested_tool": "web_scraper",
                "reasoning": "Collect first-party evidence.",
            },
            {
                "step_number": 4,
                "description": f"Find recent {company} developments",
                "suggested_tool": "web_search",
                "reasoning": "Add current market context.",
            },
            {
                "step_number": 5,
                "description": "Analyze research evidence",
                "suggested_tool": "llm_analyzer",
                "reasoning": "Create distinct report sections.",
            },
            {
                "step_number": 6,
                "description": "Write final report",
                "suggested_tool": "report_writer",
                "reasoning": "Save Markdown and JSON deliverables.",
            },
        ]