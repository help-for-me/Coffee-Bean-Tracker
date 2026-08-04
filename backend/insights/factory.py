import os

from .base import InsightGenerator
from .claude_generator import ClaudeInsightGenerator


def get_generator() -> InsightGenerator:
    provider = os.environ.get("NARRATIVE_PROVIDER", "claude")
    if provider == "claude":
        return ClaudeInsightGenerator()
    if provider == "ollama":
        raise NotImplementedError("Ollama narrative generation arrives in milestone 1.3.0")
    raise ValueError(f"Unknown NARRATIVE_PROVIDER: {provider}")
