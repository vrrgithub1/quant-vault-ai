# filepath: ingestion/load_financial_ratios.py

import os
import requests
import pandas as pd
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
FMP_API_KEY = os.getenv("FMP_API_KEY")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

TICKERS = [
    # Tech
    'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMZN', 'META', 'TSLA', 'AMD',
    # Financials
    'JPM', 'BAC', 'GS', 'MS',
    # Healthcare
    'JNJ', 'PFE', 'UNH', 'ABBV',
    # Industrial & Consumer
    'WMT', 'PG', 'CAT', 'DIS', 'XOM', 'CVX'
]

def fetch_ratios(ticker: str) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/ratios/{ticker}?period=quarter&limit=40&apikey={FMP_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if not isinstance(data, list) or len(data) == 0:
        print(f"⚠️ No ratios found for {ticker}")
        return pd.DataFrame()
        
    df = pd.DataFrame(data)
    df["symbol"] = ticker
    df["ingestion_timestamp"] = pd.Timestamp.now()
    df["record_source"] = "FMP_RATIOS_API"
    return df

def main():
    all_ratios = []
    for ticker in TICKERS:
        print(f"📥 Fetching ratios for {ticker}...")
        df = fetch_ratios(ticker)
        if not df.empty:
            all_ratios.append(df)
            
    if all_ratios:
        combined_df = pd.concat(all_ratios, ignore_index=True)
        combined_df.columns = [col.lower().replace(' ', '_') for col in combined_df.columns]
        
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
            conn.execute(text("TRUNCATE TABLE raw.raw_fmp_financial_ratios;"))
            
        combined_df.to_sql(
            name="raw_fmp_financial_ratios",
            con=engine,
            schema="raw",
            if_exists="append",
            index=False
        )
        print(f"✅ Successfully ingested {len(combined_df)} ratio records into raw.raw_fmp_financial_ratios")

def run_ratio_ingestion():
    print("📥 Starting Financial Ratio Ingestion from FMP...")
    all_ratios = []
    for ticker in TICKERS:
        print(f"📥 Fetching ratios for {ticker}...")
        df = fetch_ratios(ticker)
        if not df.empty:
            all_ratios.append(df)
            
    if all_ratios:
        combined_df = pd.concat(all_ratios, ignore_index=True)
        combined_df.columns = [col.lower().replace(' ', '_') for col in combined_df.columns]
        
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
            conn.execute(text("TRUNCATE TABLE raw.raw_fmp_financial_ratios;"))
            
        combined_df.to_sql(
            name="raw_fmp_financial_ratios",
            con=engine,
            schema="raw",
            if_exists="append",
            index=False
        )
        print(f"✅ Successfully ingested {len(combined_df)} ratio records into raw.raw_fmp_financial_ratios")
    print("✅ Financial Ratio Ingestion Complete.")

if __name__ == "__main__":
    run_ratio_ingestion()