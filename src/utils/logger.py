"""Human-readable, structured console and transcript logging."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"


def setup_logger(output_dir: Path, company: str, verbose: bool = False) -> logging.Logger:
    """Configure the package logger once and return it."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("company_intel")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    # legacy_windows=False keeps Rich on ANSI/VT rendering; the legacy win32
    # console path encodes through cp1252 and crashes on Unicode punctuation
    # (e.g. non-breaking hyphens) that the LLM's own output often contains.
    rich_console = Console(legacy_windows=False)
    console = RichHandler(
        console=rich_console,
        rich_tracebacks=True,
        show_path=False,
        markup=True,
    )
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"run_{company.lower().replace(' ', '_')}_{stamp}.md"
    file_handler = logging.FileHandler(output_dir / filename, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger
