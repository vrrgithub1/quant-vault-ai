-- filepath: dbt_project/models/stage/base_fmp_financial_ratios.sql

{{ config(materialized='view') }}

SELECT 
    symbol,
    date::DATE AS ratio_date,
    period,
    currentratio,
    debtratio,
    priceearningsratio,
    netprofitmargin,
    returnonequity,
    ingestion_timestamp,
    record_source
FROM {{ source('raw_fmp', 'raw_fmp_financial_ratios') }}