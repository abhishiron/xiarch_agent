"""Shared interface and retry utility for all tools."""
from __future__ import annotations

from abc import ABC, abstractmethod
from time import sleep
from typing import Any, Callable


ToolResult = dict[str, Any]


class BaseTool(ABC):
    """A tool with a stable, serializable success/error response contract."""

    name: str
    description: str

    @abstractmethod
    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Return ``{success: bool, data?: Any, error?: str}``."""


def retry(operation: Callable[[], ToolResult], attempts: int = 3) -> ToolResult:
    """Retry exceptions and unsuccessful transient calls with small backoff."""
    last_error = "Unknown error"
    for attempt in range(attempts):
        try:
            result = operation()
            if result.get("success"):
                return result
            last_error = str(result.get("error", last_error))
        except Exception as exc:  # integrations deliberately normalize vendor errors
            last_error = str(exc)
        if attempt < attempts - 1:
            sleep(2**attempt)
    return {"success": False, "error": last_error}
