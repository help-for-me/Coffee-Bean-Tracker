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

This must read as an actual recommendation, not a recap: not "your scores
trended up in July" but something closer to "you consistently rate Honey-
process Colombian coffees with stone fruit notes highest - look for those."
Ground the recommendation in the single strongest pattern actually present
in the data (by process, origin, or tasting note) - don't try to cover
every pattern you notice, just the clearest one.

Time window: {window_label}

Stats:
{stats_json}

Write ONE or TWO sentences, second person ("you"), specific - mention
actual process/origin/tasting-note names from the data. Say it once, plainly,
and stop - no restating the same point in different words, no hedging
("might", "could", "explore"), no closing filler sentence that just
softens or repeats what you already said. If there's too little data for a
clear pattern, say so briefly rather than stretching a weak one. Write in
Canadian English (e.g. "flavour", "favourite", "colour"). No preamble, no
markdown, just the recommendation text itself."""


class ClaudeInsightGenerator(InsightGenerator):
    def __init__(self, api_key: str | None = None, model: str | None = None, extra_instructions: str | None = None):
        self.client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
        # User-supplied addition to the prompt (1.4.0 settings UI's
        # plain-language prompt editing) - appended as its own section
        # rather than merged into the template.
        self.extra_instructions = extra_instructions

    def generate(self, insights: dict, window_type: str) -> str:
        window_label = "the recent window" if window_type == "recent" else "all time"
        prompt = NARRATIVE_PROMPT_TEMPLATE.format(
            window_label=window_label, stats_json=json.dumps(insights, indent=2, default=str)
        )
        if self.extra_instructions:
            prompt += f"\n\nAdditional instructions from the user - follow these too:\n{self.extra_instructions}"
        response = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return text.strip()
