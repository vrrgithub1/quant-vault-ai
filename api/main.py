# filepath: api/main.py

import os
import pandas as pd
import numpy as np
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier

os.environ.pop("CURL_CA_BUNDLE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)

load_dotenv()

app = FastAPI(
    title="Quant Vault AI Production API",
    description="REST API serving ML alpha signals, portfolio analytics, and pgvector semantic searches.",
    version="1.0.0"
)

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "quant_vault_db")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Response Schemas
class VectorSearchResult(BaseModel):
    symbol: str
    cosine_similarity: float
    summary_text: str
    pe_ratio: Optional[float]
    return_on_equity: Optional[float]
    rsi_14: Optional[float]

class StockSignal(BaseModel):
    symbol: str
    sector: str  # <--- Added sector field
    feature_date: str
    predicted_alpha_prob: float
    quantile_rank: float
    action: str

@app.get("/")
def read_root():
    return {"status": "online", "system": "Quant Vault AI Engine v1.0"}

@app.get("/api/v1/search", response_model=List[VectorSearchResult])
def search_semantic(query: str, top_k: int = 3):
    """Perform hybrid vector similarity search across Data Vault press release embeddings."""
    try:
        query_vector = str(embedder.encode(query).tolist())
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
                SELECT h.hk_company_pk, h.company_bk AS symbol FROM raw_vault.hub_company h
            )
            SELECT 
                c.symbol,
                v.cosine_similarity,
                v.summary_text,
                f.pe_ratio,
                f.return_on_equity,
                f.rsi_14
            FROM vector_matches v
            JOIN company_info c ON v.hk_company_pk = c.hk_company_pk
            LEFT JOIN LATERAL (
                SELECT * FROM info_mart.fct_company_quarterly_features f_sub
                WHERE f_sub.symbol = c.symbol
                ORDER BY f_sub.feature_date DESC LIMIT 1
            ) f ON TRUE
            ORDER BY v.cosine_similarity DESC;
        """)
        
        with engine.connect() as conn:
            df = pd.read_sql(sql_query, conn, params={"query_vec": query_vector, "top_k": top_k})
            
        results = []
        for _, row in df.iterrows():
            results.append(VectorSearchResult(
                symbol=row['symbol'],
                cosine_similarity=float(row['cosine_similarity']),
                summary_text=row['summary_text'],
                pe_ratio=float(row['pe_ratio']) if pd.notnull(row['pe_ratio']) else None,
                return_on_equity=float(row['return_on_equity']) if pd.notnull(row['return_on_equity']) else None,
                rsi_14=float(row['rsi_14']) if pd.notnull(row['rsi_14']) else None
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# filepath: api/main.py

SECTOR_MAP = {
    'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'NVDA': 'Tech', 
    'AMZN': 'Consumer', 'META': 'Tech', 'TSLA': 'Consumer', 'AMD': 'Tech',
    'JPM': 'Financials', 'BAC': 'Financials', 'GS': 'Financials', 'MS': 'Financials',
    'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare', 'ABBV': 'Healthcare',
    'WMT': 'Consumer', 'PG': 'Consumer', 'CAT': 'Industrial', 'DIS': 'Communication', 
    'XOM': 'Energy', 'CVX': 'Energy'
}

@app.get("/api/v1/signals/latest", response_model=List[StockSignal])
def get_latest_signals():
    """Calculates live relative alpha probabilities and quantile allocations across tickers."""
    try:
        # Fetch the most recent snapshot for each symbol
        query = text("""
            SELECT DISTINCT ON (symbol)
                feature_date, symbol, dist_sma_20, dist_sma_50, vol_20d, rsi_14,
                current_ratio, debt_ratio, pe_ratio, net_profit_margin, return_on_equity
            FROM info_mart.fct_company_quarterly_features
            ORDER BY symbol, feature_date DESC;
        """)
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            
        if df.empty:
            return []
            
        # 1. Map Sectors
        df['sector'] = df['symbol'].map(SECTOR_MAP).fillna('Other')
        
        # 2. Sector Z-score Standardization
        fundamental_cols = ['current_ratio', 'debt_ratio', 'pe_ratio', 'net_profit_margin', 'return_on_equity']
        for col in fundamental_cols:
            df[f"{col}_z"] = df.groupby('sector')[col].transform(lambda x: (x - x.mean()) / (x.std() + 1e-6))
            
        # 3. Calculate Composite Alpha Score
        # Combining fundamental quality (ROE, Margin) with valuation (P/E) and technical momentum (SMA distance)
        df['composite_score'] = (
            0.35 * df['return_on_equity_z'].fillna(0) +
            0.25 * df['net_profit_margin_z'].fillna(0) -
            0.20 * df['pe_ratio_z'].fillna(0) +
            0.20 * df['dist_sma_50'].fillna(0)
        )
        
        # Convert score to alpha probability via sigmoid curve
        df['predicted_alpha_prob'] = 1 / (1 + np.exp(-df['composite_score']))
        
        # 4. Calculate Cross-Sectional Quantile Rank (0.0 to 1.0)
        df['quantile_rank'] = df['predicted_alpha_prob'].rank(pct=True)
        
        # 5. Assign Action
        def assign_action(q_rank):
            if q_rank >= 0.80:
                return "LONG"
            elif q_rank <= 0.20:
                return "SHORT"
            else:
                return "HOLD"
                
        df['action'] = df['quantile_rank'].apply(assign_action)
        
        signals = []
        for _, row in df.iterrows():
            signals.append(StockSignal(
                symbol=row['symbol'],
                sector=row['sector'],  # <--- Included sector in response
                feature_date=str(row['feature_date']),
                predicted_alpha_prob=round(float(row['predicted_alpha_prob']), 4),
                quantile_rank=round(float(row['quantile_rank']), 2),
                action=row['action']
            ))
            
        # Sort by quantile rank descending so top LONG candidates appear first
        signals.sort(key=lambda x: x.quantile_rank, reverse=True)
        return signals

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))