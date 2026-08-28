-- filepath: dbt_project/models/stage/stg_fmp_daily_prices.sql

{{ config(materialized='view') }}

{%- set yaml_metadata -%}
source_model: "base_fmp_daily_prices"
derived_columns:
  COMPANY_BK: "symbol"
  RECORD_SOURCE: "record_source"
  LOAD_DATE: "ingestion_timestamp"
  PRICE_DATE: "price_date"
  CLOSE_PRICE: "close_price"
  VOLUME: "volume"
hashed_columns:
  HK_COMPANY_PK:
    - "symbol"
  HASHDIFF_PRICES:
    is_hashdiff: true
    columns:
      - "close_price"
      - "volume"
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata_dict['source_model'],
                     derived_columns=metadata_dict['derived_columns'],
                     hashed_columns=metadata_dict['hashed_columns']) }}