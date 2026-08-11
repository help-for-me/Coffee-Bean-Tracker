import json
import os
from typing import Optional

from anthropic import Anthropic

from .base import RoasterMatcher

FIND_CANDIDATES_PROMPT = """You are trying to find the roaster's own website product page for a
specific coffee, using web search. Search for the roaster's official
website first, then the specific product/bean page on that site.

Roaster: {roaster}
Bean name: {bean_name}{extra_context}

Only consider the roaster's own website (not review sites, retailers,
marketplaces, or other roasters) as a match - the goal is the page where
this specific roaster describes and sells this specific coffee.

Return ONLY valid JSON, no markdown, no preamble, matching this schema:

{{
  "confident_match": {{"url": string, "title": string}} or null,
  "candidates": [{{"url": string, "title": string, "snippet": string}}] or []
}}

Set confident_match (and leave candidates empty) only when you're genuinely
sure you found the right specific product page - matching both the roaster
and this exact bean, not just the roaster's general site or a different
product from them.

If you're not certain, but found up to three plausible pages, leave
confident_match null and list them under candidates instead, each with a
short snippet explaining why it might be the right one (e.g. "This
roaster's current single-origin lineup, no exact name match" or "Same bean
name, listed under a different roaster - possibly a past or different
roastery").

If nothing plausible turns up at all, return confident_match: null and
candidates: []."""

FETCH_AND_EXTRACT_PROMPT = """Fetch this page and extract whatever structured coffee information it
states about this specific coffee:

{url}

Return ONLY valid JSON, no markdown, no preamble, matching this schema:

{{
  "origin_country": string or null,
  "region": string or null,
  "farm_producer": string or null,
  "altitude_m": number or null,
  "variety": string or null,
  "process": string or null,
  "co_ferment_status": "yes" or "no" or "unknown",
  "co_ferment_ingredient": string or null,
  "certifications": string or null,
  "roast_level": string or null,
  "printed_tasting_notes": string or null,
  "roast_location": string or null,
  "website_description": string or null
}}

Only fill a field when the page actually states it - never guess or infer
from general knowledge about the roaster or region. website_description is
a short excerpt (1-2 sentences) of the roaster's own descriptive copy about
this coffee, if the page has any beyond a bare spec list - leave it null if
the page is just a spec sheet with nothing worth quoting."""


def _response_text(content_blocks) -> str:
    # A response can contain multiple content blocks (text interleaved with
    # server_tool_use/web_search_tool_result/web_fetch_tool_result) - collect
    # every text block rather than trusting content[0].
    text = "".join(block.text for block in content_blocks if getattr(block, "type", None) == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


def _parse_json(content_blocks) -> dict:
    text = _response_text(content_blocks)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude did not return valid JSON: {text[:500]!r}") from exc


def _extract_fetched_text(content_blocks) -> Optional[str]:
    for block in content_blocks:
        if getattr(block, "type", None) != "web_fetch_tool_result":
            continue
        result = getattr(block, "content", None)
        document = getattr(result, "content", None)
        source = getattr(document, "source", None)
        data = getattr(source, "data", None)
        if isinstance(data, str):
            return data
    return None


class ClaudeRoasterMatcher(RoasterMatcher):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        # Deliberately separate from CLAUDE_MODEL (which defaults to Haiku
        # for extraction/narrative) - this needs a model capable of the
        # web_search_20260209 tool's dynamic filtering and of judging match
        # confidence, not just following a fixed extraction schema.
        self.model = model or os.environ.get("ENRICHMENT_MODEL", "claude-sonnet-5")

    def find_candidates(self, roaster: str, bean_name: str, extra_context: Optional[str] = None) -> dict:
        context_block = (
            f"\n\nAdditional context from the user, since an earlier search "
            f"didn't find the right page: {extra_context}"
            if extra_context
            else ""
        )
        prompt = FIND_CANDIDATES_PROMPT.format(roaster=roaster, bean_name=bean_name, extra_context=context_block)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content)
        return {
            "confident_match": result.get("confident_match"),
            "candidates": (result.get("candidates") or [])[:3],
        }

    def fetch_and_extract(self, url: str) -> dict:
        prompt = FETCH_AND_EXTRACT_PROMPT.format(url=url)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            tools=[{"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 2}],
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "fields": _parse_json(response.content),
            "source_text": _extract_fetched_text(response.content),
        }
