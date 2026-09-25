"""Write a transparent Markdown and JSON research brief."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult


class ReportWriterTool(BaseTool):
    name = "report_writer"
    description = "Write Markdown and JSON competitive brief. Input: company, sections."

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        company, sections = str(input_data.get("company", "")).strip(), input_data.get("sections")
        if not company or not isinstance(sections, dict):
            return {"success": False, "error": "company and sections dictionary are required."}
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = {"company": company, "generated_at": datetime.now(timezone.utc).isoformat(), "sections": sections}
        stem = company.lower().replace(" ", "_") + "_report"
        json_path, md_path = self.output_dir / f"{stem}.json", self.output_dir / f"{stem}.md"
        try:
            json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            md_path.write_text(self._markdown(payload), encoding="utf-8")
            return {"success": True, "data": {"markdown_path": str(md_path), "json_path": str(json_path)}}
        except OSError as exc:
            return {"success": False, "error": f"Could not write report: {exc}"}

    @staticmethod
    def _markdown(payload: dict[str, Any]) -> str:
        sections = payload["sections"]
        lines = [f"# Competitive Landscape Brief: {payload['company']}", "", f"_Generated: {payload['generated_at']}_", ""]
        # execution_log is deliberately excluded here: it's an internal
        # debugging trail (raw tool-call outcomes, raw API error text) that
        # belongs in the run's log file (utils/logger.py), not in a report a
        # business reader would open. It's still available in the JSON
        # sibling file for anyone who wants it.
        headings = [("overview", "Company Overview"), ("products", "Key Products/Services"), ("competitors", "Competitor Landscape"), ("developments", "Recent Developments"), ("swot", "SWOT Summary"), ("sources", "Sources Used")]
        for key, title in headings:
            value = sections.get(key, "No evidence collected.")
            lines.extend([f"## {title}", ""])
            if key == "competitors" and isinstance(value, list):
                lines.extend(["| Competitor | Evidence |", "|---|---|"])
                lines.extend(f"| {item.get('name', 'Unknown')} | {item.get('evidence', '')} |" for item in value)
            elif key == "sources" and isinstance(value, list):
                lines.extend(f"- [{item.get('title', item.get('url', 'Source'))}]({item.get('url', '')})" for item in value)
            elif key == "execution_log" and isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
            else:
                lines.append(str(value))
            lines.append("")
        return "\n".join(lines)
