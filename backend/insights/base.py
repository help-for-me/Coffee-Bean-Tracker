from abc import ABC, abstractmethod


class InsightGenerator(ABC):
    @abstractmethod
    def generate(self, insights: dict, window_type: str) -> str:
        """Takes an already-computed stats dict (see stats.insights_for_window)
        and interprets it in natural language - never calculates numbers
        itself, only describes what's already there."""
        ...
