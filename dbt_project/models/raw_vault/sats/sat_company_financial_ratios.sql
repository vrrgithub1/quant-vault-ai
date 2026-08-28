-- filepath: dbt_project/models/raw_vault/sats/sat_company_financial_ratios.sql

{{ config(materialized='incremental') }}

{%- set yaml_metadata -%}
src_pk: "HK_COMPANY_PK"
src_hashdiff: "HASHDIFF_RATIOS"
src_payload:
  - "ratio_date"
  - "period"
  - "currentratio"
  - "debtratio"
  - "priceearningsratio"
  - "netprofitmargin"
  - "returnonequity"
src_ldts: "LOAD_DATE"
src_source: "RECORD_SOURCE"
source_model: "stg_fmp_financial_ratios"
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.sat(src_pk=metadata_dict['src_pk'],
                   src_hashdiff=metadata_dict['src_hashdiff'],
                   src_payload=metadata_dict['src_payload'],
                   src_ldts=metadata_dict['src_ldts'],
                   src_source=metadata_dict['src_source'],
                   source_model=metadata_dict['source_model']) }}