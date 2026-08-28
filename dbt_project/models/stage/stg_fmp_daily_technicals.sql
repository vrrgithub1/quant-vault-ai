-- filepath: dbt_project/models/stage/stg_fmp_daily_technicals.sql

{{ config(materialized='view') }}

WITH prices AS (
    SELECT 
        hk_company_pk,
        company_bk AS symbol,
        price_date,
        close_price,
        volume,
        load_date,
        record_source
    FROM {{ ref('stg_fmp_daily_prices') }}
),

daily_returns AS (
    SELECT 
        hk_company_pk,
        symbol,
        price_date,
        close_price,
        volume,
        LAG(close_price, 1) OVER (PARTITION BY symbol ORDER BY price_date) AS prev_close,
        (close_price - LAG(close_price, 1) OVER (PARTITION BY symbol ORDER BY price_date)) 
            / NULLIF(LAG(close_price, 1) OVER (PARTITION BY symbol ORDER BY price_date), 0) AS daily_return,
        GREATEST(close_price - LAG(close_price, 1) OVER (PARTITION BY symbol ORDER BY price_date), 0) AS gain,
        GREATEST(LAG(close_price, 1) OVER (PARTITION BY symbol ORDER BY price_date) - close_price, 0) AS loss
    FROM prices
),

rsi_prep AS (
    SELECT 
        hk_company_pk,
        symbol,
        price_date,
        close_price,
        volume,
        daily_return,
        AVG(close_price) OVER (PARTITION BY symbol ORDER BY price_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20_val,
        AVG(close_price) OVER (PARTITION BY symbol ORDER BY price_date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50_val,
        AVG(gain) OVER (PARTITION BY symbol ORDER BY price_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_gain_14,
        AVG(loss) OVER (PARTITION BY symbol ORDER BY price_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_loss_14,
        (LEAD(close_price, 5) OVER (PARTITION BY symbol ORDER BY price_date) - close_price) 
            / NULLIF(close_price, 0) AS target_5d_return
    FROM daily_returns
)

SELECT 
    hk_company_pk,
    symbol,
    price_date,
    close_price,
    volume,
    -- Distance from SMAs
    (close_price / NULLIF(sma_20_val, 0)) - 1 AS dist_sma_20,
    (close_price / NULLIF(sma_50_val, 0)) - 1 AS dist_sma_50,
    -- 20-day Historical Volatility
    STDDEV(daily_return) OVER (PARTITION BY symbol ORDER BY price_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS vol_20d,
    -- Safe 14-day RSI (Handles zero loss condition)
    CASE 
        WHEN avg_loss_14 = 0 AND avg_gain_14 > 0 THEN 100.0
        WHEN avg_loss_14 = 0 AND avg_gain_14 = 0 THEN 50.0
        ELSE 100.0 - (100.0 / (1.0 + (avg_gain_14 / avg_loss_14)))
    END AS rsi_14,
    target_5d_return
FROM rsi_prep