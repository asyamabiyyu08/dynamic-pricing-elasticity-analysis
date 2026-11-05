# Executive Summary: Dynamic Pricing & Promotional Elasticity

**Audience:** Commercial Director, Head of Revenue Management, Marketing/Promo Lead
**Scope:** 2,000 booking records, 32 properties, 4 categories, May-Oct 2026 (synthetic data; see README)

## Headline

Discounting is currently applied almost uniformly: **71% of bookings carry a discount, averaging 23 percentage points**. But only one customer segment responds strongly enough to make deep discounts pay. In **15 of 19** segment-event combinations we could measure, promotions of 30% or more earned *less* revenue than selling at full price. Relative to a full-price counterfactual, that is roughly **IDR 2.8 bn of net revenue given away (about 5% of the IDR 52.8 bn analysed)**.

| Segment | Price elasticity | Revenue-maximising discount (non-peak / peak) |
|---|---|---|
| Budget Seeker | -1.66 (elastic) | 11-20% / 11-20% |
| Family Leisure | -1.22 (elastic) | 21-30% / 1-10% |
| Business Traveler | -0.61 (inelastic) | 0% / 0% |
| Premium Luxury | -0.30 (inelastic) | 0% / 0% |

---

## 1. Actionable Pricing Strategy: price by segment, not by calendar

- **Cap Budget Seeker discounts at 20%.** The 11-20% band lifts revenue yield +16% (non-peak) and +14% (peak) over full price. Beyond 30%, occupancy is already ~100%, so extra depth only erodes price: yield falls to -6% (non-peak) and -16% (peak) vs. full price.
- **Family Leisure: discount only off-peak.** 21-30% is optimal off-peak (+10%); on weekends and holidays the best move is at most 1-10% (+2%), and 21%+ loses 12-27%.
- **Stop price-led promotions for Business and Premium guests.** Full price is the optimum in every context; a 31%+ discount cuts Premium yield by ~40%. Replace discounts with value-adds (breakfast, late checkout, room upgrade) that cost little and do not reset the price anchor.
- **Price weekends up for families, not down for business travellers.** Family weekend RevPAR is +29% vs. weekday at 89% occupancy: there is room to raise weekend rates. Business weekend RevPAR is -31% (47% occupancy) and discounting does not fix it because the segment is inelastic; shift that inventory to leisure channels instead.

## 2. Target Promo Optimization: spend the discount budget where it returns revenue

- **Inventory-aware promo switch-off.** 48% of deep-promo bookings sold out completely; for Budget Seekers on weekends and payday sales it is 100%. Close deep promotions automatically when forecast occupancy exceeds ~85-90%.
- **Re-allocate promo budget by property.** The most efficient properties (PRP-003 and PRP-008, both Budget Hotels) return +0.6 to +0.7% revenue per point of discount (+14-16% uplift in total). All 8 Luxury Resorts and 7 of 8 Upscale Hotels show *negative* uplift from promotions: remove them from standard promo calendars.
- **Retire "blanket" sale-day discounts.** Payday and double-date campaigns cannibalize revenue for Premium (-42%), Budget (-24% on payday, at 100% sold-out), and Business guests. Only Family Leisure showed a positive payday result (+7%).

## 3. Risk Mitigation

| Risk | Why it matters | Mitigation |
|---|---|---|
| Revenue != profit | Analysis optimises revenue yield; discounts at higher volume also raise variable cost (cleaning, OTA commission) | Re-run on contribution margin / GOP per room-night before rollout |
| Brand dilution (Premium) | Deep discounts reduce volume *and* signal lower quality (modelled -8 to -18% volume penalty at 30%+) | Hard cap of 10% for Premium; use members-only perks instead of price cuts |
| Causality | Promo depth was not randomised; sale days attracted deeper discounts | Validate with an A/B or geo hold-out test on 4-6 properties before chain-wide change |
| Competitor response | Price cuts can trigger matching and a price war | Monitor `competitor_price` daily; guardrail alerts when price index falls >10% below competitor |
| Demand censoring | Occupancy cannot exceed 100%, so true demand at sold-out dates is under-measured | Track "sold-out" rate as a KPI; test higher base prices on sold-out dates |
| Small cells | Holiday and double-date cells have 5-15 records | Treat as directional; collect more event-day data |

**Suggested rollout:** (1) 4-week pilot at 6 properties with the segment caps above vs. 6 control properties; (2) read-out on RevPAR, GOP/room-night, and sold-out rate; (3) scale to chain if RevPAR uplift is positive at neutral-or-better margin.
