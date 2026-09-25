"""CLI entry point for Company Intelligence Agent."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

# Windows' default console codepage (cp1252) can't encode punctuation the LLM
# routinely produces (non-breaking hyphens, curly quotes, em dashes), which
# otherwise crashes every console log line that contains it.
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

from .agent import Agent
from .goal import extract_company
from .planner import Planner
from .tools.llm_analyzer import LLMAnalyzerTool
from .tools.report_writer import ReportWriterTool
from .tools.web_scraper import WebScraperTool
from .tools.web_search import WebSearchTool
from .utils.config import Settings
from .utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Research a company and write a competitive brief."
    )

    parser.add_argument(
        "goal",
        help=(
            "A company name (e.g. \"Stripe\") or a natural-language goal "
            "(e.g. \"Create a competitive landscape brief for Stripe.\")"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory for reports and transcript",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show debug-level logging",
    )

    parser.add_argument(
        "--simulate-failure",
        action="store_true",
        help="Deliberately fail the first scrape to demonstrate recovery",
    )

    return parser.parse_args()


def main() -> int:
    """Configure the agent and execute a research run."""
    args = parse_args()
    console = Console(legacy_windows=False)

    company = extract_company(args.goal)

    console.print(
        Panel.fit(
            "[bold cyan]Company Intelligence Agent[/bold cyan]\n"
            f"Goal: [bold]{args.goal}[/bold]\n"
            f"Researching: [bold]{company}[/bold]"
        )
    )

    try:
        settings = Settings.load()

    except ValueError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        return 2

    output_dir = Path(args.output_dir)

    logger = setup_logger(
        output_dir=output_dir,
        company=company,
        verbose=args.verbose,
    )

    tools = {
        "web_search": WebSearchTool(settings.serpapi_api_key),
        "web_scraper": WebScraperTool(settings.apify_api_token),
        "llm_analyzer": LLMAnalyzerTool(settings.groq_api_key),
        "report_writer": ReportWriterTool(output_dir),
    }

    planner = Planner(
        api_key=settings.groq_api_key,
        logger=logger,
    )

    agent = Agent(
        tools=tools,
        planner=planner,
        llm_api_key=settings.groq_api_key,
        logger=logger,
    )

    result = agent.run(
        company=company,
        simulate_failure=args.simulate_failure,
    )

    if not result.get("success"):
        console.print(
            f"[red]Report generation failed:[/red] "
            f"{result.get('error')}"
        )
        return 1

    paths = result["data"]

    console.print(
        Panel(
            "[green]Done.[/green]\n"
            f"Markdown: {paths['markdown_path']}\n"
            f"JSON: {paths['json_path']}"
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())