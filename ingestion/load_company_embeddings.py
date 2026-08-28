# filepath: ingestion/load_company_embeddings.py

import os
import hashlib
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer

os.environ.pop("CURL_CA_BUNDLE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "quant_vault_db")
FMP_API_KEY = os.getenv("FMP_API_KEY")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMZN', 'JPM', 'BAC', 'JNJ', 'WMT', 'XOM']

# Load open-source 384-dimensional sentence transformer model
print("🧠 Loading local SentenceTransformer model (all-MiniLM-L6-v2)...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def get_md5_hash(val: str) -> bytes:
    return hashlib.md5(val.encode('utf-8')).digest()

def fetch_company_press_releases(ticker: str) -> list:
    url = f"https://financialmodelingprep.com/api/v3/press-releases/{ticker}?limit=5&apikey={FMP_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if not isinstance(data, list):
        return []
    return data

def main():
    records = []
    
    for ticker in TICKERS:
        print(f"📥 Fetching press releases for {ticker}...")
        releases = fetch_company_press_releases(ticker)
        
        for rel in releases:
            text_content = f"{rel.get('title', '')}. {rel.get('text', '')[:500]}"
            if not text_content.strip():
                continue
                
            # Generate 384-dim dense vector embedding
            embedding_vector = embedder.encode(text_content).tolist()
            
            # Data Vault standard keys
            hk_company_pk = get_md5_hash(ticker)
            hashdiff = get_md5_hash(text_content)
            
            records.append({
                'hk_company_pk': hk_company_pk,
                'load_date': pd.Timestamp.now(),
                'doc_type': 'PRESS_RELEASE',
                'summary_text': text_content,
                'embedding': str(embedding_vector),  # Formatted for pgvector insert
                'hashdiff': hashdiff,
                'record_source': 'FMP_PRESS_RELEASE'
            })
            
    if records:
        print("💾 Inserting text embeddings into raw_vault.sat_company_text_embeddings...")
        insert_query = text("""
            INSERT INTO raw_vault.sat_company_text_embeddings 
            (hk_company_pk, load_date, doc_type, summary_text, embedding, hashdiff, record_source)
            VALUES (:hk_company_pk, :load_date, :doc_type, :summary_text, :embedding, :hashdiff, :record_source)
            ON CONFLICT DO NOTHING;
        """)
        
        with engine.begin() as conn:
            conn.execute(insert_query, records)
            
        print(f"✅ Successfully processed and stored {len(records)} text embeddings!")

def run_embeddings_ingestion():
    print("🧠 Starting Vector Text Embedding Ingestion...")
    records = []
    
    for ticker in TICKERS:
        print(f"📥 Fetching press releases for {ticker}...")
        releases = fetch_company_press_releases(ticker)
        
        for rel in releases:
            text_content = f"{rel.get('title', '')}. {rel.get('text', '')[:500]}"
            if not text_content.strip():
                continue
                
            # Generate 384-dim dense vector embedding
            embedding_vector = embedder.encode(text_content).tolist()
            
            # Data Vault standard keys
            hk_company_pk = get_md5_hash(ticker)
            hashdiff = get_md5_hash(text_content)
            
            records.append({
                'hk_company_pk': hk_company_pk,
                'load_date': pd.Timestamp.now(),
                'doc_type': 'PRESS_RELEASE',
                'summary_text': text_content,
                'embedding': str(embedding_vector),  # Formatted for pgvector insert
                'hashdiff': hashdiff,
                'record_source': 'FMP_PRESS_RELEASE'
            })
            
    if records:
        print("💾 Inserting text embeddings into raw_vault.sat_company_text_embeddings...")
        insert_query = text("""
            INSERT INTO raw_vault.sat_company_text_embeddings 
            (hk_company_pk, load_date, doc_type, summary_text, embedding, hashdiff, record_source)
            VALUES (:hk_company_pk, :load_date, :doc_type, :summary_text, :embedding, :hashdiff, :record_source)
            ON CONFLICT DO NOTHING;
        """)
        
        with engine.begin() as conn:
            conn.execute(insert_query, records)
            
        print(f"✅ Successfully processed and stored {len(records)} text embeddings!")
    print("✅ Vector Embedding Ingestion Complete.")

if __name__ == "__main__":
    run_embeddings_ingestion()