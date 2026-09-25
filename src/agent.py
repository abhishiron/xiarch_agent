"""Hand-rolled ReAct loop for the Company Intelligence Agent."""
from __future__ import annotations

import json
from typing import Any

from .executor import Executor
from .planner import Planner
from .utils.groq_client import GroqLLM


THINK_PROMPT = """You are an autonomous company research agent.

Goal: {goal}

Plan:
{plan}

Memory:
{memory}

Explain the next planned step briefly.

Return JSON only:
{{
  "thought": "brief reasoning",
  "action": "web_search|web_scraper|llm_analyzer|report_writer|FINISH",
  "tool_input": {{}}
}}
"""


RECOVERY_PROMPT = """A company-research tool failed.

Failed step: {step}
Error: {error}
Memory: {memory}

Return JSON only:
{{
  "decision": "retry|skip|alternative",
  "reasoning": "brief explanation",
  "modified_input": {{}}
}}
"""


class Agent:
    """Runs a bounded, observable ReAct research workflow."""

    def __init__(
        self,
        tools: dict[str, Any],
        planner: Planner,
        llm_api_key: str,
        logger: Any,
        max_iterations: int = 10,
    ) -> None:
        self.tools = tools
        self.planner = planner
        self.logger = logger
        self.max_iterations = max_iterations

        self.executor = Executor(tools, logger)
        self.llm = GroqLLM(llm_api_key)

        self.memory: list[dict[str, Any]] = []
        self.plan: list[dict[str, Any]] = []

    def run(
        self,
        company: str,
        simulate_failure: bool = False,
    ) -> dict[str, Any]:
        """Create a plan, gather evidence, analyze it, and write a report."""
        goal = f"Research and produce a competitive landscape brief for {company}"

        self.memory = []
        self.plan = self.planner.decompose(company)

        for step in self.plan:
            self.logger.info(
                "[PLAN] %s. %s (%s)",
                step["step_number"],
                step["description"],
                step["suggested_tool"],
            )

        final_result: dict[str, Any] | None = None

        for iteration, step in enumerate(
            self.plan[: self.max_iterations],
            start=1,
        ):
            thought = self.think(goal, step)

            # Keep tool execution aligned with the validated plan.
            action = step["suggested_tool"]

            self.logger.info(
                "[TRACE] Step %s | Thought: %s | Tool: %s",
                iteration,
                thought.get("thought", step["description"]),
                action,
            )

            if action == "llm_analyzer":
                self._run_analysis_suite(company, step["description"])
                continue

            tool_input = self._tool_input(
                action=action,
                company=company,
                step_number=step["step_number"],
                simulate_failure=simulate_failure,
            )

            self.logger.info(
                "[TRACE] Input: %s",
                self._short(tool_input),
            )

            result = self.executor.execute(action, tool_input)

            if result.get("success"):
                self.memory.append(
                    {
                        "step": step["description"],
                        "action": action,
                        "input": tool_input,
                        "observation": result.get("data"),
                    }
                )

                if action == "report_writer":
                    final_result = result

                continue

            self.logger.warning(
                "[AGENT] Tool failure detected: %s failed with: %s",
                action,
                result.get("error"),
            )

            recovery = self.recover(
                step=step,
                error=str(result.get("error", "Unknown error")),
                action=action,
                old_input=tool_input,
            )

            self.logger.info(
                "[AGENT] Recovery decision: %s | %s",
                recovery["decision"],
                recovery.get("reasoning", ""),
            )

            self.memory.append(
                {
                    "step": step["description"],
                    "action": action,
                    "input": tool_input,
                    "error": result.get("error"),
                    "recovery": recovery,
                }
            )

            if recovery["decision"] == "retry":
                self.logger.info(
                    "[AGENT] Retrying %s with modified input: %s",
                    action,
                    self._short(recovery["modified_input"]),
                )

                retry_result = self.executor.execute(
                    action,
                    recovery["modified_input"],
                )

                self.logger.info(
                    "[AGENT] Retry %s.",
                    "succeeded" if retry_result.get("success") else "failed again",
                )

                self.memory.append(
                    {
                        "step": step["description"],
                        "action": action,
                        "input": recovery["modified_input"],
                        "observation": retry_result.get("data"),
                        "error": retry_result.get("error"),
                    }
                )

        if final_result and final_result.get("success"):
            return final_result

        return self.tools["report_writer"].execute(
            {
                "company": company,
                "sections": self._sections(company),
            }
        )

    def think(
        self,
        goal: str,
        step: dict[str, Any],
    ) -> dict[str, Any]:
        """Ask Groq for visible ReAct reasoning."""
        fallback = {
            "thought": step["description"],
            "action": step["suggested_tool"],
            "tool_input": {},
        }

        try:
            response = self.llm.generate_json(
                THINK_PROMPT.format(
                    goal=goal,
                    plan=json.dumps(self.plan, default=str),
                    memory=self._short(self.memory, limit=4000),
                )
            )

            return response if isinstance(response, dict) else fallback

        except Exception as exc:
            self.logger.warning("[AGENT] Think fallback: %s", exc)
            return fallback

    def recover(
        self,
        step: dict[str, Any],
        error: str,
        action: str,
        old_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Choose a safe retry, skip, or alternate-source recovery."""
        decision = {
            "decision": "skip",
            "reasoning": "Continue with available evidence.",
            "modified_input": {},
        }

        try:
            response = self.llm.generate_json(
                RECOVERY_PROMPT.format(
                    step=step["description"],
                    error=error,
                    memory=self._short(self.memory, limit=4000),
                )
            )

            if (
                isinstance(response, dict)
                and response.get("decision")
                in {"retry", "skip", "alternative"}
            ):
                decision = response

        except Exception as exc:
            self.logger.warning("[AGENT] Recovery fallback: %s", exc)

        if action == "web_scraper":
            alternative_url = self._alternative_url(old_input.get("url"))

            if alternative_url:
                decision = {
                    "decision": "retry",
                    "reasoning": "Try an alternative search-result URL.",
                    "modified_input": {"url": alternative_url},
                }

        return decision

    def _tool_input(
        self,
        action: str,
        company: str,
        step_number: int,
        simulate_failure: bool,
    ) -> dict[str, Any]:
        """Create deterministic, valid inputs for planned tools."""
        queries = {
            1: f"{company} company overview and core products",
            2: f"{company} competitors alternatives market landscape",
            4: f"{company} recent news and developments 2026",
        }

        if action == "web_search":
            return {"query": queries.get(step_number, f"{company} news")}

        if action == "web_scraper":
            return {
                "url": self._first_source_url(company)
                or f"https://www.{self._domain_token(company)}.com",
                "simulate_failure": simulate_failure,
            }

        if action == "report_writer":
            return {
                "company": company,
                "sections": self._sections(company),
            }

        return {}

    def _run_analysis_suite(
        self,
        company: str,
        step_description: str,
    ) -> None:
        """Create distinct report sections from the accumulated evidence."""
        evidence = self._evidence_text()

        tasks = [
            (
                "summarize",
                f"Write a concise Company Overview for {company}. "
                "Use only evidence supplied. Do not discuss competitors.",
            ),
            (
                "products",
                f"List {company}'s key products and services in concise bullets. "
                "Use only evidence supplied.",
            ),
            (
                "extract_competitors",
                f"Identify the primary competitors of {company}. "
                "For each, state why it competes. Use only supplied evidence.",
            ),
            (
                "developments",
                f"Summarize recent developments for {company}. "
                "Exclude rumors and clearly label uncertainty.",
            ),
            (
                "swot",
                f"Write a concise SWOT summary for {company}, based only on "
                "the supplied evidence. Use Strengths, Weaknesses, "
                "Opportunities, and Threats headings.",
            ),
        ]

        for task, context in tasks:
            tool_input = {
                "task": task,
                "content": evidence,
                "context": context,
            }

            self.logger.info(
                "[TRACE] Analysis task: %s",
                task,
            )

            result = self.executor.execute("llm_analyzer", tool_input)

            self.memory.append(
                {
                    "step": step_description,
                    "action": "llm_analyzer",
                    "input": tool_input,
                    "observation": result.get("data"),
                    "error": result.get("error"),
                }
            )

    def _first_source_url(self, company: str) -> str | None:
        """Prefer the researched company's own domain; fall back to the first relevant result."""
        fallback: str | None = None

        for entry in self.memory:
            if entry.get("action") != "web_search":
                continue

            for item in entry.get("observation") or []:
                url = item.get("url", "")

                if not url or not self._relevant(item, company):
                    continue

                if self._domain_token(company) in url.lower():
                    return url

                if fallback is None:
                    fallback = url

        return fallback

    def _alternative_url(self, previous_url: str | None) -> str | None:
        """Choose an untried URL found by web search."""
        for entry in self.memory:
            if entry.get("action") != "web_search":
                continue

            for item in entry.get("observation") or []:
                url = item.get("url")

                if url and url != previous_url:
                    return url

        return None

    def _evidence_text(self) -> str:
        """Create bounded evidence for Groq analysis."""
        evidence = [
            entry.get("observation")
            for entry in self.memory
            if entry.get("observation")
        ]

        return self._short(evidence, limit=12000)

    def _sections(self, company: str) -> dict[str, Any]:
        """Build final report sections from separate analysis outputs."""
        analyses: dict[str, str] = {}

        for entry in self.memory:
            if entry.get("action") != "llm_analyzer":
                continue

            task = entry.get("input", {}).get("task")
            analysis = (entry.get("observation") or {}).get("analysis", "")

            if task and analysis:
                analyses[task] = analysis

        sources = [
            item
            for entry in self.memory
            if entry.get("action") == "web_search"
            for item in (entry.get("observation") or [])
            if self._relevant(item, company)
        ]

        failures = [
            f"{entry['action']} failed: {entry['error']}"
            for entry in self.memory
            if entry.get("error")
        ]

        return {
            "overview": analyses.get(
                "summarize",
                "No overview analysis was collected.",
            ),
            "products": analyses.get(
                "products",
                "No product analysis was collected.",
            ),
            "competitors": [
                {
                    "name": "Competitive analysis",
                    "evidence": analyses.get(
                        "extract_competitors",
                        "No competitor analysis was collected.",
                    ),
                }
            ],
            "developments": analyses.get(
                "developments",
                "No recent-development analysis was collected.",
            ),
            "swot": analyses.get(
                "swot",
                "No SWOT analysis was collected.",
            ),
            "sources": sources,
            "execution_log": [
                (
                    f"{entry.get('action')}: "
                    f"{'failed' if entry.get('error') else 'completed'}"
                )
                for entry in self.memory
            ]
            + failures,
        }

    @staticmethod
    def _domain_token(company: str) -> str:
        """Reduce a company name to a bare token for loose domain matching."""
        return "".join(ch for ch in company.lower() if ch.isalnum())

    @classmethod
    def _relevant(cls, item: dict[str, Any], company: str) -> bool:
        """Drop off-topic search hits (e.g. dictionary/government pages) that
        don't actually mention the researched company."""
        token = cls._domain_token(company)

        if not token:
            return True

        haystack = "".join(
            ch for ch in " ".join(
                [
                    item.get("title", ""),
                    item.get("snippet", ""),
                    item.get("url", ""),
                ]
            ).lower()
            if ch.isalnum() or ch.isspace()
        )

        return token in haystack.replace(" ", "")

    @staticmethod
    def _short(value: Any, limit: int = 500) -> str:
        """Create a log-safe truncated string."""
        text = str(value).replace("\n", " ")
        return text[:limit] + ("…" if len(text) > limit else "")