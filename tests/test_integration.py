"""
Integration tests with mocked external APIs (Scryfall and Google Sheets).
Run with: pytest tests/ -v
"""

import sys
import os
from unittest.mock import MagicMock, patch

import gspread
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.fetch as fetch_mod
import src.sheets_sync as sheets_mod
import src.config as config_mod
import src.main as main_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRYFALL_PAGE_1 = {
    "data": [
        {
            "illustration_id": "art-001",
            "name": "Shivan Dragon",
            "set_name": "Alpha",
            "released_at": "1993-08-05",
            "collector_number": "1",
            "colors": ["R"],
            "prices": {"usd": "10.00"},
            "promo": False,
        }
    ],
    "has_more": False,
}


# ---------------------------------------------------------------------------
# fetch_cards()
# ---------------------------------------------------------------------------

class TestFetch:
    def test_single_page_returns_cards(self):
        with patch("src.fetch._http_get", return_value=SCRYFALL_PAGE_1) as mock_get:
            cards = fetch_mod.fetch_cards()
        assert len(cards) == 1
        assert cards[0]["name"] == "Shivan Dragon"
        mock_get.assert_called_once()

    def test_pagination_follows_next_page(self):
        page1 = {
            "data": [{"illustration_id": "art-001", "name": "Dragon A",
                      "set_name": "S1", "released_at": "2020-01-01",
                      "collector_number": "1", "colors": ["R"],
                      "prices": {"usd": "1.00"}, "promo": False}],
            "next_page": "https://api.scryfall.com/cards/search?page=2",
        }
        page2 = {
            "data": [{"illustration_id": "art-002", "name": "Dragon B",
                      "set_name": "S2", "released_at": "2021-01-01",
                      "collector_number": "2", "colors": ["R"],
                      "prices": {"usd": "2.00"}, "promo": False}],
        }
        with patch("src.fetch._http_get", side_effect=[page1, page2]):
            cards = fetch_mod.fetch_cards()
        assert len(cards) == 2

    def test_missing_data_field_raises_valueerror(self):
        bad_payload = {"object": "error", "code": "not_found"}
        with patch("src.fetch._http_get", return_value=bad_payload):
            with pytest.raises(ValueError, match="missing 'data' field"):
                fetch_mod.fetch_cards()

    def test_max_pages_limit_respected(self, monkeypatch):
        monkeypatch.setattr(fetch_mod, "MAX_PAGES", 2)
        infinite_page = {
            "data": [{"illustration_id": "art-x", "name": "X",
                      "set_name": "S", "released_at": "2020-01-01",
                      "collector_number": "1", "colors": [],
                      "prices": {"usd": None}, "promo": False}],
            "next_page": "https://api.scryfall.com/cards/search?page=next",
        }
        with patch("src.fetch._http_get", return_value=infinite_page):
            cards = fetch_mod.fetch_cards()
        assert len(cards) == 2  # MAX_PAGES=2 pages


# ---------------------------------------------------------------------------
# _http_get() retry e timeout
# ---------------------------------------------------------------------------

class TestHttpGet:
    def test_timeout_retries_and_raises(self):
        import requests as req
        with patch("src.fetch.requests.get",
                   side_effect=req.exceptions.Timeout), \
             patch("src.fetch.time.sleep"):
            with pytest.raises(RuntimeError, match="Failed after"):
                fetch_mod._http_get("https://example.com")

    def test_http_4xx_raises_immediately(self):
        import requests as req
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_err = req.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_err

        with patch("src.fetch.requests.get", return_value=mock_response):
            with pytest.raises(RuntimeError, match="HTTP error 404"):
                fetch_mod._http_get("https://example.com")

    def test_success_returns_json(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": []}

        with patch("src.fetch.requests.get", return_value=mock_response):
            result = fetch_mod._http_get("https://example.com")
        assert result == {"data": []}


# ---------------------------------------------------------------------------
# ensure_tabs()
# ---------------------------------------------------------------------------

class TestEnsureTabs:
    def _make_sheet(self, existing_tabs):
        sheet = MagicMock()
        sheet.worksheets.return_value = [
            MagicMock(title=t) for t in existing_tabs
        ]
        return sheet

    def test_creates_missing_tabs(self):
        sheet = self._make_sheet([])
        sheets_mod.ensure_tabs(sheet)
        titles_created = [c.args[0] for c in sheet.add_worksheet.call_args_list]
        assert "Collection" in titles_created
        assert "Sets" in titles_created
        assert "Dashboard" in titles_created

    def test_skips_existing_tabs(self):
        sheet = self._make_sheet(["Collection", "Sets", "Dashboard"])
        sheets_mod.ensure_tabs(sheet)
        sheet.add_worksheet.assert_not_called()

    def test_creates_only_missing(self):
        sheet = self._make_sheet(["Collection"])
        sheets_mod.ensure_tabs(sheet)
        titles_created = [c.args[0] for c in sheet.add_worksheet.call_args_list]
        assert "Collection" not in titles_created
        assert "Sets" in titles_created
        assert "Dashboard" in titles_created


# ---------------------------------------------------------------------------
# open_sheet() decision flow
# ---------------------------------------------------------------------------

class TestOpenSheet:
    def test_recreate_yes_returns_true_flag(self):
        client = MagicMock()
        sheet = MagicMock(id="new-sheet-id")
        client.create.return_value = sheet

        with patch("builtins.input", return_value="y"):
            got_sheet, should_update_dashboard = sheets_mod.open_sheet(client)

        assert got_sheet is sheet
        assert should_update_dashboard is True
        client.create.assert_called_once_with(config_mod.SHEET_NAME)
        client.open.assert_not_called()

    def test_existing_sheet_prompts_dashboard_default_no(self):
        client = MagicMock()
        sheet = MagicMock(id="existing-sheet-id")
        client.open.return_value = sheet

        with patch("builtins.input", side_effect=["", ""]):
            got_sheet, should_update_dashboard = sheets_mod.open_sheet(client)

        assert got_sheet is sheet
        assert should_update_dashboard is False
        client.open.assert_called_once_with(config_mod.SHEET_NAME)
        client.create.assert_not_called()

    def test_existing_sheet_prompts_dashboard_yes(self):
        client = MagicMock()
        sheet = MagicMock(id="existing-sheet-id")
        client.open.return_value = sheet

        with patch("builtins.input", side_effect=["n", "y"]):
            got_sheet, should_update_dashboard = sheets_mod.open_sheet(client)

        assert got_sheet is sheet
        assert should_update_dashboard is True
        client.open.assert_called_once_with(config_mod.SHEET_NAME)
        client.create.assert_not_called()

    def test_missing_sheet_auto_create_returns_true(self):
        client = MagicMock()
        sheet = MagicMock(id="auto-created-id")
        client.open.side_effect = gspread.exceptions.SpreadsheetNotFound()
        client.create.return_value = sheet

        with patch("builtins.input", return_value="n"):
            got_sheet, should_update_dashboard = sheets_mod.open_sheet(client)

        assert got_sheet is sheet
        assert should_update_dashboard is True
        client.open.assert_called_once_with(config_mod.SHEET_NAME)
        client.create.assert_called_once_with(config_mod.SHEET_NAME)


# ---------------------------------------------------------------------------
# main.run() dashboard conditional update
# ---------------------------------------------------------------------------

class TestMainRunDashboardFlag:
    def test_run_updates_dashboard_when_flag_true(self):
        with patch("src.main.setup_logging"), \
             patch("src.main.get_client", return_value=MagicMock()), \
             patch("src.main.open_sheet", return_value=(MagicMock(), True)), \
             patch("src.main.ensure_tabs"), \
             patch("src.main.fetch_cards", return_value=[]), \
               patch("src.main.transform_cards", return_value=([], [])), \
             patch("src.main.update_sets"), \
             patch("src.main.update_collection"), \
             patch("src.main.apply_checkboxes"), \
             patch("src.main.update_dashboard") as dashboard_mock:
            main_mod.run()

        dashboard_mock.assert_called_once()

    def test_run_skips_dashboard_when_flag_false(self):
        with patch("src.main.setup_logging"), \
             patch("src.main.get_client", return_value=MagicMock()), \
             patch("src.main.open_sheet", return_value=(MagicMock(), False)), \
             patch("src.main.ensure_tabs"), \
             patch("src.main.fetch_cards", return_value=[]), \
               patch("src.main.transform_cards", return_value=([], [])), \
             patch("src.main.update_sets"), \
             patch("src.main.update_collection"), \
             patch("src.main.apply_checkboxes"), \
             patch("src.main.update_dashboard") as dashboard_mock:
            main_mod.run()

        dashboard_mock.assert_not_called()
