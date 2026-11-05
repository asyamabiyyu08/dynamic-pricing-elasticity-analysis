"""
build_dashboard.py - embed the CSV into dashboard/template.html and write the web dashboard.

    python src/build_dashboard.py                 # -> dashboard/index.html (standalone page, GitHub Pages ready)
    python src/build_dashboard.py --fragment out.html   # page body only (no <html> wrapper)

The dashboard has no server and no dependencies: all 2,000 records are embedded in the page and every
number is recomputed in the browser when a filter changes (the JS mirrors the logic in sql/01-05).
"""
import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--fragment", type=Path, help="write the page without the <html> wrapper to this path")
args = ap.parse_args()

df = pd.read_csv(ROOT / "data" / "pricing_transactions.csv")
cols = ["transaction_id", "date", "property_or_product_id", "category", "base_price", "discount_percentage",
        "final_price", "units_sold_or_booked", "customer_segment", "event_flag", "competitor_price", "rooms_available"]
rows = [[None if pd.isna(v) else (int(v) if isinstance(v, (int, float)) and not isinstance(v, str) else v)
         for v in rec] for rec in df[cols].itertuples(index=False, name=None)]
payload = json.dumps({"columns": cols, "rows": rows}, separators=(",", ":"))

page = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8").replace("__DATA__", payload)

if args.fragment:
    args.fragment.write_text(page, encoding="utf-8")
    print(f"fragment -> {args.fragment} ({len(page)/1024:.0f} KB)")
else:
    out = ROOT / "dashboard" / "index.html"
    out.write_text('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                   + page + "\n</html>\n", encoding="utf-8")
    print(f"dashboard -> {out} ({out.stat().st_size/1024:.0f} KB)")
