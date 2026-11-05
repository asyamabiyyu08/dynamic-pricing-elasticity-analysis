"""
make_charts.py - build the README charts from the SQL outputs (run run_analysis.py first).
Palette: validated categorical order (blue, orange, aqua, yellow); diverging blue <-> orange
around a neutral midpoint. Direct labels are used so identity never depends on color alone.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
OUT, IMG = ROOT / "outputs", ROOT / "images"
IMG.mkdir(exist_ok=True)

INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SEG_COLOR = {"Budget Seeker": "#2a78d6", "Family Leisure": "#eb6834",
             "Business Traveler": "#1baf7a", "Premium Luxury": "#eda100"}
SEG_ORDER = list(SEG_COLOR)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True,
})


def title(fig, head, sub):
    fig.text(0.01, 0.975, head, fontsize=14, fontweight="bold", va="top", ha="left")
    fig.text(0.01, 0.915, sub, fontsize=10, color=INK2, va="top", ha="left")


# ---- 1. Elasticity by segment (headline) --------------------------------------------------
q1 = pd.read_csv(OUT / "01_price_elasticity.csv")
el = (q1[q1.dimension == "segment"].drop_duplicates("grp").set_index("grp")["elasticity_core"]
      .reindex(SEG_ORDER))
fig, ax = plt.subplots(figsize=(8, 4.2))
y = np.arange(len(el))[::-1]
ax.barh(y, -el.values, color=[SEG_COLOR[s] for s in el.index], height=0.55)
for yi, (seg, v) in zip(y, el.items()):
    ax.text(-v + 0.03, yi, f"{v:.2f}", va="center", fontsize=10, color=INK)
ax.set_yticks(y, el.index)
ax.axvline(1, color=INK2, lw=1.2, ls="--")
ax.text(1.02, y.max() + 0.48, "|e| = 1: revenue-neutral", fontsize=9, color=INK2, va="bottom")
ax.set_xlabel("Price elasticity of demand, absolute value (discounts up to 20%)")
ax.set_xlim(0, 2.1); ax.grid(axis="y", visible=False)
title(fig, "Budget Seekers respond to discounts; Premium guests barely notice",
      "Price elasticity by customer segment. Right of the dashed line, a discount pays for itself")
fig.tight_layout(rect=(0, 0, 1, 0.86)); fig.savefig(IMG / "01_elasticity_by_segment.png", dpi=200); plt.close(fig)

# ---- 2. Revenue yield vs full price, by discount band (optimal discount matrix) ---------------
q5 = pd.read_csv(OUT / "05_optimal_discount_matrix.csv")
bands = ["0%", "1-10%", "11-20%", "21-30%", "31%+"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for ax, ctx in zip(axes, ["Non-peak", "Peak (holiday/weekend)"]):
    for seg in SEG_ORDER:
        d = q5[(q5.customer_segment == seg) & (q5.demand_context == ctx)].set_index("discount_band").reindex(bands)
        ax.plot(range(5), d.vs_full_price_pct, color=SEG_COLOR[seg], lw=2, marker="o", ms=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5)
        best = d.vs_full_price_pct.idxmax(); xb = bands.index(best)
        ax.scatter([xb], [d.vs_full_price_pct[best]], s=150, facecolors="none",
                   edgecolors=SEG_COLOR[seg], linewidths=1.8, zorder=5)
        ax.text(4.12, d.vs_full_price_pct.iloc[-1], seg, color=INK, fontsize=9, va="center")
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(range(5), bands); ax.set_xlim(-0.2, 5.6)
    ax.set_title(ctx, fontsize=11, loc="left", color=INK2)
    ax.set_xlabel("Discount depth")
axes[0].set_ylabel("Revenue yield vs. full price (%)")
title(fig, "The best discount is shallow for some segments and zero for others",
      "Revenue yield change vs. 0% discount, by segment. Circled point = revenue-maximising band")
fig.tight_layout(rect=(0, 0, 1, 0.86)); fig.savefig(IMG / "02_optimal_discount_by_segment.png", dpi=200); plt.close(fig)

# ---- 3. Cannibalization heatmap -------------------------------------------------------------
q2 = pd.read_csv(OUT / "02_promo_cannibalization.csv")
events = ["Regular Weekday", "Weekend", "Payday Sale", "Double Date Sale", "Libur Nasional"]
piv = q2.pivot(index="customer_segment", columns="event_flag", values="revenue_delta_pct").reindex(
    index=SEG_ORDER, columns=events)
conf = q2.pivot(index="customer_segment", columns="event_flag", values="sample_confidence").reindex(
    index=SEG_ORDER, columns=events)
cmap = LinearSegmentedColormap.from_list("div", ["#eb6834", "#f0efec", "#2a78d6"])
fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.imshow(piv.values, cmap=cmap, vmin=-45, vmax=45, aspect="auto")
ax.grid(False)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j]
        if np.isnan(v):
            ax.text(j, i, "n/a", ha="center", va="center", color=INK2, fontsize=9)
        else:
            star = "*" if str(conf.values[i, j]).startswith("Low") else ""
            ax.text(j, i, f"{v:+.0f}%{star}", ha="center", va="center", fontsize=11,
                    color=INK, fontweight="bold")
ax.set_xticks(range(len(events)), events); ax.set_yticks(range(len(SEG_ORDER)), SEG_ORDER)
ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
title(fig, "Deep discounts (30%+) lose money in 15 of 19 segment-event cells",
      "Revenue yield change of 30%+ promos vs. full price. Orange = cannibalization, blue = incremental. * = small sample")
fig.tight_layout(rect=(0, 0, 1, 0.86)); fig.savefig(IMG / "03_cannibalization_heatmap.png", dpi=200); plt.close(fig)

# ---- 4. Weekend vs weekday RevPAR ---------------------------------------------------------------
q3 = pd.read_csv(OUT / "03_weekend_vs_weekday.csv")
wk = q3[q3.day_type == "Weekend"].set_index("customer_segment")["revpar_delta_pct"].reindex(SEG_ORDER)
fig, ax = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(wk))
ax.bar(x, wk.values, color=[SEG_COLOR[s] for s in wk.index], width=0.55)
for xi, v in zip(x, wk.values):
    ax.text(xi, v + (1.2 if v >= 0 else -1.2), f"{v:+.1f}%", ha="center",
            va="bottom" if v >= 0 else "top", fontsize=10)
ax.axhline(0, color=INK2, lw=1)
ax.set_xticks(x, [s.replace(" ", "\n") for s in wk.index]); ax.grid(axis="x", visible=False)
ax.set_ylabel("Weekend RevPAR vs. weekday (%)"); ax.set_ylim(-38, 38)
title(fig, "Weekends are a Family Leisure story, and a Business Traveler problem",
      "RevPAR (revenue per available room-night), weekend vs. weekday, by customer segment")
fig.tight_layout(rect=(0, 0, 1, 0.86)); fig.savefig(IMG / "04_weekend_vs_weekday.png", dpi=200); plt.close(fig)
print("charts saved to", IMG)
