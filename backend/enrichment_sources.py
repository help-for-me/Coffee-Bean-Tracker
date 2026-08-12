import os
from pathlib import Path

SOURCES_PATH = Path(os.environ.get("ENRICHMENT_SOURCES_PATH", "data/enrichment_sources"))


def save_source(bean_profile_id: int, text: str) -> str:
    # Deliberately unversioned - a fixed filename per profile so a later
    # reprocess overwrites the previous source rather than accumulating
    # stale copies, matching "the current best known source" semantics.
    SOURCES_PATH.mkdir(parents=True, exist_ok=True)
    path = SOURCES_PATH / f"{bean_profile_id}.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)
