import logging
from pathlib import Path
from typing import Optional

from . import crud, database
from .extractor.base import BeanExtractor
from .extractor.factory import get_extractor

logger = logging.getLogger(__name__)


def run_extraction(entry_id: int, photo_paths: list[str], extractor: Optional[BeanExtractor] = None) -> None:
    conn = database.get_connection()
    try:
        image_bytes_list = [Path(path).read_bytes() for path in photo_paths]
        active_extractor = extractor or get_extractor(conn)
        result = active_extractor.extract(image_bytes_list)
        crud.apply_extraction_result(conn, entry_id, result)
        logger.info("Extraction complete for entry %s", entry_id)
    except Exception:
        logger.exception("Extraction failed for entry %s", entry_id)
        crud.mark_extraction_failed(conn, entry_id)
    finally:
        conn.close()
