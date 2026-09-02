# Net Worth Dashboard — Requirements

Static web dashboard for tracking and projecting personal net worth. Password-gated, mobile-responsive, GitHub Pages hosted.

## Live

- **URL:** https://macdude95.github.io/NetWorth/
- **Repo:** https://github.com/macdude95/NetWorth
- **Password:** `vesper` (client-side casual privacy gate; not suitable for protecting secrets)

## Architecture

```
NetWorth/
├── config.json          # Account definitions and projection defaults
├── data/
│   └── snapshots.json   # Chronological net worth snapshots (the source of truth)
├── templates/
│   └── index.html       # HTML/JS template with Chart.js charts + milestone engine
├── generate.py          # Reads config + snapshots → injects JSON data → writes docs/index.html
├── docs/
│   └── index.html       # Built output, deployed to GitHub Pages
└── REQUIREMENTS.md      # This file
```

`generate.py` computes derived series (net worth total, liquid, retirement, non-retirement) from raw account snapshots and explicit metadata in `config.json`, hashes the password, and injects everything into the template as a `const DATA = {...}` JSON blob. All chart rendering, projections, and milestones run client-side.

## Data model

### `data/snapshots.json`

Each snapshot has a date, account balances, and home equity. Account inclusion and retirement classification come from `config.json`; unconfigured accounts are intentionally excluded. `home_equity` is already net equity, not gross home value, and `mortgage_balance` is retained for ownership milestones. Optional top-level `income` and `expenses` values (annual dollars) feed projection calculations and FIRE milestones.

```json
{
  "date": "2026-08-01",
  "accounts": {
    "michael_robinhood_retirement": 184585.27,
    "michael_robinhood_taxable": 465434.97
  },
  "home_equity": 642684.22,
  "mortgage_balance": 565396.78,
  "income": 400000,
  "expenses": 108000
}
```

Checking and savings are not tracked by design. `config.json` is the authoritative source for whether an account is liquid and whether it belongs to retirement or non-retirement.

### `config.json`

Defines account metadata and projection settings. See file for full schema. Key fields:
- `accounts.<key>.bucket`: `"retirement"` or `"non_retirement"`
- `accounts.<key>.liquid`: `true`/`false` (home equity is illiquid)
- `projection.*`: editable projection defaults used by the UI; presets are 4% conservative, 7% expected, and 9% optimistic
- `retirement_profile.target_age`: target retirement age used by Coast FIRE
- `retirement_profile.birth_year` and `birth_month`: used to calculate the target month
- `retirement_profile.fire_multiple`: retirement target multiple used by Coast FIRE (default 25)
- `retirement_profile.inflation_rate`: annual inflation assumption used for bridge-fund targets (default 3%)

Password credentials are stored in `data/password.json` and injected into the generated page. They provide casual privacy, not security against source inspection or offline brute force.

## Features

### 1. Net Worth Chart (total + ex-housing)
- Two lines on one chart: total net worth + liquid (excl. home equity)
- Timeframe toggles: YTD, 1Y, 5Y, All

### 2. Projections (1–30 years, default 10)
- **Inputs:** annual expenses, annual income, investment growth %
- **Computation:** deterministic monthly compounding
- **Output:** stacked current-liquid-investments and future-contributions series
- **Model:** after-tax income minus expenses is invested monthly at the given growth rate, starting from current liquid net worth
- Horizon is editable and defaults to 10 years; assumptions persist locally and can be reset.

### 3. Retirement vs Non-Retirement
- Stacked bar chart
- Timeframe toggles: YTD, 1Y, 5Y, All

### 4. Milestones & Achievements

Four categories with progress bars and projected cross-dates:

| Category | Milestones |
|---|---|
| 💰 Liquid Net Worth | $1M, $2M, $3M, $4M, $5M, $7.5M, $10M |
| 🔥 FIRE | Coast FIRE, Lean FIRE (25× expenses), Full FIRE (33×), Fat FIRE (40×) |
| 🌉 Bridge Fund | 1yr, 3yr, 5yr, 10yr, 15yr, 20yr expenses in non-retirement accounts |
| 🏠 Home Equity | 50%, 75%, 100% ownership (mortgage-free) |

- **Horizontal milestone lines** on projection chart for liquid NW + FIRE targets
- **Collapsible achievements panel** (click "🏆 Achievements") with progress bars, estimated cross-dates, and color coding (green = done, amber = close, gray = distant)
- **FIRE and bridge milestones** recalculate live when expense input changes
- **Projection scenarios** provide Conservative, Expected, Optimistic, and Custom modes; detailed inputs are hidden under Advanced settings by default
- **Achievement cards** include collapsed calculation explanations and distinguish completed, current-focus, and future ladder milestones
- **Bridge targets** use inflation-adjusted monthly withdrawals beginning at the target retirement age, discounted by the selected scenario return; the default inflation assumption is 3%

### 5. Password Gate
- SHA-256 client-side gate
- Enabled in the current build for casual privacy only. The source HTML still contains the data and hash.

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
