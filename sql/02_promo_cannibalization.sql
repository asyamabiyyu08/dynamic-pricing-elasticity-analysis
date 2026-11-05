-- =====================================================================================
-- Q2 | PROMO CANNIBALIZATION  -  when does a deep discount LOSE money vs. full price?
-- -------------------------------------------------------------------------------------
-- Definition
--   "Deep promo"   = discount_percentage >= 30
--   "Normal price" = discount_percentage  = 0
--   Revenue Yield  = (final_price x units) / (base_price x rooms_available)
--                    -> share of the *maximum potential revenue at rack rate* actually captured.
--                    Comparable across properties of very different price levels.
--   CANNIBALIZATION = avg yield of deep promos < avg yield at normal price in the same
--                     segment x event cell  (we gave away margin without buying enough volume)
--
-- Diagnostics
--   pct_deep_sold_out : share of deep-promo records that hit 100% of inventory
--                       -> discount was "wasted" because the room would have sold anyway
--   net_revenue_impact_idr : sum over deep-promo records of (actual - counterfactual) revenue,
--                       where counterfactual = potential revenue x cell's normal-price yield.
--                       Negative = money left on the table.
-- Cells with fewer than 5 records on either side are dropped; cells < 15 are tagged in sample_confidence.
-- Window functions: AVG(...) FILTER ... OVER (PARTITION BY ...) for the counterfactual baseline,
--                   RANK() OVER (...) for severity.
-- =====================================================================================
WITH scored AS (
    SELECT
        customer_segment,
        event_flag,
        CASE WHEN discount_percentage = 0  THEN 'normal'
             WHEN discount_percentage >= 30 THEN 'deep'
             ELSE 'light' END                                           AS promo_tier,
        units_sold_or_booked::numeric / rooms_available                 AS occupancy,
        (final_price::numeric * units_sold_or_booked)
            / (base_price::numeric * rooms_available)                   AS revenue_yield,
        (base_price::numeric * rooms_available)                         AS potential_revenue,
        (units_sold_or_booked = rooms_available)                        AS sold_out
    FROM pricing_transactions
),
with_baseline AS (
    SELECT *,
           AVG(revenue_yield) FILTER (WHERE promo_tier = 'normal')
               OVER (PARTITION BY customer_segment, event_flag)         AS baseline_yield
    FROM scored
),
cells AS (
    SELECT
        customer_segment,
        event_flag,
        COUNT(*) FILTER (WHERE promo_tier = 'normal')                   AS n_normal,
        COUNT(*) FILTER (WHERE promo_tier = 'deep')                     AS n_deep,
        AVG(occupancy)     FILTER (WHERE promo_tier = 'normal')         AS occ_normal,
        AVG(occupancy)     FILTER (WHERE promo_tier = 'deep')           AS occ_deep,
        AVG(revenue_yield) FILTER (WHERE promo_tier = 'normal')         AS yield_normal,
        AVG(revenue_yield) FILTER (WHERE promo_tier = 'deep')           AS yield_deep,
        AVG(sold_out::int) FILTER (WHERE promo_tier = 'deep')           AS pct_deep_sold_out,
        SUM(potential_revenue * (revenue_yield - baseline_yield))
            FILTER (WHERE promo_tier = 'deep')                          AS net_revenue_impact_idr
    FROM with_baseline
    GROUP BY customer_segment, event_flag
    HAVING COUNT(*) FILTER (WHERE promo_tier = 'normal') >= 5
       AND COUNT(*) FILTER (WHERE promo_tier = 'deep')   >= 5
)
SELECT
    customer_segment,
    event_flag,
    n_normal,
    n_deep,
    CASE WHEN LEAST(n_normal, n_deep) >= 15 THEN 'High'
         WHEN LEAST(n_normal, n_deep) >= 10 THEN 'Medium'
         ELSE 'Low (directional)' END                                   AS sample_confidence,
    ROUND(100 * occ_normal, 1)                                          AS occupancy_normal_pct,
    ROUND(100 * occ_deep,   1)                                          AS occupancy_deep_pct,
    ROUND(100 * yield_normal, 1)                                        AS yield_normal_pct,
    ROUND(100 * yield_deep,   1)                                        AS yield_deep_pct,
    ROUND(100 * (yield_deep / yield_normal - 1), 1)                     AS revenue_delta_pct,
    ROUND(100 * pct_deep_sold_out, 1)                                   AS deep_sold_out_pct,
    ROUND(net_revenue_impact_idr / 1e6, 1)                              AS net_revenue_impact_idr_mn,
    CASE WHEN yield_deep < yield_normal THEN 'CANNIBALIZATION'
         ELSE 'Incremental' END                                         AS verdict,
    RANK() OVER (ORDER BY yield_deep / yield_normal ASC)                AS severity_rank   -- 1 = worst
FROM cells
ORDER BY severity_rank;
