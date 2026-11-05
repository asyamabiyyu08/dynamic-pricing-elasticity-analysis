-- =====================================================================================
-- 00_schema_and_load.sql   |   PostgreSQL 12+
-- Creates the fact table and loads the synthetic CSV.
-- Run from the project root:   psql -d pricing -f sql/00_schema_and_load.sql
-- =====================================================================================
DROP TABLE IF EXISTS pricing_transactions;

CREATE TABLE pricing_transactions (
    transaction_id          TEXT PRIMARY KEY,
    date                    DATE     NOT NULL,                       -- stay date
    property_or_product_id  TEXT     NOT NULL,
    category                TEXT     NOT NULL,
    base_price              INTEGER  NOT NULL CHECK (base_price > 0),            -- dynamic rack rate (IDR)
    discount_percentage     SMALLINT NOT NULL CHECK (discount_percentage BETWEEN 0 AND 90),
    final_price             INTEGER  NOT NULL CHECK (final_price > 0),           -- price paid per room-night
    units_sold_or_booked    INTEGER  NOT NULL CHECK (units_sold_or_booked > 0),  -- room-nights booked
    customer_segment        TEXT     NOT NULL,
    event_flag              TEXT     NOT NULL,
    competitor_price        INTEGER,                                             -- NULL = scrape failure
    rooms_available         INTEGER  NOT NULL CHECK (rooms_available > 0),       -- allocated inventory
    CHECK (units_sold_or_booked <= rooms_available)
);

-- \copy is a psql client-side command, so the path is relative to where you run psql.
\copy pricing_transactions FROM 'data/pricing_transactions.csv' WITH (FORMAT csv, HEADER true)

CREATE INDEX idx_pt_date     ON pricing_transactions (date);
CREATE INDEX idx_pt_property ON pricing_transactions (property_or_product_id);
ANALYZE pricing_transactions;

-- Quick sanity check
SELECT COUNT(*) AS n_rows, MIN(date) AS first_day, MAX(date) AS last_day,
       COUNT(DISTINCT property_or_product_id) AS n_properties
FROM pricing_transactions;
