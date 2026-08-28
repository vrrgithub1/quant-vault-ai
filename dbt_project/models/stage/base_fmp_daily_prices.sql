-- filepath: dbt_project/models/stage/base_fmp_daily_prices.sql

{{ config(materialized='view') }}

SELECT 
    symbol,
    date::DATE AS price_date,
    open::NUMERIC AS open_price,
    high::NUMERIC AS high_price,
    low::NUMERIC AS low_price,
    close::NUMERIC AS close_price,
    volume::NUMERIC AS volume,
    ingestion_timestamp,
    record_source
FROM {{ source('raw_fmp', 'raw_fmp_daily_prices') }}