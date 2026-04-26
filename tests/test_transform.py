"""
Testes unitários para as funções de transformação e merge incremental.
Execute com: pytest tests/ -v
"""

import pandas as pd
import pytest

# Importar funções a testar
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.transform import _safe_price, transform_cards as transform
from src.config import COLLECTION_HEADERS, MANUAL_FIELDS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_card(
    illustration_id="art-001",
    name="Shivan Dragon",
    set_name="Alpha",
    released_at="1993-08-05",
    collector_number="1",
    colors=None,
    price_usd="10.00",
    promo=False,
):
    return {
        "illustration_id": illustration_id,
        "name": name,
        "set_name": set_name,
        "released_at": released_at,
        "collector_number": collector_number,
        "colors": ["R"] if colors is None else colors,
        "prices": {"usd": price_usd},
        "promo": promo,
    }


# ---------------------------------------------------------------------------
# _safe_price
# ---------------------------------------------------------------------------

class TestSafePrice:
    def test_valid_price(self):
        card = make_card(price_usd="5.99")
        assert _safe_price(card) == 5.99

    def test_none_price_returns_zero(self):
        card = make_card(price_usd=None)
        assert _safe_price(card) == 0.0

    def test_empty_string_returns_zero(self):
        card = {"prices": {"usd": ""}}
        assert _safe_price(card) == 0.0

    def test_invalid_string_returns_zero(self):
        card = {"prices": {"usd": "N/A"}}
        assert _safe_price(card) == 0.0

    def test_missing_prices_key(self):
        card = {}
        assert _safe_price(card) == 0.0

    def test_zero_price(self):
        card = make_card(price_usd="0.00")
        assert _safe_price(card) == 0.0


# ---------------------------------------------------------------------------
# transform
# ---------------------------------------------------------------------------

class TestTransform:
    def test_basic_single_card(self):
        cards = [make_card()]
        df, sets = transform(cards)
        assert len(df) == 1
        assert "Shivan Dragon" in df["Name"].values
        assert "Alpha" in sets

    def test_columns_present(self):
        cards = [make_card()]
        df, _ = transform(cards)
        for col in COLLECTION_HEADERS:
            assert col in df.columns, f"Coluna ausente: {col}"

    def test_price_brl_calculated(self):
        cards = [make_card(price_usd="10.00")]
        df, _ = transform(cards)
        # CURRENCY_RATE_BRL default = 5.0
        assert df.iloc[0]["Price USD"] == 10.0
        assert df.iloc[0]["Price BRL"] == pytest.approx(50.0)

    def test_card_without_illustration_id_discarded(self):
        cards = [
            make_card(illustration_id="art-001"),
            {"name": "No Art", "set_name": "Test", "released_at": "2020-01-01",
             "illustration_id": None, "prices": {"usd": "1.00"}},
        ]
        df, _ = transform(cards)
        assert len(df) == 1
        assert "No Art" not in df["Name"].values

    def test_dedup_by_art_id(self):
        cards = [
            make_card(illustration_id="art-001", set_name="Alpha"),
            make_card(illustration_id="art-001", set_name="Beta"),
        ]
        df, _ = transform(cards)
        assert len(df) == 1

    def test_all_sets_by_art_combined(self):
        cards = [
            make_card(illustration_id="art-001", set_name="Alpha"),
            make_card(illustration_id="art-001", set_name="Beta"),
        ]
        df, sets = transform(cards)
        assert "Alpha" in df.iloc[0]["All Sets By Art"]
        assert "Beta" in df.iloc[0]["All Sets By Art"]
        assert "Alpha" in sets
        assert "Beta" in sets

    def test_colors_missing_defaults_to_C(self):
        card = make_card(colors=[])
        df, _ = transform([card])
        assert df.iloc[0]["Colors"] == "C"

    def test_colorless_card(self):
        card = make_card(colors=["C"])
        df, _ = transform([card])
        assert df.iloc[0]["Colors"] == "C"

    def test_premium_flag(self):
        promo_card = make_card(illustration_id="art-promo", promo=True)
        normal_card = make_card(illustration_id="art-normal", promo=False)
        df, _ = transform([promo_card, normal_card])
        promo_row = df[df["Art"] == "art-promo"].iloc[0]
        normal_row = df[df["Art"] == "art-normal"].iloc[0]
        assert promo_row["Premium"] == "YES"
        assert normal_row["Premium"] == "NO"

    def test_empty_cards_returns_empty_df(self):
        df, sets = transform([])
        assert len(df) == 0
        assert len(sets) == 0

    def test_have_ignore_quantity_default_values(self):
        cards = [make_card()]
        df, _ = transform(cards)
        row = df.iloc[0]
        assert row["Have"] == False
        assert row["Ignore"] == False
        assert row["Quantity"] == 0
        assert row["Owned Sets"] == ""

    def test_oldest_card_selected_as_base(self):
        cards = [
            make_card(illustration_id="art-001", set_name="Beta",  released_at="1993-12-01"),
            make_card(illustration_id="art-001", set_name="Alpha", released_at="1993-08-05"),
        ]
        df, _ = transform(cards)
        assert df.iloc[0]["Original Set"] == "Alpha"


# ---------------------------------------------------------------------------
# Merge incremental (simulando update_collection)
# ---------------------------------------------------------------------------

class TestMergeIncremental:
    """Verifica que campos manuais são preservados após merge com dados existentes."""

    def _merge(self, new_df: pd.DataFrame, existing_df: pd.DataFrame) -> pd.DataFrame:
        """Replica a lógica de merge de update_collection sem dependência de I/O."""
        if existing_df.empty or "Art" not in existing_df.columns:
            return new_df

        existing_df = existing_df.drop_duplicates(subset=["Art"])
        merged = pd.merge(new_df, existing_df, on="Art", how="left", suffixes=("", "_old"))

        for col in MANUAL_FIELDS:
            old_col = f"{col}_old"
            if old_col in merged.columns:
                merged[col] = merged[old_col].combine_first(merged[col])

        return merged[[c for c in COLLECTION_HEADERS if c in merged.columns]]

    def test_have_preserved_after_merge(self):
        new_df = pd.DataFrame([{
            "Art": "art-001", "Name": "Dragon", "Have": False, "Ignore": False,
            "Quantity": 0, "Extras": "", "Owned Sets": "",
            "Number": "#1", "Original Set": "Alpha", "Release Date": "1993-08-05",
            "All Sets By Art": "Alpha", "Colors": "R",
            "Price USD": 5.0, "Price BRL": 25.0, "Premium": "NO",
        }])
        existing_df = pd.DataFrame([{
            "Art": "art-001", "Have": True, "Ignore": False,
            "Quantity": 2, "Extras": "foil", "Owned Sets": "Alpha",
        }])
        result = self._merge(new_df, existing_df)
        assert result.iloc[0]["Have"] == True
        assert result.iloc[0]["Quantity"] == 2
        assert result.iloc[0]["Extras"] == "foil"

    def test_new_card_not_in_existing_keeps_defaults(self):
        new_df = pd.DataFrame([{
            "Art": "art-002", "Name": "New Dragon", "Have": False, "Ignore": False,
            "Quantity": 0, "Extras": "", "Owned Sets": "",
            "Number": "#2", "Original Set": "Beta", "Release Date": "1993-12-01",
            "All Sets By Art": "Beta", "Colors": "R",
            "Price USD": 1.0, "Price BRL": 5.0, "Premium": "NO",
        }])
        existing_df = pd.DataFrame([{
            "Art": "art-001", "Have": True, "Ignore": False,
            "Quantity": 1, "Extras": "", "Owned Sets": "",
        }])
        result = self._merge(new_df, existing_df)
        row = result[result["Art"] == "art-002"].iloc[0]
        assert row["Have"] is False
        assert row["Quantity"] == 0

    def test_empty_existing_returns_new_as_is(self):
        new_df = pd.DataFrame([{
            col: "val" for col in COLLECTION_HEADERS
        }])
        result = self._merge(new_df, pd.DataFrame())
        assert len(result) == 1
