-- filepath: dbt_project/models/stage/stg_fmp_financial_ratios.sql

{{ config(materialized='view') }}

{%- set yaml_metadata -%}
source_model: "base_fmp_financial_ratios"
derived_columns:
  COMPANY_BK: "symbol"
  RECORD_SOURCE: "record_source"
  LOAD_DATE: "ingestion_timestamp"
  RATIO_DATE: "ratio_date"
  PERIOD: "period"
  CURRENTRATIO: "currentratio"
  DEBTRATIO: "debtratio"
  PRICEEARNINGSRATIO: "priceearningsratio"
  NETPROFITMARGIN: "netprofitmargin"
  RETURNONEQUITY: "returnonequity"
hashed_columns:
  HK_COMPANY_PK:
    - "symbol"
  HASHDIFF_RATIOS:
    is_hashdiff: true
    columns:
      - "currentratio"
      - "debtratio"
      - "priceearningsratio"
      - "netprofitmargin"
      - "returnonequity"
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata_dict['source_model'],
                     derived_columns=metadata_dict['derived_columns'],
                     hashed_columns=metadata_dict['hashed_columns']) }}