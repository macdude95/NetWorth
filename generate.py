#!/usr/bin/env python3
"""
Net Worth Dashboard Generator
Reads config.json + data/snapshots.json -> writes a single static HTML file
with Chart.js charts, password gate, projections, and timeframe toggles.
Mobile-responsive, self-contained (Chart.js via CDN).

Usage:
  python3 generate.py                      # build with current config/data
  python3 generate.py --set-password PWD   # update password hash in config
"""

import json
import hashlib
import secrets
import os
import sys
from math import exp, sqrt
import random
from datetime import datetime, timedelta

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")
SNAPSHOTS_PATH = os.path.join(PROJECT_DIR, "data", "snapshots.json")
TEMPLATE_PATH = os.path.join(PROJECT_DIR, "templates", "index.html")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "docs")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "index.html")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def derive_net_worth_series(snapshots, config):
    """Compute net worth total, ex-housing, retirement, non-retirement per snapshot."""
    accounts_def = config["accounts"]
    dates = []
    net_worth_total = []
    net_worth_ex_housing = []
    retirement = []
    non_retirement = []

    for snap in snapshots:
        dates.append(snap["date"])
        nw = 0.0
        home_equity = 0.0
        mortgage = 0.0
        ret = 0.0
        non_ret = 0.0
        for key, val in snap["accounts"].items():
            acct = accounts_def[key]
            nw += val
            if key == "home_equity":
                home_equity = val
            if acct["bucket"] == "retirement":
                ret += val
            else:
                non_ret += val
        for key, val in snap.get("liabilities", {}).items():
            if key == "mortgage_balance":
                mortgage = val
            nw -= val
        net_worth_total.append(nw)
        net_worth_ex_housing.append(nw - home_equity + mortgage)
        retirement.append(ret)
        non_retirement.append(non_ret)

    return {
        "dates": dates,
        "net_worth_total": net_worth_total,
        "net_worth_ex_housing": net_worth_ex_housing,
        "retirement": retirement,
        "non_retirement": non_retirement,
    }


def compute_projections(snapshots, config):
    """Forward projection: growth + contributions + Monte Carlo bands."""
    proj_cfg = config.get("projections", {})
    if not proj_cfg.get("enabled"):
        return None

    horizon_months = proj_cfg["horizon_years"] * 12
    contributions = proj_cfg["contributions_usd_per_month"]
    volatility = proj_cfg["volatility_annual_pct"]
    mc_runs = proj_cfg.get("monte_carlo_runs", 500)
    accounts_def = config["accounts"]

    last = snapshots[-1]
    start_values = {}
    for key in accounts_def:
        start_values[key] = last["accounts"].get(key, 0)

    # Deterministic p50 projection (compound growth + contributions)
    p50 = []
    for m in range(horizon_months + 1):
        total = 0.0
        for key, val in start_values.items():
            acct = accounts_def[key]
            r = acct["growth_rate"]
            monthly_growth = val * ((1 + r) ** (m / 12))
            contrib = contributions.get(key, 0) * m
            total += monthly_growth + contrib
        p50.append(round(total, 2))

    # Monte Carlo for p10/p90 bands
    random.seed(42)
    paths = []
    for _ in range(mc_runs):
        path = []
        current = dict(start_values)
        for m in range(horizon_months + 1):
            total = 0.0
            for key, val in current.items():
                acct = accounts_def[key]
                bucket = acct["bucket"]
                liquid = acct["liquid"]
                if not liquid:
                    vol_key = "home"
                else:
                    vol_key = bucket  # "retirement" or "non_retirement"
                annual_vol = volatility.get(vol_key, 15) / 100.0
                monthly_vol = annual_vol / sqrt(12)
                r = acct["growth_rate"]
                shock = random.gauss(0, monthly_vol)
                new_val = val * exp((r - 0.5 * monthly_vol ** 2) / 12 + shock)
                total += new_val
                current[key] = new_val
            for key, contrib in contributions.items():
                if m > 0:
                    total += contrib
                    current[key] += contrib
            path.append(round(total, 2))
        paths.append(path)

    p10_band = []
    p90_band = []
    for m in range(horizon_months + 1):
        vals = sorted(p[m] for p in paths)
        p10_band.append(vals[int(mc_runs * 0.10)])
        p90_band.append(vals[int(mc_runs * 0.90)])

    last_date = last["date"]
    dt = datetime.strptime(last_date, "%Y-%m-%d")
    proj_dates = []
    for m in range(horizon_months + 1):
        d = dt + timedelta(days=m * 30)
        proj_dates.append(d.strftime("%Y-%m-%d"))

    return {
        "dates": proj_dates,
        "p50": p50,
        "p10": p10_band,
        "p90": p90_band,
        "horizon_label": f"{proj_cfg['horizon_years']}yr projection",
    }


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt


def cmd_set_password(password):
    """Set the password in config.json."""
    config = load_json(CONFIG_PATH)
    h, s = hash_password(password)
    config["password"]["hash"] = h
    config["password"]["salt"] = s
    write_json(CONFIG_PATH, config)
    print(f"✅ Password set. Salt: {s[:8]}..., Hash: {h[:16]}...")


def main():
    if "--set-password" in sys.argv:
        idx = sys.argv.index("--set-password")
        if idx + 1 < len(sys.argv):
            cmd_set_password(sys.argv[idx + 1])
        else:
            print("Usage: python3 generate.py --set-password YOUR_PASSWORD")
        return

    config = load_json(CONFIG_PATH)
    data = load_json(SNAPSHOTS_PATH)
    snapshots = data["snapshots"]

    series = derive_net_worth_series(snapshots, config)
    projections = compute_projections(snapshots, config)

    # Password setup
    pw_cfg = config.get("password", {})
    stored_hash = pw_cfg.get("hash", "PLACEHOLDER_HASH")
    stored_salt = pw_cfg.get("salt", "PLACEHOLDER_SALT")

    if stored_hash == "PLACEHOLDER_HASH":
        demo_pw = "demo123"
        stored_hash, stored_salt = hash_password(demo_pw)
        print(f"Using demo password: '{demo_pw}' — set yours with: python3 generate.py --set-password YOUR_PASSWORD")

    chart_data = {
        "series": series,
        "projections": projections,
        "accounts": config["accounts"],
        "liabilities": config.get("liabilities", {}),
        "password": {
            "hash": stored_hash,
            "salt": stored_salt,
        },
    }

    with open(TEMPLATE_PATH) as f:
        html = f.read()
    html = html.replace("__CHART_DATA_JSON__", json.dumps(chart_data))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    print(f"Dashboard written to {OUTPUT_PATH}")
    print(f"  Open with:    open {OUTPUT_PATH}")
    print(f"  Or serve via: cd {OUTPUT_DIR} && python3 -m http.server 8080")


if __name__ == "__main__":
    main()
