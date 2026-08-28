# filepath: ingestion/setup_vector_vault.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

os.environ.pop("CURL_CA_BUNDLE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "quant_vault_db")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

DDL_SCRIPT = """
-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create Schema if not exists
CREATE SCHEMA IF NOT EXISTS raw_vault;

-- 3. Create Satellite Table for Text Embeddings (384 dimensions for sentence-transformers/all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS raw_vault.sat_company_text_embeddings (
    hk_company_pk BYTEA NOT NULL,
    load_date TIMESTAMP WITH TIME ZONE NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    summary_text TEXT NOT NULL,
    embedding vector(384),
    hashdiff BYTEA NOT NULL,
    record_source VARCHAR(100) NOT NULL,
    PRIMARY KEY (hk_company_pk, load_date)
);

-- 4. Create Cosine Distance IVFFlat Index for fast similarity searches
CREATE INDEX IF NOT EXISTS idx_sat_company_text_vec 
ON raw_vault.sat_company_text_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 10);
"""

def main():
    with engine.begin() as conn:
        conn.execute(text(DDL_SCRIPT))
    print("✅ pgvector extension enabled and raw_vault.sat_company_text_embeddings created successfully.")

if __name__ == "__main__":
    main()