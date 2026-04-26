"""
auth.py — Google OAuth 2.0 authentication.
Responsibility: load/refresh credentials and return an authenticated gspread client.
"""

import logging
import os
import pickle

import gspread
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import CREDENTIALS_FILE, GOOGLE_SCOPES, TOKEN_FILE

logger = logging.getLogger("dragonExport.auth")


def get_client() -> gspread.Client:
    """
    Return an authenticated gspread client.
    Reuse cached token when available; open OAuth flow otherwise.

    Raises:
        FileNotFoundError: If credentials.json is not found.
    """
    logger.info("[AUTH] Starting authentication")
    creds = None

    if os.path.exists(TOKEN_FILE):
        logger.debug("[AUTH] Loading token from %s", TOKEN_FILE)
        with open(TOKEN_FILE, "rb") as fh:
            creds = pickle.load(fh)

    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Credentials file not found: {CREDENTIALS_FILE}. "
                "Check CREDENTIALS_FILE in .env"
            )
        logger.info("[AUTH] Credentials expired or missing - opening OAuth flow")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, GOOGLE_SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as fh:
            pickle.dump(creds, fh)
        logger.debug("[AUTH] Token saved to %s", TOKEN_FILE)

    logger.info("[AUTH] Authenticated successfully")
    return gspread.authorize(creds)
