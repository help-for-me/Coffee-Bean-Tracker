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
Ground every recommendation in the highest-scoring pattern(s) actually
present in the data (by process, origin, or tasting note), and tell the
reader what to look for next, not just what already happened.

Time window: {window_label}

Stats:
{stats_json}

Write 3-5 sentences, second person ("you"), friendly and specific - mention
actual roaster/bean/process/origin names from the data where relevant. If a
section is empty or there's too little data in it, skip it rather than
mentioning the lack of data. No preamble, no markdown, just the
recommendation text itself."""


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
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return text.strip()
