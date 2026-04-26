"""
transform.py — Transform raw cards into a structured DataFrame.
Responsibility: group by artwork, deduplicate, compute prices, and normalize fields.
"""

import logging
from collections import defaultdict

import pandas as pd

from .config import COLLECTION_HEADERS, CURRENCY_RATE_BRL

logger = logging.getLogger("dragonExport.transform")


def _safe_price(card: dict) -> float:
    """
    Extract USD price as float.
    Return 0.0 when value is missing, null, or invalid.
    """
    raw = card.get("prices", {}).get("usd")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (ValueError, TypeError):
        logger.debug(
            "[TRANSFORM] Ignored invalid price for %r: %r", card.get("name"), raw
        )
        return 0.0


def transform_cards(cards: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """
    Transform a list of raw cards into a DataFrame and unique set list.

    Groups by illustration_id, selects the oldest print as base,
    and computes derived fields (Price BRL, Colors, Premium, All Sets By Art).

    Args:
        cards: List of dicts containing raw Scryfall API card data.

    Returns:
        Tuple (DataFrame sorted by Release Date, sorted set list).
    """
    logger.info("[TRANSFORM] Processing %d raw cards", len(cards))

    grouped: dict[str, list[dict]] = defaultdict(list)
    discarded = 0

    for card in cards:
        art_id = card.get("illustration_id")
        if art_id:
            grouped[art_id].append(card)
        else:
            discarded += 1

    if discarded:
        logger.warning(
            "[TRANSFORM] %d card(s) discarded due to missing illustration_id", discarded
        )

    rows: list[dict] = []
    all_sets: set[str] = set()

    for art_id, group in grouped.items():
        group_sorted = sorted(group, key=lambda c: c.get("released_at", ""))
        base = group_sorted[0]

        card_sets = sorted({c["set_name"] for c in group_sorted if c.get("set_name")})
        all_sets.update(card_sets)

        price_usd = _safe_price(base)

        rows.append({
            "Number":          f"#{base.get('collector_number', '')}",
            "Have":            False,
            "Ignore":          False,
            "Name":            base.get("name", ""),
            "Original Set":    base.get("set_name", ""),
            "Art":             art_id,
            "Extras":          "",
            "Release Date":    base.get("released_at", ""),
            "Quantity":        0,
            "Owned Sets":      "",
            "All Sets By Art": ", ".join(card_sets),
            "Colors":          "".join(base.get("colors", [])) or "C",
            "Price USD":       price_usd,
            "Price BRL":       round(price_usd * CURRENCY_RATE_BRL, 2),
            "Premium":         "YES" if base.get("promo") else "NO",
        })

    df = pd.DataFrame(rows).drop_duplicates(subset=["Art"])
    logger.info("[TRANSFORM] %d unique records generated", len(df))

    if df.empty:
        return df, sorted(all_sets)

    return df.sort_values(by="Release Date").reset_index(drop=True), sorted(all_sets)
