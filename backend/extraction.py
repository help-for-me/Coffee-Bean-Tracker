import logging
from pathlib import Path
from typing import Optional

from . import crud, database
from .enrichment import run_enrichment_lookup
from .extractor.base import BeanExtractor
from .extractor.factory import get_extractor

logger = logging.getLogger(__name__)


def run_extraction(entry_id: int, photo_paths: list[str], extractor: Optional[BeanExtractor] = None) -> None:
    conn = database.get_connection()
    try:
        image_bytes_list = [Path(path).read_bytes() for path in photo_paths]
        active_extractor = extractor or get_extractor()
        result = active_extractor.extract(image_bytes_list)
        crud.apply_extraction_result(conn, entry_id, result)
        logger.info("Extraction complete for entry %s", entry_id)
        # A photo-only entry doesn't know its real bean_profile identity
        # until extraction resolves it above - only trigger the 1.9.0
        # website lookup once that identity is in, mirroring the typed-
        # identity trigger in routers/entries.py.
        entry = crud.get_entry(conn, entry_id)
        if entry and not entry["bean_profile"]["is_provisional"]:
            if crud.maybe_start_enrichment(conn, entry["bean_profile"]["id"]):
                run_enrichment_lookup(entry["bean_profile"]["id"])
    except Exception:
        logger.exception("Extraction failed for entry %s", entry_id)
        crud.mark_extraction_failed(conn, entry_id)
    finally:
        conn.close()
