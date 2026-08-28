# filepath: scripts/query_hybrid_quant.py

import os
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

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

print("🧠 Loading SentenceTransformer model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def search_quant_vault(query_text: str, top_k: int = 3):
    print(f"\n🔍 Searching Quant Vault for semantic query: '{query_text}'...")
    
    # Generate vector string
    query_vector = embedder.encode(query_text).tolist()
    vec_str = str(query_vector)
    
    # Using CAST(:query_vec AS vector) prevents SQLAlchemy parameter binding syntax collisions
    sql_query = text("""
        WITH vector_matches AS (
            SELECT 
                s.hk_company_pk,
                s.summary_text,
                1 - (s.embedding <=> CAST(:query_vec AS vector)) AS cosine_similarity
            FROM raw_vault.sat_company_text_embeddings s
            ORDER BY s.embedding <=> CAST(:query_vec AS vector) ASC
            LIMIT :top_k
        ),
        
        company_info AS (
            SELECT 
                h.hk_company_pk,
                h.company_bk AS symbol
            FROM raw_vault_raw_vault.hub_company h
        )
        
        SELECT 
            c.symbol,
            v.cosine_similarity,
            v.summary_text,
            f.feature_date,
            f.pe_ratio,
            f.return_on_equity,
            f.rsi_14,
            f.target_5d_return
        FROM vector_matches v
        JOIN company_info c ON v.hk_company_pk = c.hk_company_pk
        LEFT JOIN LATERAL (
            SELECT * 
            FROM raw_vault_info_mart.fct_company_quarterly_features f_sub
            WHERE f_sub.symbol = c.symbol
            ORDER BY f_sub.feature_date DESC
            LIMIT 1
        ) f ON TRUE
        ORDER BY v.cosine_similarity DESC;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(sql_query, conn, params={"query_vec": vec_str, "top_k": top_k})
        
    print("\n================ Hybrid Semantic & Quantitative Search Results ================")
    for idx, row in df.iterrows():
        print(f"\n📌 #{idx+1} | Stock: {row['symbol']} | Cosine Similarity: {row['cosine_similarity']:.4f}")
        print(f"   Summary: {row['summary_text'][:150]}...")
        pe_val = f"{row['pe_ratio']:.2f}" if pd.notnull(row['pe_ratio']) else "N/A"
        roe_val = f"{row['return_on_equity']:.2%}" if pd.notnull(row['return_on_equity']) else "N/A"
        rsi_val = f"{row['rsi_14']:.2f}" if pd.notnull(row['rsi_14']) else "N/A"
        print(f"   Latest Features -> P/E: {pe_val} | ROE: {roe_val} | RSI: {rsi_val}")

if __name__ == "__main__":
    search_quant_vault("AI cloud infrastructure growth and generative intelligence", top_k=3)
    search_quant_vault("financial performance quarterly revenue dividend profit", top_k=3)