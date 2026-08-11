import json
import os

from anthropic import Anthropic

from .base import InsightGenerator

NARRATIVE_PROMPT_TEMPLATE = """You are writing a short flavour/preference recommendation for a personal
coffee-tracking app, based on someone's own logged data. You are given
already-computed statistics below as JSON - interpret patterns in plain
language, but NEVER invent or restate a number that isn't in this data, and
never calculate anything yourself (e.g. don't average numbers together that
aren't already averaged for you).

by_process/by_origin_country/by_tasting_note are each a ranked "items" list
plus a "significance" verdict comparing the TOP TWO items in that ranking
using a real statistical test:
- Items are already sorted by adjusted_score, not avg_score. adjusted_score
  pulls thin-sample items toward the overall average, so a single 9-out-of-
  10 rating can't outrank an item backed by ten ratings - always use
  adjusted_score's ordering, never re-rank by avg_score yourself.
- significance.comparable=false means there isn't even enough data to test
  (fewer than 2 groups, or fewer than 2 ratings on one side).
- significance.significant=false means the gap between the top two could
  plausibly just be noise, not a real preference, even if their averages
  look different.

This must read as an actual recommendation, not a recap: not "your scores
trended up in July" but something closer to "you consistently rate Honey-
process Colombian coffees with stone fruit notes highest - look for those."
Ground it in the top-ranked item (by adjusted_score) from whichever
dimension - process, origin, or tasting note - has significant=true. If
NONE of the three dimensions have significant=true, do not pick one
anyway: say plainly that there's no clear statistically meaningful
preference yet in the logged data. Never claim a preference the
significance verdict doesn't support, even when one average looks higher
by eye - "verifiable and rigorous" beats "interesting-sounding."

Time window: {window_label}

Stats:
{stats_json}

Write ONE or TWO sentences, second person ("you"), specific - mention
actual process/origin/tasting-note names from the data when there's a real
pattern to report. Say it once, plainly, and stop - no restating the same
point in different words, no hedging ("might", "could", "explore"), no
closing filler sentence that just softens or repeats what you already
said. Write in Canadian English (e.g. "flavour", "favourite", "colour").
No preamble, no markdown, just the recommendation text itself."""


class ClaudeInsightGenerator(InsightGenerator):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    def generate(self, insights: dict, window_type: str) -> str:
        window_label = "the recent window" if window_type == "recent" else "all time"
        prompt = NARRATIVE_PROMPT_TEMPLATE.format(
            window_label=window_label, stats_json=json.dumps(insights, indent=2, default=str)
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return text.strip()
