# Changelog

## [1.0.0] — 2026-04-26

### Features
- Fetches all Dragon cards from Scryfall API with safe pagination and configurable query.
- Exports unique artworks to a Google Sheets spreadsheet with incremental merge — manual fields (`Have`, `Ignore`, `Quantity`, `Extras`, `Owned Sets`) are preserved across runs.
- Populates three tabs: **Collection** (card data), **Sets** (sorted set list), **Dashboard** (FILTER-based counters).
- Interactive CLI prompts: recreate spreadsheet from scratch or update existing; optionally refresh dashboard formulas (default: No).
- Google OAuth 2.0 authentication with local token cache (`token.pickle`).
- HTTP resilience: configurable timeout, exponential backoff retry, immediate failure on 4xx errors.
- Environment-based configuration via `.env` — no hardcoded secrets.
- Modular architecture under `src/`: `auth`, `config`, `fetch`, `transform`, `sheets_sync`, `main`.
- 37 automated tests covering transformation logic, incremental merge, HTTP retry, and mocked integrations.
