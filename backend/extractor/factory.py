import os
import sqlite3
from typing import Optional

from .. import crud
from .base import BeanExtractor
from .claude_extractor import ClaudeExtractor


def get_extractor(conn: Optional[sqlite3.Connection] = None) -> BeanExtractor:
    provider = os.environ.get("EXTRACTOR_PROVIDER", "claude")
    if provider == "claude":
        extra_instructions = crud.get_setting(conn, "extraction_custom_instructions") if conn else None
        return ClaudeExtractor(extra_instructions=extra_instructions)
    if provider == "ollama":
        raise NotImplementedError("Ollama extraction arrives in milestone 1.3.0")
    raise ValueError(f"Unknown EXTRACTOR_PROVIDER: {provider}")
