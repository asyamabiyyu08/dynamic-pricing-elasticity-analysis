-- =====================================================================================
-- Q1 | PRICE ELASTICITY OF DEMAND  (by category AND by customer segment)
-- -------------------------------------------------------------------------------------
-- Business question
--   How much does booking volume move when price moves by 1%?
--
-- Method (two complementary estimators)
--   (a) ARC ELASTICITY between consecutive discount bands  = %chg in volume / %chg in price
--       -> uses LAG() window functions; reads like the textbook definition.
--   (b) LOG-LOG "WITHIN" ELASTICITY (fixed-effects slope) = REGR_SLOPE(ln occupancy, ln price_index)
--       after de-meaning inside every category x segment x event cell, so that
--       seasonality / event demand and segment mix do not leak into the price effect.
--       Reported twice:
--         elasticity_core     -> discounts <= 20% only (before inventory starts to saturate). USED FOR THE VERDICT.
--         elasticity_all_rows -> all discounts; visibly attenuated because occupancy is capped at 100%
--                                (a sold-out room cannot show extra demand = censored demand).
--
-- Normalisations (important for a multi-property dataset)
--   price_index = final_price / base_price          (1.00 = rack rate, 0.70 = 30% off)
--   occupancy   = units_sold_or_booked / rooms_available   (removes property size)
--
-- Reading the output
--   elasticity_core <= -1 -> ELASTIC   : a discount grows volume faster than it shrinks price
--   -1 < elasticity_core < 0 -> INELASTIC: a discount destroys revenue
--   Caveat: elasticity is observational (promo depth is not randomised) and demand is censored at
--   100% occupancy, so treat values as directional; an A/B price test is the gold-standard follow-up.
-- =====================================================================================
WITH base AS (
    SELECT
        category,
        customer_segment,
        event_flag,
        discount_percentage,
        CASE WHEN discount_percentage = 0  THEN 0
             WHEN discount_percentage <= 10 THEN 1
             WHEN discount_percentage <= 20 THEN 2
             WHEN discount_percentage <= 30 THEN 3
             ELSE 4 END                                       AS band_order,
        CASE WHEN discount_percentage = 0  THEN '0% (full price)'
             WHEN discount_percentage <= 10 THEN '1-10%'
             WHEN discount_percentage <= 20 THEN '11-20%'
             WHEN discount_percentage <= 30 THEN '21-30%'
             ELSE '31%+' END                                  AS discount_band,
        final_price::numeric / base_price                     AS price_index,
        units_sold_or_booked::numeric / rooms_available       AS occupancy
    FROM pricing_transactions
),
demeaned AS (                                   -- fixed-effects transformation (window function)
    SELECT *,
           LN(occupancy)   - AVG(LN(occupancy))   OVER w AS dm_ln_occ,
           LN(price_index) - AVG(LN(price_index)) OVER w AS dm_ln_price
    FROM base
    WINDOW w AS (PARTITION BY category, customer_segment, event_flag)
),
long_fmt AS (                                   -- one row per transaction per reporting dimension
    SELECT v.dimension, v.grp, d.*
    FROM demeaned d
    CROSS JOIN LATERAL (VALUES ('category', d.category),
                               ('segment',  d.customer_segment)) AS v(dimension, grp)
),
fe AS (
    SELECT dimension, grp,
           COUNT(*)                                   AS n_obs,
           REGR_SLOPE(dm_ln_occ, dm_ln_price)
               FILTER (WHERE discount_percentage <= 20)  AS elasticity_core,
           REGR_SLOPE(dm_ln_occ, dm_ln_price)            AS elasticity_all_rows
    FROM long_fmt
    GROUP BY dimension, grp
),
bands AS (
    SELECT dimension, grp, band_order, discount_band,
           COUNT(*)            AS n_records,
           AVG(price_index)    AS avg_price_index,
           AVG(occupancy)      AS avg_occupancy
    FROM long_fmt
    GROUP BY dimension, grp, band_order, discount_band
),
arc AS (
    SELECT b.*,
           LAG(avg_price_index) OVER w AS prev_price,
           LAG(avg_occupancy)   OVER w AS prev_occ,
           FIRST_VALUE(avg_price_index) OVER w AS full_price_idx,
           FIRST_VALUE(avg_occupancy)   OVER w AS full_price_occ
    FROM bands b
    WINDOW w AS (PARTITION BY dimension, grp ORDER BY band_order)
)
SELECT
    a.dimension,
    a.grp,
    a.discount_band,
    a.n_records,
    ROUND(a.avg_price_index, 3)                                           AS avg_price_index,
    ROUND(100 * a.avg_occupancy, 1)                                       AS avg_occupancy_pct,
    ROUND(100 * (a.avg_price_index / a.prev_price - 1), 1)                AS pct_chg_price_vs_prev_band,
    ROUND(100 * (a.avg_occupancy   / a.prev_occ   - 1), 1)                AS pct_chg_volume_vs_prev_band,
    ROUND((a.avg_occupancy / a.prev_occ - 1)
        / NULLIF(a.avg_price_index / a.prev_price - 1, 0), 2)             AS arc_elasticity_step,
    ROUND((a.avg_occupancy / a.full_price_occ - 1)
        / NULLIF(a.avg_price_index / a.full_price_idx - 1, 0), 2)         AS arc_elasticity_vs_full_price,
    ROUND(f.elasticity_core::numeric, 2)                                  AS elasticity_core,
    ROUND(f.elasticity_all_rows::numeric, 2)                              AS elasticity_all_rows,
    CASE WHEN f.elasticity_core <= -1 THEN 'ELASTIC'
         ELSE 'INELASTIC' END                                             AS demand_type
FROM arc a
JOIN fe  f USING (dimension, grp)
ORDER BY a.dimension, f.elasticity_core, a.grp, a.band_order;
