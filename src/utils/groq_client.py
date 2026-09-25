"""Small Groq client wrapper for text and JSON agent responses."""
from __future__ import annotations

import json
from typing import Any

from groq import Groq


class GroqLLM:
    """Provides consistent Groq calls for planning and analysis."""

    model = "openai/gpt-oss-20b"

    def __init__(self, api_key: str) -> None:
        self.client = Groq(api_key=api_key)

    def generate_text(self, prompt: str) -> str:
        """Return a plain-text completion."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise company-research assistant. "
                        "Use only the supplied evidence and state uncertainty."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        text = response.choices[0].message.content
        if not text or not text.strip():
            raise ValueError("Groq returned an empty response.")

        return text.strip()

    def generate_json(self, prompt: str) -> dict[str, Any] | list[Any]:
        """Return a JSON completion for planner and ReAct decisions."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Return valid JSON only. Do not use Markdown fences.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        text = response.choices[0].message.content
        if not text or not text.strip():
            raise ValueError("Groq returned an empty JSON response.")

        return json.loads(text)