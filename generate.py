#!/usr/bin/env python3
"""
Net Worth Dashboard Generator
Reads data/snapshots.json -> writes a single static HTML file
with Chart.js charts, password gate, and timeframe toggles.

Usage:
  python3 generate.py                      # build with current data
  python3 generate.py --set-password PWD  # update data/password.json
"""

import json
import hashlib
import secrets
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(PROJECT_DIR, "templates", "index.html")
SNAPSHOTS_PATH = os.path.join(PROJECT_DIR, "data", "snapshots.json")
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")
PASSWORD_PATH = os.path.join(PROJECT_DIR, "data", "password.json")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "docs")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "index.html")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def derive_series(snapshots, config):
    """Compute explicit liquid, retirement, non-retirement, and total series."""
    dates = []
    net_worth_total = []
    net_worth_ex_housing = []
    retirement = []
    non_retirement = []
    account_config = config["accounts"]

    for snap in snapshots:
        dates.append(snap["date"])
        liquid = sum(
            snap.get("accounts", {}).get(key, 0)
            for key, meta in account_config.items()
            if meta.get("liquid", False)
        )
        ret = sum(
            snap.get("accounts", {}).get(key, 0)
            for key, meta in account_config.items()
            if meta.get("liquid", False) and meta.get("bucket") == "retirement"
        )
        non_ret = sum(
            snap.get("accounts", {}).get(key, 0)
            for key, meta in account_config.items()
            if meta.get("liquid", False) and meta.get("bucket") == "non_retirement"
        )

        nw = liquid + snap.get("home_equity", 0)
        net_worth_total.append(nw)
        net_worth_ex_housing.append(liquid)
        retirement.append(ret)
        non_retirement.append(non_ret)

    return {
        "dates": dates,
        "net_worth_total": net_worth_total,
        "net_worth_ex_housing": net_worth_ex_housing,
        "retirement": retirement,
        "non_retirement": non_retirement,
    }


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt


def cmd_set_password(password):
    h, s = hash_password(password)
    write_json(PASSWORD_PATH, {"hash": h, "salt": s})
    print(f"Password set. Salt: {s[:8]}..., Hash: {h[:16]}...")


def main():
    if "--set-password" in sys.argv:
        idx = sys.argv.index("--set-password")
        if idx + 1 < len(sys.argv):
            cmd_set_password(sys.argv[idx + 1])
        else:
            print("Usage: python3 generate.py --set-password YOUR_PASSWORD")
        return

    data = load_json(SNAPSHOTS_PATH)
    config = load_json(CONFIG_PATH)
    snapshots = data["snapshots"]
    series = derive_series(snapshots, config)

    # Password setup
    pw_data = {"hash": "PLACEHOLDER_HASH", "salt": "PLACEHOLDER_SALT"}
    if os.path.exists(PASSWORD_PATH):
        pw_data = load_json(PASSWORD_PATH)
    
    stored_hash = pw_data.get("hash", "PLACEHOLDER_HASH")
    stored_salt = pw_data.get("salt", "PLACEHOLDER_SALT")

    if stored_hash == "PLACEHOLDER_HASH":
        demo_pw = "demo123"
        stored_hash, stored_salt = hash_password(demo_pw)
        print(f"Using demo password: '{demo_pw}' — set yours with: python3 generate.py --set-password YOUR_PASSWORD")

    # Build current snapshot summary
    last = snapshots[-1]
    chart_data = {
        "series": series,
        "current": {
            "home_equity": last.get("home_equity", 0),
            "mortgage_balance": last.get("mortgage_balance"),
            "income": last.get("income"),
            "expenses": last.get("expenses"),
        },
        "password": {"hash": stored_hash, "salt": stored_salt},
        "password_enabled": True,
        "tooltip_mode": "dismiss-button",
        "projection_defaults": config.get("projection", {}),
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
