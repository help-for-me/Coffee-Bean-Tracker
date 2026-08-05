import base64
import difflib
import json
import os
import re

from anthropic import Anthropic

from . import coffee_vocab
from .base import BeanExtractor
from ..image_utils import sniff_image_type

EXTRACTION_PROMPT = """You are extracting structured data from photo(s) related to a coffee — a
bag label, a cafe menu board, or an info card. Return ONLY valid JSON, no
markdown, no preamble, matching this schema:

{
  "roaster": string or null,
  "bean_name": string or null,
  "origin_country": string or null,
  "region": string or null,
  "farm_producer": string or null,
  "farms": [{"farm_name": string, "location": string or null}] or null,
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
  "batch_number": string or null,
  "roast_location": string or null
}

printed_tasting_notes, origin_country, region, process, and roast_level are
the most important fields when available — extract printed_tasting_notes
exactly as written.

roaster and bean_name identify the product itself, distinct from every
other field below (which describe the coffee's origin/processing): roaster
is the roasting company's own brand name (typically the most prominent
logo/wordmark on the label, e.g. "Stumptown", "Pallet Coffee Roasters" -
not a growing region or a farm); bean_name is the specific product name
the roaster gave this coffee (e.g. "Hair Bender", "Elkin Guzman") - this
is sometimes the same as the grower/farm name (roasters that name single-
origin lots after the producer) but is still a distinct field from
farm_producer, since a blend's bean_name usually isn't a person or farm at
all. Always attempt both from whatever's printed, even for entries that
already have a name - the caller decides whether to use it.

Specialty bag labels often stack several short lines close together (e.g.
farm name, then grower name, then a "Variety - Process" line, then a
tasting-notes line), and it's easy to misfile a word from one line into the
wrong field. Think carefully about which category each word belongs to
before filing it:
- **region**: a sub-national growing area or department (e.g. Huila,
  Nariño, Yirgacheffe, Tarrazú) — never a person's name or a specific farm
  name, even if it's printed in the position where a region usually goes.
  If only a farm or grower name is printed and no actual region name
  appears anywhere, leave region null rather than guessing.
- **farm_producer**: the specific farm, mill, or grower name (e.g. "El
  Mirador", "Elkin Guzman", "Finca La Esperanza") — just the name(s), as a
  simple summary.
- **farms**: one entry per distinct farm named on the label, each with its
  own location if the label prints one for that specific farm (most bags
  name exactly one farm, so this will usually be a single-item list
  mirroring farm_producer; only list more than one when the label
  genuinely names multiple distinct farms, e.g. a blend).
- **roast_location**: where the ROASTER roasted the coffee (e.g. "Roasted
  in Vancouver, B.C." printed near the roaster's logo) — this is about the
  roastery's location, never where the coffee was grown. Keep it separate
  from origin_country/region, which are always about growing origin.
- **variety**: the coffee plant varietal (e.g. Castillo, Caturra, Bourbon,
  Typica, Geisha/Gesha) — never a process or a region.
- **process**: ONLY the base processing method (e.g. Washed, Honey,
  Natural, Anaerobic, Carbonic Maceration). Never append co-fermentation
  wording or ingredient names here (no "Co-Fermented", "Co-ferment", or
  fruit/yeast names in this field) — that belongs exclusively in
  co_ferment_status/co_ferment_ingredient below.
- **printed_tasting_notes**: ONLY flavor/aroma descriptors (fruits,
  florals, sweeteners, spices, etc). If a label line reads like
  "Castillo - Honey" immediately followed by flavor words (e.g. "Hibiscus
  - Peach - Tropical Fruits"), split it: "Castillo" is the variety,
  "Honey" is the process, and only the flavor words belong in
  printed_tasting_notes. Common single words are easy to misfile: "Honey"
  and "Natural" are almost always a process, not a tasting note. Also
  exclude product-category/packaging text, which is easy to mistake for a
  notes list because it's often printed right next to one: bilingual
  labels are common (e.g. "Whole Bean Coffee / Grains de café", "Ground
  Coffee / Café moulu" on Canadian bags) - these describe the product
  format, not the flavor, and belong in neither this field nor any other.

Reference vocabulary (not exhaustive — real labels use plenty of valid
terms outside these lists, so don't force a fit if the label clearly says
something else; use this only to sanity-check ambiguous words before
filing them):
- Common processes: __PROCESSES__
- Common varieties: __VARIETIES__
- Common growing regions: __REGIONS__

co_ferment_status is "yes" only if the label explicitly indicates a
co-fermentation process (e.g. names a fruit, yeast strain, or other
ingredient introduced during fermentation); "no" only if the label
explicitly states a standard single process; "unknown" otherwise.
co_ferment_ingredient should capture the specific named ingredient when
co_ferment_status is "yes" (e.g. "lychee", "cascara", "wine yeast") — leave
null if not named or status isn't "yes". Roasters that use co-ferments
typically disclose the specific ingredient rather than just flagging that
one was used, so capture it precisely as written (e.g. "honey-processed
lychee co-ferment"), but keep that wording out of the process field above.
batch_number is a printed roast/lot number or code, if the bag has one.
For everything else, if a field isn't visible or provided, return null.
Do not guess."""

EXTRACTION_PROMPT = (
    EXTRACTION_PROMPT.replace("__PROCESSES__", ", ".join(coffee_vocab.KNOWN_PROCESSES))
    .replace("__VARIETIES__", ", ".join(coffee_vocab.KNOWN_VARIETIES))
    .replace("__REGIONS__", ", ".join(coffee_vocab.KNOWN_REGIONS))
)


def _sniff_media_type(image_bytes: bytes) -> str:
    # Unlike image_utils.sniff_image_type (used to reject non-images on
    # upload), this always needs *some* answer to hand the Anthropic API -
    # by the time extraction runs, the file has already passed upload
    # validation, so falling back to jpeg here is a reasonable default
    # rather than a security gap.
    return sniff_image_type(image_bytes) or "image/jpeg"


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


def _strip_coferment_wording(process: str | None) -> str | None:
    # Defensive cleanup for when the model still appends co-ferment wording
    # to the process field despite the prompt saying not to (e.g. "Washed,
    # Mango Co-Fermented") - that information belongs solely in
    # co_ferment_status/co_ferment_ingredient.
    if not process:
        return process
    segments = [s.strip() for s in re.split(r"[,;/]", process)]
    kept = [s for s in segments if s and "ferment" not in s.lower()]
    return ", ".join(kept) or None


def _correct_against_vocab(value: str | None, vocab: list[str]) -> str | None:
    # Fixes small OCR/typing slips (e.g. "Castllo" -> "Castillo") by
    # matching each comma-separated segment against a known-terms list.
    # Conservative on purpose: a real but uncommon term (not in the list)
    # is left untouched rather than remapped to the closest known one.
    if not value:
        return value
    segments = [s.strip() for s in re.split(r"[,/]", value)]
    corrected = []
    for segment in segments:
        if not segment:
            continue
        match = difflib.get_close_matches(segment, vocab, n=1, cutoff=0.84)
        corrected.append(match[0] if match else segment)
    return ", ".join(corrected)


def normalize_extraction(result: dict) -> dict:
    if result.get("process"):
        result["process"] = _correct_against_vocab(
            _strip_coferment_wording(result["process"]), coffee_vocab.KNOWN_PROCESSES
        )
    if result.get("variety"):
        result["variety"] = _correct_against_vocab(result["variety"], coffee_vocab.KNOWN_VARIETIES)
    return result


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
        return normalize_extraction(_parse_extraction(response.content))
