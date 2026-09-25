"""Groq-powered focused text analysis."""
from __future__ import annotations

from typing import Any

from ..utils.groq_client import GroqLLM
from .base import BaseTool, ToolResult, retry


class LLMAnalyzerTool(BaseTool):
    """Analyze collected research evidence through Groq."""

    name = "llm_analyzer"
    description = (
        "Summarize, extract competitors, compare, or classify supplied evidence."
    )

    supported_tasks = {
        "summarize",
        "extract_competitors",
        "compare",
        "classify",
        "swot",
        "products",
        "developments"

    }

    def __init__(
        self,
        api_key: str,
        model_name: str = "openai/gpt-oss-20b",
    ) -> None:
        self.llm = GroqLLM(api_key)
        self.model_name = model_name

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Validate analysis input and run a retried Groq completion."""
        task = input_data.get("task")
        content = str(input_data.get("content", "")).strip()
        context = str(input_data.get("context", "")).strip()

        if task not in self.supported_tasks:
            return {
                "success": False,
                "error": f"Unsupported analysis task: {task}",
            }

        if not content:
            return {
                "success": False,
                "error": "Analysis content cannot be empty.",
            }

        return retry(lambda: self._analyze(str(task), content[:12000], context))

    def _analyze(
        self,
        task: str,
        content: str,
        context: str,
    ) -> ToolResult:
        """Call Groq and normalize its text output."""
        try:
            prompt = f"""Analyze evidence for a company-research brief.

Task: {task}
Context: {context}

Evidence:
{content}

Be concise and factual. Do not invent facts. Clearly state uncertainty where needed.
"""

            analysis = self.llm.generate_text(prompt)

            return {
                "success": True,
                "data": {"analysis": analysis},
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"Groq analysis failed: {exc}",
            }