import base64
import json
import os

from anthropic import Anthropic

from .base import BeanExtractor

EXTRACTION_PROMPT = """You are extracting structured data from photo(s) related to a coffee — a
bag label, a cafe menu board, or an info card. Return ONLY valid JSON, no
markdown, no preamble, matching this schema:

{
  "origin_country": string or null,
  "region": string or null,
  "farm_producer": string or null,
  "altitude_m": number or null,
  "variety": string or null,
  "process": string or null,
  "co_ferment_status": "yes" or "no" or "unknown",
  "co_ferment_ingredient": string or null,
  "roast_level": string or null,
  "certifications": string or null,
  "printed_tasting_notes": string or null,
  "roast_date": "YYYY-MM-DD" or null,
  "bag_weight_g": number or null,
  "batch_number": string or null
}

printed_tasting_notes, origin_country, region, process, and roast_level are
the most important fields when available — extract printed_tasting_notes
exactly as written. co_ferment_status is "yes" only if the label explicitly
indicates a co-fermentation process (e.g. names a fruit, yeast strain, or
other ingredient introduced during fermentation); "no" only if the label
explicitly states a standard single process; "unknown" otherwise.
co_ferment_ingredient should capture the specific named ingredient when
co_ferment_status is "yes" (e.g. "lychee", "cascara", "wine yeast") — leave
null if not named or status isn't "yes". Roasters that use co-ferments
typically disclose the specific ingredient rather than just flagging that
one was used, so capture it precisely as written (e.g. "honey-processed
lychee co-ferment"). batch_number is a printed roast/lot number or code,
if the bag has one. For everything else, if a field isn't visible or
provided, return null. Do not guess."""


def _sniff_media_type(image_bytes: bytes) -> str:
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _response_text(content_blocks) -> str:
    # A response can contain multiple content blocks and the first one
    # isn't always the real text - collect every text block instead of
    # trusting content[0].
    text = "".join(block.text for block in content_blocks if getattr(block, "type", None) == "text")
    text = text.strip()
    # Defensive: the prompt says "no markdown", but models don't always
    # comply - strip a ```json ... ``` or ``` ... ``` fence if present.
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


def _parse_extraction(content_blocks) -> dict:
    text = _response_text(content_blocks)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude did not return valid JSON: {text[:500]!r}") from exc


class ClaudeExtractor(BeanExtractor):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    def extract(self, image_bytes_list: list[bytes]) -> dict:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _sniff_media_type(image_bytes),
                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                },
            }
            for image_bytes in image_bytes_list
        ]
        content.append({"type": "text", "text": EXTRACTION_PROMPT})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )
        return _parse_extraction(response.content)
