# PersonalFinance — Tinkoff Statement Analyzer

Parses Tinkoff bank statement PDFs, categorizes transactions, and uploads a formatted summary to Google Sheets.

## Pipeline

```
parse_statements.py  →  categorize.py  →  upload_to_sheets.py
       ↓                     ↓                     ↓
  parsed/all.csv      categorized.csv       Google Sheets
```

## Setup

```bash
pip install pdfplumber gspread google-auth
```

Place your Tinkoff PDF statements in the data directory (default: `../../Личное/Мои деньги/`).
Override with env var:

```bash
export PERSONAL_FINANCE_DATA_DIR=/path/to/your/statements
```

For Google Sheets upload, place a service account JSON at one of:
- `../../.credentials/credentials.json`
- `../../Projects/FinanceBot/service_account.json`
- `../../Projects/ChatManager/service_account.json`

## Personal cash expenses

Cash expenses (rent, gym, etc.) are stored in `personal_config.py` (gitignored):

```bash
cp personal_config.example.py personal_config.py
# edit personal_config.py with your actual amounts
```

## Usage

```bash
python parse_statements.py   # extract transactions from PDFs -> parsed/all.csv
python categorize.py         # categorize + add cash expenses -> parsed/categorized.csv
python upload_to_sheets.py   # upload to Google Sheets
```

## Output

- `parsed/all.csv` — raw transactions from all PDFs
- `parsed/categorized.csv` — categorized transactions incl. cash expenses
- `parsed/summary.txt` — balance check per PDF
- `parsed/final_summary.txt` — expense summary by category and period
- Google Sheet with two tabs: **Транзакции** (all rows) and **Сводка по категориям** (grouped summary)
