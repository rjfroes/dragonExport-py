# MTG Dragons Tracker

Exports Dragon cards from Scryfall to a Google Sheets spreadsheet, with incremental merge support for manual collection fields.

## Prerequisites

- Python 3.10+
- Google account with Google Sheets / Drive access
- Google OAuth 2.0 credentials file (`credentials.json`)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Google credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project and enable **Google Sheets API** and **Google Drive API**
3. Create OAuth 2.0 credentials (type: Desktop App)
4. Download the JSON file and save it as `credentials.json` in the project root

> `credentials.json` and `token.pickle` are listed in `.gitignore`. Never commit them.

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env if needed
```

Available variables (all with safe defaults):

| Variable              | Default             | Description                            |
|-----------------------|---------------------|----------------------------------------|
| `SHEET_NAME`          | MTG Dragons Tracker | Google Drive spreadsheet name          |
| `SCRYFALL_QUERY`      | t:dragon game:paper | Scryfall search query                  |
| `SCRYFALL_UNIQUE`     | prints              | Scryfall uniqueness mode (prints/cards)|
| `HTTP_TIMEOUT`        | 30                  | Request timeout in seconds             |
| `MAX_PAGES`           | 200                 | Pagination page limit                  |
| `HTTP_RETRY_ATTEMPTS` | 3                   | Retry attempts on HTTP failures        |
| `HTTP_RETRY_BACKOFF`  | 2                   | Exponential backoff base               |
| `CURRENCY_RATE_BRL`   | 5.0                 | USD to BRL conversion rate             |
| `CREDENTIALS_FILE`    | credentials.json    | Credentials file path                  |
| `TOKEN_FILE`          | token.pickle        | OAuth token cache path                 |
| `LOG_LEVEL`           | INFO                | Log level (DEBUG/INFO/WARNING)         |

## Run

```bash
python exportDragons.py
```

On first run, a browser opens for OAuth login. The token is stored in `token.pickle` for future executions.

## First Run Checklist

1. Confirm `credentials.json` exists in the project root.
2. Create `.env` from `.env.example` and review key variables.
3. Run `python exportDragons.py`.
4. Complete OAuth login in the browser window.
5. Return to terminal and choose create/update options.

Interactive flow:

1. First prompt:

```text
Recreate spreadsheet from scratch? (y/N):
```

- `y`: creates a new spreadsheet from scratch.
- Enter / any other value: uses the existing spreadsheet (incremental update).

2. If existing spreadsheet mode is selected and the spreadsheet exists, second prompt:

```text
Update dashboard formulas? (y/N):
```

- `y`: updates dashboard formulas.
- Enter / any other value: does not update dashboard formulas (default is No).

## Generated Spreadsheet Structure

| Tab         | Content                                                     |
|-------------|-------------------------------------------------------------|
| Collection  | All unique Dragon artworks and collection fields            |
| Sets        | Sorted list of all sets containing Dragon cards             |
| Dashboard   | Counters: Total, Collected, Missing, Completion percentage  |

### Collection tab columns

`Number` · `Have` · `Ignore` · `Name` · `Original Set` · `Art` · `Extras` · `Release Date` · `Quantity` · `Owned Sets` · `All Sets By Art` · `Colors` · `Price USD` · `Price BRL` · `Premium`

Manual fields (preserved during incremental merge): `Have`, `Ignore`, `Quantity`, `Extras`, `Owned Sets`

## Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

Current suite covers transformation, incremental merge, HTTP retry behavior, and mocked integration paths.

## Project Structure

```text
dragonExport/
├── exportDragons.py        # Thin CLI entry point
├── src/
│   ├── auth.py             # Google OAuth authentication
│   ├── config.py           # Environment/config constants
│   ├── fetch.py            # Scryfall HTTP fetch/retry
│   ├── main.py             # Pipeline orchestrator
│   ├── sheets_sync.py      # Google Sheets operations
│   └── transform.py        # Data transformation logic
├── tests/
│   ├── test_transform.py
│   └── test_integration.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Security

- OAuth credentials are never hardcoded in source code.
- `credentials.json` and `token.pickle` are ignored by git.
- Runtime configuration comes from environment variables with safe defaults.
- HTTP retry is limited to transient failures (network / 429 / 503).

## Troubleshooting

| Error | Cause | Solution |
|------|-------|----------|
| `FileNotFoundError: credentials.json` | Missing credentials file | Check `CREDENTIALS_FILE` in `.env` |
| `SpreadsheetNotFound` | Spreadsheet does not exist | The script creates it automatically |
| `Failed after N attempts` | API temporarily unavailable | Check network/API availability and retry |
| Expired token | Invalid `token.pickle` cache | Delete `token.pickle` and authenticate again |
