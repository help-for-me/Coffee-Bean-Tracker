import os

from .base import RoasterMatcher
from .claude_matcher import ClaudeRoasterMatcher


def get_matcher() -> RoasterMatcher:
    provider = os.environ.get("ENRICHMENT_PROVIDER", "claude")
    if provider == "claude":
        return ClaudeRoasterMatcher()
    raise ValueError(f"Unknown ENRICHMENT_PROVIDER: {provider}")
