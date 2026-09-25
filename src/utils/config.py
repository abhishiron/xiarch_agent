"""Environment configuration with early, actionable validation."""
from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime credentials required by the agent."""

    serpapi_api_key: str
    apify_api_token: str
    groq_api_key: str

    @classmethod
    def load(cls) -> "Settings":
        """Load required settings from .env and validate them."""
        load_dotenv()

        values = {
            "SERPAPI_API_KEY": os.getenv("SERPAPI_API_KEY", "").strip(),
            "APIFY_API_TOKEN": os.getenv("APIFY_API_TOKEN", "").strip(),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY", "").strip(),
        }

        missing = [
            key
            for key, value in values.items()
            if not value or value.startswith("your_")
        ]

        if missing:
            raise ValueError(
                "Missing required environment variables: "
                + ", ".join(missing)
                + ". Copy .env.example to .env."
            )

        return cls(
            serpapi_api_key=values["SERPAPI_API_KEY"],
            apify_api_token=values["APIFY_API_TOKEN"],
            groq_api_key=values["GROQ_API_KEY"],
        )