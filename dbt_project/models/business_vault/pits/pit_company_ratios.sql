-- filepath: dbt_project/models/business_vault/pits/pit_company_ratios.sql

{{ config(materialized='table', schema='business_vault') }}

{%- set yaml_metadata -%}
source_model: "hub_company"
src_pk: "HK_COMPANY_PK"
as_of_dates_table: "dim_snapshot_dates"
satellites:
  sat_company_financial_ratios:
    pk:
      PK: "HK_COMPANY_PK"
    ldts:
      LDTS: "LOAD_DATE"
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.pit(source_model=metadata_dict['source_model'],
                   src_pk=metadata_dict['src_pk'],
                   as_of_dates_table=metadata_dict['as_of_dates_table'],
                   satellites=metadata_dict['satellites']) }}