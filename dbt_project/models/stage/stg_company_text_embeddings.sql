-- filepath: dbt_project/models/stage/stg_company_text_embeddings.sql

{{ config(materialized='view') }}

SELECT 
    hk_company_pk,
    load_date,
    doc_type,
    summary_text,
    embedding,
    hashdiff,
    record_source
FROM {{ source('raw_vault', 'sat_company_text_embeddings') }}