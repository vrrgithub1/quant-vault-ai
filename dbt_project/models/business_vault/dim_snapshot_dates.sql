-- filepath: dbt_project/models/business_vault/dim_snapshot_dates.sql

{{ config(materialized='table', schema='business_vault') }}

WITH date_spine AS (
    SELECT 
        generate_series(
            '2020-01-01'::DATE, 
            CURRENT_DATE, 
            '1 day'::INTERVAL
        )::DATE AS as_of_date
)

SELECT as_of_date FROM date_spine