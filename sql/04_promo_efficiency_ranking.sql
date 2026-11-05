-- =====================================================================================
-- Q4 | TOP 10 PROPERTIES BY PROMO EFFICIENCY
--    (revenue uplift achieved per percentage point of discount given)
-- -------------------------------------------------------------------------------------
-- For each property:
--   Revenue Uplift %     = avg Revenue Yield on promo records / avg Revenue Yield at full price - 1
--   Promo Efficiency     = Revenue Uplift % / average discount depth (pp)
--                          e.g. +0.8 means: every 1pp of discount returned +0.8% revenue.
--                          Negative = discounting destroys revenue at this property.
-- Guard-rails: a property needs >=10 full-price and >=20 promo records to be ranked.
-- Window functions: RANK() overall and PARTITION BY category.
-- =====================================================================================
WITH rows_scored AS (
    SELECT
        property_or_product_id,
        category,
        discount_percentage,
        (final_price::numeric * units_sold_or_booked)
            / (base_price::numeric * rooms_available)   AS revenue_yield,
        final_price::numeric * units_sold_or_booked     AS revenue
    FROM pricing_transactions
),
prop AS (
    SELECT
        property_or_product_id,
        category,
        COUNT(*) FILTER (WHERE discount_percentage = 0)          AS n_full_price,
        COUNT(*) FILTER (WHERE discount_percentage > 0)          AS n_promo,
        AVG(revenue_yield) FILTER (WHERE discount_percentage = 0) AS yield_full,
        AVG(revenue_yield) FILTER (WHERE discount_percentage > 0) AS yield_promo,
        AVG(revenue)       FILTER (WHERE discount_percentage = 0) AS avg_rev_full,
        AVG(revenue)       FILTER (WHERE discount_percentage > 0) AS avg_rev_promo,
        AVG(discount_percentage) FILTER (WHERE discount_percentage > 0) AS avg_discount_pp
    FROM rows_scored
    GROUP BY property_or_product_id, category
    HAVING COUNT(*) FILTER (WHERE discount_percentage = 0) >= 10
       AND COUNT(*) FILTER (WHERE discount_percentage > 0) >= 20
),
scored AS (
    SELECT *,
           100 * (yield_promo / yield_full - 1)                         AS revenue_uplift_pct,
           100 * (yield_promo / yield_full - 1) / avg_discount_pp       AS uplift_per_discount_pp
    FROM prop
),
ranked AS (
    SELECT *,
           RANK() OVER (ORDER BY uplift_per_discount_pp DESC)                       AS overall_rank,
           RANK() OVER (PARTITION BY category ORDER BY uplift_per_discount_pp DESC) AS rank_in_category,
           COUNT(*) OVER ()                                                         AS n_ranked
    FROM scored
)
SELECT
    overall_rank,
    property_or_product_id,
    category,
    n_full_price,
    n_promo,
    ROUND(avg_discount_pp, 1)            AS avg_discount_pp,
    ROUND(avg_rev_full  / 1e6, 1)        AS avg_rev_full_idr_mn,
    ROUND(avg_rev_promo / 1e6, 1)        AS avg_rev_promo_idr_mn,
    ROUND(revenue_uplift_pct, 1)         AS revenue_uplift_pct,
    ROUND(uplift_per_discount_pp, 2)     AS uplift_per_discount_pp,
    rank_in_category,
    n_ranked
FROM ranked
WHERE overall_rank <= 10
ORDER BY overall_rank;
