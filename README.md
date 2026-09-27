# Sponsor Lead Automation extraction (P&S)

Finds sponsor companies for E-Summits held in Hyderabad, pulls any publicly
listed contact info (email, phone, LinkedIn), and saves it to a local Excel
file (`sponsors.xlsx`) — no cloud account or billing needed.

## Setup

1. `pip install -r requirements.txt`
2. `playwright install chromium`

That's it for scraping — no API keys, no service account, no billing.

Optional, for hands-off LinkedIn login: copy `.env.example` to `.env` and fill
in `LINKEDIN_EMAIL`/`LINKEDIN_PASSWORD` yourself (never paste these into a
chat with anyone, including Claude — `.env` is gitignored and read locally
only). Without this, `linkedin_enrich.py` just pauses for you to log in
manually in the browser it opens. Either way, LinkedIn's 2FA/CAPTCHA
checkpoints can't be automated, so it may still fall back to asking you to
finish logging in by hand.

## Usage

Run the full pipeline:

```
python main.py
```

Run stages individually, or skip ones you've already done:

```
python discover.py                      # just find event URLs
python scrape_sponsors.py               # just scrape sponsor info from seeds.csv
python linkedin_enrich.py --dry-run     # preview LinkedIn searches without running them
python linkedin_enrich.py               # actually run LinkedIn enrichment (see warning below)
python excel_writer.py                  # just write cached rows to sponsors.xlsx

python main.py --skip-discover --skip-linkedin
```

First LinkedIn enrichment run opens a visible browser — log in manually when
prompted, the session is cached in `data/storage_state.json` after that.

Results land in `sponsors.xlsx` in this folder — open it directly in Excel.
Set `OUTPUT_XLSX_PATH` (env var) to change where it's written.

## ⚠️ LinkedIn warning

`linkedin_enrich.py` automates your own logged-in LinkedIn session, which
goes against LinkedIn's Terms of Service and can get an account rate-limited
or restricted. It caps lookups per run and adds delays to reduce risk, but
the risk isn't zero — use sparingly, and prefer `--dry-run` first.

## Data files (not committed)

- `data/seeds.csv` — discovered event URLs
- `data/sponsors_cache.csv` — scraped/enriched sponsor rows (local checkpoint)
- `data/storage_state.json` — cached LinkedIn browser session
- `sponsors.xlsx` — the final output spreadsheet
