-- =====================================================================================
-- Q3 | WEEKEND vs WEEKDAY PERFORMANCE BY CUSTOMER SEGMENT
-- -------------------------------------------------------------------------------------
-- Hospitality KPIs
--   Occupancy = room-nights booked / room-nights available
--   ADR       = Average Daily Rate  = revenue / room-nights booked
--   RevPAR    = Revenue per Available Room = revenue / room-nights available
--               (RevPAR = ADR x Occupancy; the industry's headline yield metric)
-- Weekend = Saturday/Sunday (ISODOW 6,7), derived from the date itself, NOT from event_flag
-- (a national holiday on a Tuesday is still a weekday here; see Q2/Q5 for holiday effects).
-- Window functions: LAG for weekend-vs-weekday deltas, SUM() OVER for revenue mix,
--                   RANK() OVER for cross-segment ranking.
-- =====================================================================================
WITH tagged AS (
    SELECT
        customer_segment,
        CASE WHEN EXTRACT(ISODOW FROM date) IN (6, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type,
        discount_percentage,
        units_sold_or_booked,
        rooms_available,
        final_price::numeric * units_sold_or_booked AS revenue
    FROM pricing_transactions
),
agg AS (
    SELECT
        customer_segment,
        day_type,
        COUNT(*)                                        AS n_records,
        SUM(units_sold_or_booked)                       AS room_nights,
        SUM(rooms_available)                            AS rooms_available,
        SUM(revenue)                                    AS revenue,
        AVG(discount_percentage)                        AS avg_discount_pct,
        AVG((discount_percentage > 0)::int)             AS promo_penetration
    FROM tagged
    GROUP BY customer_segment, day_type
),
kpi AS (
    SELECT *,
           room_nights::numeric / rooms_available       AS occupancy,
           revenue / room_nights                        AS adr,
           revenue / rooms_available                    AS revpar
    FROM agg
)
SELECT
    customer_segment,
    day_type,
    n_records,
    ROUND(100 * occupancy, 1)                                         AS occupancy_pct,
    ROUND(adr / 1e3)                                                  AS adr_idr_k,
    ROUND(revpar / 1e3)                                               AS revpar_idr_k,
    ROUND(avg_discount_pct, 1)                                        AS avg_discount_pct,
    ROUND(100 * promo_penetration, 1)                                 AS promo_penetration_pct,
    ROUND(100 * revenue / SUM(revenue) OVER (PARTITION BY customer_segment), 1) AS pct_of_segment_revenue,
    -- weekend vs weekday deltas (value shown on the Weekend row only)
    ROUND(100 * (occupancy - LAG(occupancy) OVER w), 1)               AS occupancy_delta_pts,
    ROUND(100 * (adr    / LAG(adr)    OVER w - 1), 1)                 AS adr_delta_pct,
    ROUND(100 * (revpar / LAG(revpar) OVER w - 1), 1)                 AS revpar_delta_pct,
    RANK() OVER (PARTITION BY day_type ORDER BY revpar DESC)          AS revpar_rank_within_daytype
FROM kpi
WINDOW w AS (PARTITION BY customer_segment ORDER BY day_type)   -- 'Weekday' sorts before 'Weekend'
ORDER BY customer_segment, day_type;
