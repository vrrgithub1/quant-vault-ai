-- filepath: dbt_project/models/info_marts/fct_company_quarterly_features.sql

{{ config(materialized='table', schema='info_mart') }}

WITH hub AS (
    SELECT hk_company_pk, company_bk AS symbol FROM {{ ref('hub_company') }}
),
ratios AS (
    SELECT hk_company_pk, ratio_date, currentratio, debtratio, priceearningsratio, netprofitmargin, returnonequity
    FROM {{ ref('sat_company_financial_ratios') }}
),
technicals AS (
    SELECT hk_company_pk, symbol, price_date, close_price, dist_sma_20, dist_sma_50, vol_20d, rsi_14, target_5d_return
    FROM {{ ref('stg_fmp_daily_technicals') }}
)

SELECT DISTINCT ON (t.price_date, h.symbol)
    t.price_date AS feature_date,
    h.symbol,
    t.close_price,
    t.dist_sma_20,
    t.dist_sma_50,
    t.vol_20d,
    t.rsi_14,
    COALESCE(r.currentratio, 0.0) AS current_ratio,
    COALESCE(r.debtratio, 0.0) AS debt_ratio,
    COALESCE(r.priceearningsratio, 0.0) AS pe_ratio,
    COALESCE(r.netprofitmargin, 0.0) AS net_profit_margin,
    COALESCE(r.returnonequity, 0.0) AS return_on_equity,
    t.target_5d_return,
    CASE WHEN t.target_5d_return > 0.005 THEN 1 ELSE 0 END AS target_5d_class  -- Added >0.5% threshold filter
FROM technicals t
JOIN hub h ON t.hk_company_pk = h.hk_company_pk
LEFT JOIN ratios r ON h.hk_company_pk = r.hk_company_pk AND r.ratio_date <= t.price_date
WHERE t.dist_sma_50 IS NOT NULL 
  AND t.rsi_14 IS NOT NULL
  AND t.target_5d_return IS NOT NULL
ORDER BY t.price_date, h.symbol, r.ratio_date DESC