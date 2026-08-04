import os

from .base import BeanExtractor
from .claude_extractor import ClaudeExtractor


def get_extractor() -> BeanExtractor:
    provider = os.environ.get("EXTRACTOR_PROVIDER", "claude")
    if provider == "claude":
        return ClaudeExtractor()
    if provider == "ollama":
        raise NotImplementedError("Ollama extraction arrives in milestone 1.6.0")
    raise ValueError(f"Unknown EXTRACTOR_PROVIDER: {provider}")
