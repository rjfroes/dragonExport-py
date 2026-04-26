"""
sheets_sync.py — Google Sheets synchronization.
Responsibility: open spreadsheet, ensure tabs, incremental merge, sets, and dashboard.
"""

import logging

import gspread
import pandas as pd

from .config import COLLECTION_HEADERS, MANUAL_FIELDS, SHEET_NAME

logger = logging.getLogger("dragonExport.sheets")


def open_sheet(client: gspread.Client) -> tuple[gspread.Spreadsheet, bool]:
    """
    Open (or create) the configured spreadsheet.
    Ask interactively whether it should be recreated from scratch.

    Returns:
        tuple[gspread.Spreadsheet, bool]:
            - Opened/created spreadsheet
            - Flag indicating whether dashboard should be updated

    Raises:
        RuntimeError: On unexpected API failure.
    """
    logger.info("[SHEET] Opening spreadsheet: %s", SHEET_NAME)
    answer = input("\nRecreate spreadsheet from scratch? (y/N): ").strip().lower()

    if answer == "y":
        sheet = client.create(SHEET_NAME)
        logger.info("[SHEET] Spreadsheet created")
        should_update_dashboard = True
    else:
        try:
            sheet = client.open(SHEET_NAME)
            logger.info("[SHEET] Spreadsheet found")
            dashboard_answer = input("Update dashboard formulas? (y/N): ").strip().lower()
            should_update_dashboard = dashboard_answer == "y"
        except gspread.exceptions.SpreadsheetNotFound:
            logger.warning("[SHEET] Spreadsheet not found - creating new")
            sheet = client.create(SHEET_NAME)
            should_update_dashboard = True
        except gspread.exceptions.APIError as exc:
            raise RuntimeError(f"Error accessing Google Sheets API: {exc}") from exc

    logger.info("[SHEET] https://docs.google.com/spreadsheets/d/%s", sheet.id)
    return sheet, should_update_dashboard


def ensure_tabs(sheet: gspread.Spreadsheet) -> None:
    """Create Collection, Sets, and Dashboard tabs if missing."""
    titles = {w.title for w in sheet.worksheets()}

    if "Collection" not in titles:
        logger.info("[TABS] Creating Collection tab")
        ws = sheet.add_worksheet("Collection", 5000, 20)
        ws.update([COLLECTION_HEADERS])

    if "Sets" not in titles:
        logger.info("[TABS] Creating Sets tab")
        sheet.add_worksheet("Sets", 2000, 2)

    if "Dashboard" not in titles:
        logger.info("[TABS] Creating Dashboard tab")
        sheet.add_worksheet("Dashboard", 100, 20)


def apply_checkboxes(sheet: gspread.Spreadsheet) -> None:
    """Apply checkbox validation to Have and Ignore columns in Collection tab."""
    logger.info("[CHECKBOX] Applying checkbox validation on Have/Ignore columns")
    ws = sheet.worksheet("Collection")

    sheet.batch_update({
        "requests": [{
            "setDataValidation": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": 1,
                    "endRowIndex": 5000,
                    "startColumnIndex": 1,
                    "endColumnIndex": 3,
                },
                "rule": {"condition": {"type": "BOOLEAN"}},
            }
        }]
    })


def update_collection(sheet: gspread.Spreadsheet, df: pd.DataFrame) -> None:
    """
    Update Collection tab with incremental merge.
    Preserve manual fields (Have, Ignore, Quantity, Extras, Owned Sets)
    from existing records.

    Raises:
        RuntimeError: On API read/write failures.
    """
    logger.info("[UPDATE] Updating Collection tab")
    ws = sheet.worksheet("Collection")

    try:
        existing_records = ws.get_all_records()
    except gspread.exceptions.APIError as exc:
        raise RuntimeError(f"Failed to read existing Collection: {exc}") from exc

    existing = pd.DataFrame(existing_records)

    if not existing.empty and "Art" in existing.columns:
        logger.info("[UPDATE] Incremental merge with %d existing records", len(existing))
        existing = existing.drop_duplicates(subset=["Art"])
        df = pd.merge(df, existing, on="Art", how="left", suffixes=("", "_old"))

        for col in MANUAL_FIELDS:
            old_col = f"{col}_old"
            if old_col in df.columns:
                df[col] = df[old_col].combine_first(df[col])

        df = df[[c for c in COLLECTION_HEADERS if c in df.columns]]
    else:
        logger.info("[UPDATE] No existing data - initial write")

    try:
        ws.update(
            [df.columns.values.tolist()] + df.values.tolist(),
            value_input_option="USER_ENTERED",
        )
    except gspread.exceptions.APIError as exc:
        raise RuntimeError(f"Failed to write Collection: {exc}") from exc

    logger.info("[UPDATE] Collection updated with %d rows", len(df))


def update_sets(sheet: gspread.Spreadsheet, sets: list[str]) -> None:
    """Overwrite Sets tab with sorted set names."""
    logger.info("[SETS] Updating Sets tab with %d sets", len(sets))
    ws = sheet.worksheet("Sets")
    ws.clear()
    ws.update([["Set Name"]] + [[s] for s in sets])


def update_dashboard(sheet: gspread.Spreadsheet) -> None:
    """Update Dashboard with FILTER formulas for dynamic counts."""
    logger.info("[DASHBOARD] Updating Dashboard with FILTER formulas")
    ws = sheet.worksheet("Dashboard")
    ws.clear()
    ws.update([
        ["Type", "Value"],
        ["Total",    '=ROWS(FILTER(Collection!D2:D;Collection!D2:D<>\"\";Collection!C2:C=FALSE))'],
        ["Obtidos",  '=ROWS(FILTER(Collection!D2:D;Collection!D2:D<>\"\";Collection!B2:B=TRUE;Collection!C2:C=FALSE))'],
        ["Faltando", '=ROWS(FILTER(Collection!D2:D;Collection!D2:D<>\"\";Collection!B2:B=FALSE;Collection!C2:C=FALSE))'],
        ["%",        "=IFERROR(FIXED((B3/B2)*100;2);0)"],
    ])
    logger.info("[DASHBOARD] Updated")
