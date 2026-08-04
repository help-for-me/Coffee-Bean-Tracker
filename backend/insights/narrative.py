import sqlite3
from typing import Optional

from .. import crud
from .base import InsightGenerator
from .factory import get_generator
from .stats import get_insights, insights_for_window


def generate_narrative(conn: sqlite3.Connection, window_type: str, generator: Optional[InsightGenerator] = None) -> dict:
    windowed_stats = insights_for_window(get_insights(conn), window_type)
    active_generator = generator or get_generator()
    summary_text = active_generator.generate(windowed_stats, window_type)
    return crud.save_narrative(conn, window_type, summary_text)
