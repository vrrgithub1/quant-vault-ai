-- filepath: dbt_project/models/raw_vault/hubs/hub_company.sql

{{ config(materialized='incremental') }}

{%- set yaml_metadata -%}
src_pk: "HK_COMPANY_PK"
src_nk: "COMPANY_BK"
src_ldts: "LOAD_DATE"
src_source: "RECORD_SOURCE"
source_model: "stg_fmp_financial_ratios"
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.hub(src_pk=metadata_dict['src_pk'],
                    src_nk=metadata_dict['src_nk'],
                    src_ldts=metadata_dict['src_ldts'],
                    src_source=metadata_dict['src_source'],
                    source_model=metadata_dict['source_model']) }}