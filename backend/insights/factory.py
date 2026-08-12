import os
import sqlite3
from typing import Optional

from .. import crud
from .base import InsightGenerator
from .claude_generator import ClaudeInsightGenerator


def get_generator(conn: Optional[sqlite3.Connection] = None) -> InsightGenerator:
    provider = os.environ.get("NARRATIVE_PROVIDER", "claude")
    if provider == "claude":
        extra_instructions = crud.get_setting(conn, "narrative_custom_instructions") if conn else None
        return ClaudeInsightGenerator(extra_instructions=extra_instructions)
    if provider == "ollama":
        raise NotImplementedError("Ollama narrative generation arrives in milestone 1.3.0")
    raise ValueError(f"Unknown NARRATIVE_PROVIDER: {provider}")
