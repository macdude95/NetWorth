# Net Worth Dashboard

A personal net worth tracking and projection dashboard. Track liquid net worth, retirement vs. non-retirement breakdowns, and forward projections with customizable assumptions.

**Live:** https://macdude95.github.io/NetWorth/

## Features

- **Net Worth tracking** — liquid net worth and total (incl. home equity) over time, with month-over-month deltas
- **Projections** — forward projection split into two stacked components: your current investments compounding vs. future contributions, driven by adjustable growth rate, income, tax rate, expenses, and time horizon
- **Retirement breakdown** — stacked bar chart over time + doughnut chart for the current retirement vs. non-retirement split (toggle between views)
- **Achievements** — milestone tracker for liquid net worth ($1M–$10M), FIRE milestones (Coast/Lean/Full/Fat), bridge fund, and home equity, with progress bars and estimated completion dates
- **Mobile responsive** — designed for phone viewing, tap-friendly controls

## How it works

Static site, no backend. A Python script reads account data from JSON and generates a single self-contained HTML file deployed to GitHub Pages.

### Project structure

```
NetWorth/
├── data/
│   └── snapshots.json      # investment account balances, home equity, mortgage, income, expenses
├── templates/
│   └── index.html          # HTML/JS/CSS template (Chart.js)
├── docs/
│   └── index.html          # generated output served by GitHub Pages
├── generate.py             # builds docs/index.html from data + template
└── verify.py               # Playwright headless verification
```

### Build

```bash
python3 generate.py
```

### Verify

```bash
python3 verify.py    # runs headless Chromium, checks all charts render
```

### Set a password (optional)

The dashboard supports a client-side password gate (SHA-256, feature-flagged off by default):

```bash
python3 generate.py --set-password YOUR_PASSWORD
```

Then set `password_enabled` to `True` in `generate.py` to enable it.

## Data model

`data/snapshots.json` holds monthly snapshots. Each snapshot:

```json
{
  "date": "2026-08-01",
  "accounts": {
    "michael_robinhood_retirement": 184585.27,
    "michael_robinhood_taxable": 465434.97,
    "michael_fidelity_401k": 297426.72,
    "chris_robinhood_retirement": 96626.55,
    "chris_fidelity_401k": 69146.73,
    "chris_investco_ira": 11636.85
  },
  "home_equity": 642684.22,
  "mortgage_balance": 565396.78,
  "income": 400000,
  "expenses": 108000
}
```

Accounts are classified as retirement vs. non-retirement by keyword (`retirement`, `401k`, `ira` in the key name). Home equity and mortgage are tracked separately; liquid net worth excludes both.
