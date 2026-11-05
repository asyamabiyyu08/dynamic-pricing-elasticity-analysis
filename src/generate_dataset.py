"""
generate_dataset.py
===================
Synthetic transaction data for the "Dynamic Pricing & Promotional Elasticity" project.

Business context
----------------
An Indonesian online travel marketplace (OTA) sells room-nights for 32 properties across
4 categories. One row = one *property x customer segment x stay date* booking batch
(room-nights booked for that slot at one price point).

The data is synthetic, but it is generated from an explicit demand model so that
realistic, *discoverable* patterns exist (see PATTERNS below). Because the generating
process is documented, every insight in the README can be traced back to a known
ground truth - a good habit for validating analytical methods.

PATTERNS BAKED INTO THE DATA
----------------------------
1. Segment elasticity differs sharply
      Budget Seeker  : highly elastic     (|e| ~ 2.3)
      Family Leisure : moderately elastic (|e| ~ 1.4)
      Business Trav. : inelastic          (|e| ~ 0.6)
      Premium Luxury : very inelastic     (|e| ~ 0.35) + brand-dilution penalty at >=30% off
2. Category modifies elasticity (Budget hotels more price-sensitive than Luxury resorts).
3. Event days lift demand (national holidays, weekends, sale days) -> inventory
   (`rooms_available`) becomes the binding constraint, so discounts there are wasted
   (promo cannibalization).
4. Business travelers skew to weekdays; Family/Premium skew to weekends & holidays.
5. Promo depth is NOT random: sale days (payday / double-date) attract deeper discounts,
   Budget Seekers get deeper discounts, Premium gets slightly shallower ones (mild
   confounding, like in real life).
6. ~2% of competitor prices are missing (data-quality realism).

Usage
-----
    python src/generate_dataset.py                 # 2,000 rows, seed 42
    python src/generate_dataset.py --rows 1500 --seed 7
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------------------------------------------
START_DATE, END_DATE = "2026-05-01", "2026-10-31"   # last 6 months (relative to Nov 2026)

# Simplified Indonesian national-holiday calendar for the window (illustrative; verify the
# official SKB 3 Menteri calendar before using this for any real-world forecasting).
NATIONAL_HOLIDAYS = pd.to_datetime([
    "2026-05-14",  # Ascension of Jesus Christ
    "2026-05-27",  # Eid al-Adha
    "2026-05-28",  # Joint leave
    "2026-05-31",  # Waisak
    "2026-06-01",  # Pancasila Day
    "2026-06-16",  # Islamic New Year
    "2026-08-17",  # Independence Day
    "2026-08-25",  # Maulid Nabi
])
DOUBLE_DATES = {(5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10)}   # e.g. "7.7 sale"
PAYDAY_DAYS = {25, 26, 27, 28}

EVENTS = ["Regular Weekday", "Weekend", "Libur Nasional", "Payday Sale", "Double Date Sale"]
EVENT_DATE_WEIGHT = {"Regular Weekday": 1.0, "Weekend": 1.0, "Libur Nasional": 1.6,
                     "Payday Sale": 1.3, "Double Date Sale": 1.6}
EVENT_PRICE_FACTOR = {"Regular Weekday": 1.00, "Weekend": 1.08, "Libur Nasional": 1.15,
                      "Payday Sale": 1.00, "Double Date Sale": 0.98}   # dynamic base price
EVENT_COMP_BUMP = {"Regular Weekday": 0.00, "Weekend": 0.03, "Libur Nasional": 0.06,
                   "Payday Sale": 0.00, "Double Date Sale": -0.01}

CATEGORIES = {
    #                 id_prefix, n_props, price_range (IDR),       base room-nights, elasticity factor
    "Budget Hotel":   dict(n=8, price=(300_000, 450_000),   demand=30, e_factor=1.15,
                           seg_mix=[0.55, 0.25, 0.15, 0.05]),
    "Midscale Hotel": dict(n=8, price=(600_000, 900_000),   demand=24, e_factor=1.00,
                           seg_mix=[0.25, 0.35, 0.30, 0.10]),
    "Upscale Hotel":  dict(n=8, price=(1_100_000, 1_800_000), demand=18, e_factor=0.85,
                           seg_mix=[0.10, 0.30, 0.35, 0.25]),
    "Luxury Resort":  dict(n=8, price=(2_800_000, 5_500_000), demand=14, e_factor=0.75,
                           seg_mix=[0.05, 0.25, 0.10, 0.60]),
}

SEGMENTS = ["Budget Seeker", "Family Leisure", "Business Traveler", "Premium Luxury"]
SEG_ELASTICITY = {"Budget Seeker": 2.30, "Family Leisure": 1.40,
                  "Business Traveler": 0.60, "Premium Luxury": 0.35}   # |e|
SEG_VOLUME_SCALE = {"Budget Seeker": 1.00, "Family Leisure": 0.95,
                    "Business Traveler": 0.85, "Premium Luxury": 0.80}

# Demand multiplier by (segment, event). Business -> weekdays; Family/Premium -> weekends/holidays.
EVENT_DEMAND = {
    "Budget Seeker":     {"Regular Weekday": 1.00, "Weekend": 1.20, "Libur Nasional": 1.35,
                          "Payday Sale": 1.50, "Double Date Sale": 1.60},
    "Family Leisure":    {"Regular Weekday": 1.00, "Weekend": 1.45, "Libur Nasional": 1.70,
                          "Payday Sale": 1.15, "Double Date Sale": 1.20},
    "Business Traveler": {"Regular Weekday": 1.00, "Weekend": 0.65, "Libur Nasional": 0.60,
                          "Payday Sale": 1.00, "Double Date Sale": 0.95},
    "Premium Luxury":    {"Regular Weekday": 1.00, "Weekend": 1.25, "Libur Nasional": 1.40,
                          "Payday Sale": 1.05, "Double Date Sale": 1.00},
}

DISCOUNT_LEVELS = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40, 50])
DISCOUNT_BASE_P = np.array([0.30, 0.06, 0.10, 0.10, 0.10, 0.08, 0.10, 0.06, 0.07, 0.03])

CAPACITY_HEADROOM = 1.75   # rooms_available = 1.75 x baseline demand  (=> ~57% baseline occupancy)


# --------------------------------------------------------------------------------------
# 2. HELPERS
# --------------------------------------------------------------------------------------
def classify_event(ts: pd.Timestamp) -> str:
    """Assign ONE event flag per date. Priority: holiday > double-date > payday > weekend."""
    if ts in NATIONAL_HOLIDAYS:
        return "Libur Nasional"
    if (ts.month, ts.day) in DOUBLE_DATES:
        return "Double Date Sale"
    if ts.day in PAYDAY_DAYS:
        return "Payday Sale"
    if ts.dayofweek >= 5:
        return "Weekend"
    return "Regular Weekday"


def round_to(x: float, step: int) -> int:
    return int(round(x / step) * step)


def build_properties(rng: np.random.Generator) -> pd.DataFrame:
    rows, k = [], 1
    for cat, cfg in CATEGORIES.items():
        for _ in range(cfg["n"]):
            rows.append({
                "property_or_product_id": f"PRP-{k:03d}",
                "category": cat,
                "list_price": round_to(rng.uniform(*cfg["price"]), 5_000),
                "prop_factor": float(np.exp(rng.normal(0, 0.12))),   # property size / popularity
            })
            k += 1
    return pd.DataFrame(rows)


def discount_probs(event: str, segment: str) -> np.ndarray:
    """Promo policy is not random: sale days & budget seekers get deeper discounts."""
    p = DISCOUNT_BASE_P.copy()
    deep = DISCOUNT_LEVELS >= 20
    if event in ("Payday Sale", "Double Date Sale"):
        p[deep] *= 1.6
    if segment == "Budget Seeker":
        p[deep] *= 1.25
    if segment == "Premium Luxury":
        p[deep] *= 0.90
    return p / p.sum()


# --------------------------------------------------------------------------------------
# 3. MAIN GENERATOR
# --------------------------------------------------------------------------------------
def generate(n_rows: int = 2000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    props = build_properties(rng)

    # Calendar with sampling weights (event days are slightly over-represented)
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal["event_flag"] = cal["date"].map(classify_event)
    cal["w"] = cal["event_flag"].map(EVENT_DATE_WEIGHT)
    cal["w"] /= cal["w"].sum()

    # Property-segment baseline demand (room-nights/day) and allocated inventory
    records = []
    for i in range(n_rows):
        prop = props.iloc[rng.integers(len(props))]
        cfg = CATEGORIES[prop["category"]]
        seg = rng.choice(SEGMENTS, p=cfg["seg_mix"])
        day = cal.iloc[rng.choice(len(cal), p=cal["w"].values)]
        event = day["event_flag"]

        # ---- pricing -------------------------------------------------------------------
        base_price = round_to(prop["list_price"] * EVENT_PRICE_FACTOR[event], 5_000)
        disc = int(rng.choice(DISCOUNT_LEVELS, p=discount_probs(event, seg)))
        final_price = round_to(base_price * (1 - disc / 100), 1_000)
        comp_price = round_to(base_price * (1 + EVENT_COMP_BUMP[event] + rng.normal(0, 0.06)), 5_000)

        # ---- demand model ----------------------------------------------------------------
        lam_base = cfg["demand"] * prop["prop_factor"] * SEG_VOLUME_SCALE[seg]
        rooms_available = int(np.ceil(lam_base * CAPACITY_HEADROOM))

        e_eff = SEG_ELASTICITY[seg] * cfg["e_factor"]
        price_effect = (1 - disc / 100) ** (-e_eff)

        brand_dilution = 1.0                       # premium guests read deep discounts as "lower quality"
        if seg == "Premium Luxury":
            brand_dilution = 0.82 if disc >= 40 else 0.92 if disc >= 30 else 1.0

        comp_effect = (comp_price / base_price) ** 0.6   # competitor more expensive -> we gain
        noise = np.exp(rng.normal(0, 0.10))

        lam = lam_base * EVENT_DEMAND[seg][event] * price_effect * brand_dilution * comp_effect * noise
        units = int(np.clip(rng.poisson(lam), 1, rooms_available))   # inventory is a hard cap

        records.append({
            "date": day["date"].date().isoformat(),
            "property_or_product_id": prop["property_or_product_id"],
            "category": prop["category"],
            "base_price": base_price,
            "discount_percentage": disc,
            "final_price": final_price,
            "units_sold_or_booked": units,
            "customer_segment": seg,
            "event_flag": event,
            "competitor_price": comp_price,
            "rooms_available": rooms_available,
        })

    df = pd.DataFrame(records).sort_values(["date", "property_or_product_id"]).reset_index(drop=True)
    df.insert(0, "transaction_id", [f"TRX-{i:05d}" for i in range(1, len(df) + 1)])

    # Data-quality realism: ~1.5% target missing competitor prices (scrape failures)
    miss = rng.random(len(df)) < 0.015
    df["competitor_price"] = df["competitor_price"].astype("Int64")
    df.loc[miss, "competitor_price"] = pd.NA

    cols = ["transaction_id", "date", "property_or_product_id", "category", "base_price",
            "discount_percentage", "final_price", "units_sold_or_booked", "customer_segment",
            "event_flag", "competitor_price", "rooms_available"]
    return df[cols]


def sanity_report(df: pd.DataFrame) -> None:
    """Quick checks that the baked-in patterns are really present."""
    d = df.copy()
    d["revenue"] = d["final_price"] * d["units_sold_or_booked"]
    d["occupancy"] = d["units_sold_or_booked"] / d["rooms_available"]
    d["is_deep"] = d["discount_percentage"] >= 30

    print(f"\nRows: {len(d):,} | dates: {d['date'].min()} -> {d['date'].max()} | "
          f"properties: {d['property_or_product_id'].nunique()}")
    print("\nAvg occupancy by event_flag:")
    print(d.groupby("event_flag")["occupancy"].mean().round(3).sort_values(ascending=False).to_string())
    print("\nAvg revenue/record: no discount vs >=30% off, by segment (IDR millions):")
    t = (d.assign(g=np.where(d["discount_percentage"] == 0, "no_disc",
                    np.where(d["is_deep"], "deep_30plus", "other")))
           .pivot_table(index="customer_segment", columns="g", values="revenue", aggfunc="mean") / 1e6)
    t["deep_vs_no_disc_%"] = (t["deep_30plus"] / t["no_disc"] - 1) * 100
    print(t[["no_disc", "deep_30plus", "deep_vs_no_disc_%"]].round(1).to_string())
    print(f"\nMissing competitor_price: {d['competitor_price'].isna().mean():.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parents[1] / "data" / "pricing_transactions.csv")
    args = ap.parse_args()

    data = generate(args.rows, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.out, index=False)
    print(f"Saved -> {args.out}")
    sanity_report(data)
