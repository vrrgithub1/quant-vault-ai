# filepath: scripts/test_vector_query.py

import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer

# 1. Load Environment & Database Connection
load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "quant_vault_db")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# 2. Encode Search Query using SentenceTransformers
search_text = "AI cloud infrastructure growth and generative intelligence"
print(f"🔍 Encoding query string: '{search_text}'...\n")

model = SentenceTransformer("all-MiniLM-L6-v2")
query_embedding = model.encode(search_text).tolist()

# 3. Formulate & Execute Hybrid SQL Query
hybrid_query = text("""
    SELECT 
        h.company_bk as symbol,
        e.doc_type,
        LEFT(e.summary_text, 65) AS summary_snippet,
        r.priceearningsratio as pe_ratio,
        r.returnonequity as return_on_equity,
        ROUND(CAST(1 - (e.embedding <=> CAST(:query_vec AS vector)) AS numeric), 4) AS text_similarity
    FROM raw_vault.sat_company_text_embeddings e
    JOIN raw_vault.hub_company h 
        ON e.hk_company_pk = h.hk_company_pk
    JOIN raw_vault.sat_company_financial_ratios r 
        ON h.hk_company_pk = r.hk_company_pk
    ORDER BY e.embedding <=> CAST(:query_vec AS vector) ASC
    LIMIT 10;
""")

# 4. Fetch & Display Results
df = pd.read_sql(hybrid_query, engine, params={"query_vec": str(query_embedding)})

print("=========================================================================================")
print(f"   HYBRID VECTOR SEARCH & FINANCIAL METRICS RESULTS (Query: '{search_text}')")
print("=========================================================================================")
print(df.to_string(index=False))
print("=========================================================================================\n")
