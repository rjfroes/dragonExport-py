"""
config.py — Centralized configuration via environment variables.
All project constants live here; no module should read os.getenv directly.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# Google Sheets
SHEET_NAME: str = os.getenv("SHEET_NAME", "MTG Dragons Tracker")

# Scryfall API
SCRYFALL_QUERY: str  = os.getenv("SCRYFALL_QUERY", "t:dragon game:paper")
SCRYFALL_UNIQUE: str = os.getenv("SCRYFALL_UNIQUE", "prints")

# HTTP
HTTP_TIMEOUT: int      = int(os.getenv("HTTP_TIMEOUT", "30"))
MAX_PAGES: int         = int(os.getenv("MAX_PAGES", "200"))
RETRY_ATTEMPTS: int    = int(os.getenv("HTTP_RETRY_ATTEMPTS", "3"))
RETRY_BACKOFF: float   = float(os.getenv("HTTP_RETRY_BACKOFF", "2"))

# Domain
CURRENCY_RATE_BRL: float = float(os.getenv("CURRENCY_RATE_BRL", "5.0"))

# Authentication
CREDENTIALS_FILE: str = os.getenv("CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE: str       = os.getenv("TOKEN_FILE", "token.pickle")

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Google OAuth scopes
GOOGLE_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Collection tab schema
COLLECTION_HEADERS: list[str] = [
    "Number", "Have", "Ignore", "Name", "Original Set", "Art", "Extras",
    "Release Date", "Quantity", "Owned Sets", "All Sets By Art",
    "Colors", "Price USD", "Price BRL", "Premium",
]

# Fields preserved during incremental merge
MANUAL_FIELDS: list[str] = ["Have", "Ignore", "Quantity", "Extras", "Owned Sets"]


def setup_logging() -> None:
    """Configure root logging for the project."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
