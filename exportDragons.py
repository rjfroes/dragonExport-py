"""
exportDragons.py — Ponto de entrada do MTG Dragons Tracker.

A lógica de negócio está em src/:
  src/config.py       — configuração centralizada
  src/auth.py         — autenticação Google OAuth
  src/fetch.py        — busca Scryfall com retry
  src/transform.py    — transformação e normalização de cartas
  src/sheets_sync.py  — sincronização com Google Sheets
  src/main.py         — orquestrador do pipeline

Execute:
    python exportDragons.py
"""

from src.main import run

if __name__ == "__main__":
    run()