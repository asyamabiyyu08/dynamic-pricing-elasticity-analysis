-- =====================================================================================
-- Q5 | OPTIMAL DISCOUNT DEPTH MATRIX  (segment x demand context)
-- -------------------------------------------------------------------------------------
-- Turns the diagnostics of Q1-Q4 into a decision table:
--   "For this segment, in this demand context, which discount band maximises Revenue Yield?"
--   demand_context: Peak = national holiday or weekend ; Non-peak = everything else.
--   The 0% band is the benchmark; if it ranks #1, the right discount is *no discount*.
-- Window functions: FIRST_VALUE (benchmark), RANK (optimal band).
-- =====================================================================================
WITH tagged AS (
    SELECT
        customer_segment,
        CASE WHEN event_flag IN ('Libur Nasional', 'Weekend')
             THEN 'Peak (holiday/weekend)' ELSE 'Non-peak' END       AS demand_context,
        CASE WHEN discount_percentage = 0  THEN 0
             WHEN discount_percentage <= 10 THEN 1
             WHEN discount_percentage <= 20 THEN 2
             WHEN discount_percentage <= 30 THEN 3
             ELSE 4 END                                              AS band_order,
        CASE WHEN discount_percentage = 0  THEN '0%'
             WHEN discount_percentage <= 10 THEN '1-10%'
             WHEN discount_percentage <= 20 THEN '11-20%'
             WHEN discount_percentage <= 30 THEN '21-30%'
             ELSE '31%+' END                                         AS discount_band,
        units_sold_or_booked::numeric / rooms_available              AS occupancy,
        (final_price::numeric * units_sold_or_booked)
            / (base_price::numeric * rooms_available)                AS revenue_yield
    FROM pricing_transactions
),
bands AS (
    SELECT customer_segment, demand_context, band_order, discount_band,
           COUNT(*)            AS n_records,
           AVG(occupancy)      AS avg_occupancy,
           AVG(revenue_yield)  AS avg_yield
    FROM tagged
    GROUP BY customer_segment, demand_context, band_order, discount_band
    HAVING COUNT(*) >= 15
),
ranked AS (
    SELECT *,
           FIRST_VALUE(avg_yield) OVER (PARTITION BY customer_segment, demand_context
                                        ORDER BY band_order)                        AS yield_full_price,
           RANK()         OVER (PARTITION BY customer_segment, demand_context
                                ORDER BY avg_yield DESC)                            AS yield_rank
    FROM bands
)
SELECT
    customer_segment,
    demand_context,
    discount_band,
    n_records,
    ROUND(100 * avg_occupancy, 1)                           AS occupancy_pct,
    ROUND(100 * avg_yield, 1)                               AS revenue_yield_pct,
    ROUND(100 * (avg_yield / yield_full_price - 1), 1)      AS vs_full_price_pct,
    yield_rank,
    CASE WHEN yield_rank = 1 THEN 'OPTIMAL' ELSE '' END     AS recommendation
FROM ranked
ORDER BY customer_segment, demand_context, band_order;
