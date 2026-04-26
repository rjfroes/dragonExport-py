"""
fetch.py — Card retrieval from Scryfall API.
Responsibility: pagination, HTTP retries, and payload validation.
"""

import logging
import time

import requests

from .config import (
    HTTP_TIMEOUT,
    MAX_PAGES,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF,
    SCRYFALL_QUERY,
    SCRYFALL_UNIQUE,
)

logger = logging.getLogger("dragonExport.fetch")


def _http_get(url: str, params: dict | None = None) -> dict:
    """
    GET with timeout, exponential retry, and HTTP status validation.

    Retries only transient failures (network, 429, 503).
    4xx errors (except 429) fail immediately.

    Raises:
        RuntimeError: After exhausting attempts or on non-transient HTTP error.
    """
    last_exc: Exception | None = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            last_exc = TimeoutError(f"Timeout after {HTTP_TIMEOUT}s on {url}")
            logger.warning("[FETCH] Attempt %d/%d - timeout", attempt, RETRY_ATTEMPTS)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            if exc.response is not None and exc.response.status_code not in (429, 503):
                raise RuntimeError(f"HTTP error {status} on {url}") from exc
            last_exc = exc
            logger.warning("[FETCH] Attempt %d/%d - HTTP %s", attempt, RETRY_ATTEMPTS, status)
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            logger.warning("[FETCH] Attempt %d/%d - %s", attempt, RETRY_ATTEMPTS, exc)

        if attempt < RETRY_ATTEMPTS:
            sleep_time = RETRY_BACKOFF ** attempt
            logger.debug("[FETCH] Waiting %.1fs before retry", sleep_time)
            time.sleep(sleep_time)

    raise RuntimeError(f"Failed after {RETRY_ATTEMPTS} attempts on {url}") from last_exc


def fetch_cards() -> list[dict]:
    """
    Fetch all Dragon cards from Scryfall with safe pagination.

    Returns:
        List of dicts with raw card data.

    Raises:
        ValueError: If API response does not include the 'data' field.
        RuntimeError: On persistent HTTP failure.
    """
    logger.info("[SCRYFALL] Starting fetch - query: %r", SCRYFALL_QUERY)

    url: str = "https://api.scryfall.com/cards/search"
    params: dict | None = {"q": SCRYFALL_QUERY, "unique": SCRYFALL_UNIQUE}
    cards: list[dict] = []
    page = 0

    while url and page < MAX_PAGES:
        page += 1
        logger.debug("[SCRYFALL] Fetching page %d", page)

        payload = _http_get(url, params=params if page == 1 else None)

        if "data" not in payload:
            raise ValueError(
                f"Unexpected Scryfall API response (missing 'data' field): {list(payload.keys())}"
            )

        cards.extend(payload["data"])
        url = payload.get("next_page")

    if page >= MAX_PAGES and url:
        logger.warning(
            "[SCRYFALL] Page limit (%d) reached - stopping pagination", MAX_PAGES
        )

    logger.info("[SCRYFALL] %d cards fetched across %d page(s)", len(cards), page)
    return cards
