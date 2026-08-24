from abc import ABC, abstractmethod
from typing import Optional


class RoasterMatcher(ABC):
    @abstractmethod
    def find_candidates(self, roaster: str, bean_name: str, extra_context: Optional[str] = None) -> dict:
        """Searches for the roaster's own product page for this specific bean.
        Returns {"confident_match": {"url", "title"} or None, "candidates": [...]}
        (candidates has 0-3 items, and is only meaningful when confident_match
        is None)."""
        ...

    @abstractmethod
    def fetch_and_extract(self, url: str) -> dict:
        """Fetches a confirmed product page and extracts structured coffee
        fields from it. Returns {"fields": {...}, "source_text": str or None}."""
        ...

    @abstractmethod
    def extract_from_upload(self, file_bytes: bytes, media_type: str) -> dict:
        """Extracts structured coffee fields directly from a user-supplied
        image or PDF (a screenshot or spec sheet the user found themselves),
        with no web search or fetch involved. Returns the fields dict."""
        ...
