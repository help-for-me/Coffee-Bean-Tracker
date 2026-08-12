import logging
from typing import Optional

from . import crud, database
from .enrichment_sources import save_source
from .matcher.base import RoasterMatcher
from .matcher.factory import get_matcher

logger = logging.getLogger(__name__)


def run_enrichment_lookup(
    bean_profile_id: int, extra_context: Optional[str] = None, matcher: Optional[RoasterMatcher] = None
) -> None:
    conn = database.get_connection()
    try:
        profile = crud.get_bean_profile(conn, bean_profile_id)
        if profile is None:
            return
        active_matcher = matcher or get_matcher()
        result = active_matcher.find_candidates(profile["roaster"], profile["bean_name"], extra_context)
        confident = result.get("confident_match")
        if confident:
            _confirm(conn, bean_profile_id, confident["url"], confident.get("title", ""), active_matcher)
        elif result.get("candidates"):
            crud.save_enrichment_candidates(conn, bean_profile_id, result["candidates"])
            logger.info(
                "Enrichment: %s candidate(s) found for bean_profile %s", len(result["candidates"]), bean_profile_id
            )
        else:
            crud.mark_enrichment_no_match(conn, bean_profile_id)
            logger.info("Enrichment: no match found for bean_profile %s", bean_profile_id)
    except Exception:
        logger.exception("Enrichment lookup failed for bean_profile %s", bean_profile_id)
        crud.mark_enrichment_failed(conn, bean_profile_id)
    finally:
        conn.close()


def run_enrichment_confirm(
    bean_profile_id: int, url: str, title: str, matcher: Optional[RoasterMatcher] = None
) -> None:
    conn = database.get_connection()
    try:
        _confirm(conn, bean_profile_id, url, title, matcher or get_matcher())
    except Exception:
        logger.exception("Enrichment fetch/extract failed for bean_profile %s", bean_profile_id)
        crud.mark_enrichment_failed(conn, bean_profile_id)
    finally:
        conn.close()


def _confirm(conn, bean_profile_id: int, url: str, title: str, matcher: RoasterMatcher) -> None:
    extracted = matcher.fetch_and_extract(url)
    source_text = extracted.get("source_text")
    source_path = save_source(bean_profile_id, source_text) if source_text else None
    crud.confirm_enrichment(
        conn, bean_profile_id, url=url, title=title, source_path=source_path, fields=extracted.get("fields") or {}
    )
    logger.info("Enrichment confirmed for bean_profile %s: %s", bean_profile_id, url)
