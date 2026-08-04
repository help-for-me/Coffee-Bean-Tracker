import pytest

from backend import crud
from backend.insights.base import InsightGenerator
from backend.insights.factory import get_generator
from backend.insights.narrative import generate_narrative
from backend.models import EntryCreate


class FakeGenerator(InsightGenerator):
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.calls = []

    def generate(self, insights, window_type):
        self.calls.append((insights, window_type))
        if self.error:
            raise self.error
        return self.text


def test_factory_ollama_not_implemented(monkeypatch):
    monkeypatch.setenv("NARRATIVE_PROVIDER", "ollama")
    with pytest.raises(NotImplementedError):
        get_generator()


def test_factory_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("NARRATIVE_PROVIDER", "bogus")
    with pytest.raises(ValueError):
        get_generator()


def test_factory_claude_requires_api_key(monkeypatch):
    monkeypatch.setenv("NARRATIVE_PROVIDER", "claude")
    with pytest.raises(KeyError):
        get_generator()


def test_generate_narrative_saves_and_returns_result(conn):
    crud.create_entry(conn, EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8))
    fake = FakeGenerator(text="You tend to enjoy washed process coffees.")

    result = generate_narrative(conn, "all_time", generator=fake)

    assert result["summary_text"] == "You tend to enjoy washed process coffees."
    assert result["window_type"] == "all_time"
    assert crud.get_latest_narrative(conn, "all_time")["id"] == result["id"]


def test_generate_narrative_passes_window_scoped_stats_only(conn):
    crud.create_entry(conn, EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8))
    fake = FakeGenerator(text="summary")

    generate_narrative(conn, "recent", generator=fake)

    passed_insights, passed_window = fake.calls[0]
    assert passed_window == "recent"
    # A flat, window-scoped shape - not the nested all_time/recent split
    # get_insights() itself returns, and never a calculation the generator
    # would need to do itself.
    assert set(passed_insights) == {
        "monthly_trend", "by_process", "by_origin_country", "by_tasting_note", "most_repurchased",
    }


def test_generate_narrative_propagates_generator_errors(conn):
    fake = FakeGenerator(error=RuntimeError("provider unavailable"))
    with pytest.raises(RuntimeError, match="provider unavailable"):
        generate_narrative(conn, "all_time", generator=fake)
    assert crud.get_latest_narrative(conn, "all_time") is None
