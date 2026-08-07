# Net Worth Dashboard — Requirements

Static web dashboard for tracking and projecting personal net worth. Password-gated, mobile-responsive, GitHub Pages hosted.

## Live

- **URL:** https://macdude95.github.io/NetWorth/
- **Repo:** https://github.com/macdude95/NetWorth
- **Password:** disabled for testing — set via `python3 generate.py --set-password PWD` and flip `password_enabled` to `True` in `generate.py`

## Architecture

```
NetWorth/
├── config.json          # Account definitions (retirement/non-retirement, liquid/illiquid, growth rates)
├── data/
│   └── snapshots.json   # Chronological net worth snapshots (the source of truth)
├── templates/
│   └── index.html       # HTML/JS template with Chart.js charts + milestone engine
├── generate.py          # Reads config + snapshots → injects JSON data → writes docs/index.html
├── docs/
│   └── index.html       # Built output, deployed to GitHub Pages
└── REQUIREMENTS.md      # This file
```

`generate.py` computes derived series (net worth total, ex-housing, retirement, non-retirement) from raw account snapshots, hashes the password, and injects everything into the template as a `const DATA = {...}` JSON blob. All chart rendering, projections, and milestones run client-side.

## Data model

### `data/snapshots.json`

```json
{
  "snapshots": [
    {
      "date": "2026-08-01",
      "accounts": {
        "checking": 12500,
        "hysa": 70000,
        "brokerage_taxable": 178000,
        "brokerage_roth": 265000,
        "retirement_401k": 330000,
        "home_equity": 475000
      },
      "liabilities": {
        "mortgage_balance": 261000
      }
    }
  ]
}
```

Each account exists as a key in `accounts`. Liabilities (mortgage) reduce net worth. `home_equity` is net of the mortgage (already equity, not gross value).

### `config.json`

Defines account metadata and projection settings. See file for full schema. Key fields:
- `accounts.<key>.bucket`: `"retirement"` or `"non_retirement"`
- `accounts.<key>.liquid`: `true`/`false` (home equity is illiquid)
- `accounts.<key>.growth_rate`: annual nominal rate for projection defaults
- `password.hash` + `password.salt`: SHA-256 credentials

## Features

### 1. Net Worth Chart (total + ex-housing)
- Two lines on one chart: total net worth + liquid (excl. home equity)
- Timeframe toggles: YTD, 1Y, 5Y, All

### 2. Projections (30 years)
- **Inputs:** annual expenses, annual income, investment growth %
- **Computation:** client-side Monte Carlo (200 runs, 15% annual vol)
- **Output:** median projection line + p10/p90 shaded band
- **Model:** net savings (income − expenses) are invested at the given growth rate, starting from current net worth
- No timeframe toggle — fixed 30-year horizon (like Robinhood Future)

### 3. Retirement vs Non-Retirement
- Stacked bar chart
- Timeframe toggles: YTD, 1Y, 5Y, All

### 4. Milestones & Achievements

Four categories with progress bars and projected cross-dates:

| Category | Milestones |
|---|---|
| 💰 Liquid Net Worth | $1M, $2M, $3M, $4M, $5M, $7.5M, $10M |
| 🔥 FIRE | Coast FIRE, Lean FIRE (25× expenses), Full FIRE (33×), Fat FIRE (40×) |
| 🌉 Bridge Fund | 1yr, 3yr, 5yr expenses in non-retirement accounts |
| 🏠 Home Equity | 50%, 75%, 100% ownership (mortgage-free) |

- **Horizontal milestone lines** on projection chart for liquid NW + FIRE targets
- **Collapsible achievements panel** (click "🏆 Achievements") with progress bars, estimated cross-dates, and color coding (green = done, amber = close, gray = distant)
- FIRE and bridge milestones recalculate live when expense input changes

### 5. Password Gate
- SHA-256 client-side gate
- Feature-flagged off (`password_enabled: false`) during development
- To re-enable: set `password_enabled` to `True` in `generate.py` and rebuild

### 6. Stats Row
- Latest net worth with delta from previous snapshot
- Liquid NW (excl. home)
- Retirement total
- Snapshot count

## Cron — Monthly Data Collection

- **Schedule:** 1st of each month, 9am PT
- **Job ID:** `b58d31ae1a2a` (in Hermes cron)
- **Behavior:** posts to #projects thread asking for 7 account balances; on reply, appends snapshot, regenerates dashboard, and `git push`es

## Future / Todo

- [ ] Real data import (YNAB CSV or manual historical dump)
- [ ] Coast FIRE calculation (proper compound-to-65 formula)
- [ ] Retirement balance ratio milestone ("good balance" between retirement and non-retirement)
- [ ] Account-specific milestone tracking (e.g., "$500K in taxable")
- [ ] Password re-enable when ready for public hosting
- [ ] Income growth rate input (separate from investment growth)
- [ ] Dark/light theme toggle
- [ ] CSV export of snapshots
