"""
main.py — Main orchestrator for MTG Dragons ETL.
Responsibility: coordinate auth -> fetch -> transform -> sync, with no business logic.
"""

import logging
import time

from .auth import get_client
from .config import setup_logging
from .fetch import fetch_cards
from .sheets_sync import (
    apply_checkboxes,
    ensure_tabs,
    open_sheet,
    update_collection,
    update_dashboard,
    update_sets,
)
from .transform import transform_cards

logger = logging.getLogger("dragonExport.main")


def run() -> None:
    """
    Run the full export pipeline.

    Raises:
        SystemExit(1): On missing file or runtime error.
        SystemExit(130): On user interruption (Ctrl+C).
    """
    setup_logging()
    start = time.time()
    logger.info("[MAIN] Starting MTG Dragons export")

    try:
        client = get_client()
        sheet, should_update_dashboard = open_sheet(client)

        ensure_tabs(sheet)

        cards    = fetch_cards()
        df, sets = transform_cards(cards)

        update_sets(sheet, sets)
        update_collection(sheet, df)
        apply_checkboxes(sheet)
        if should_update_dashboard:
            update_dashboard(sheet)

    except FileNotFoundError as exc:
        logger.error("[MAIN] Required file not found: %s", exc)
        raise SystemExit(1) from exc
    except RuntimeError as exc:
        logger.error("[MAIN] Runtime error: %s", exc)
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        logger.warning("[MAIN] Execution interrupted by user")
        raise SystemExit(130)

    elapsed = time.time() - start
    logger.info(
        "[MAIN] Completed in %.1fs - %d unique artworks | %d sets",
        elapsed, len(df), len(sets),
    )
