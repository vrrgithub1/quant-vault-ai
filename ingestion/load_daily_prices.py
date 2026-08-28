# filepath: ingestion/load_daily_prices.py

import os
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Clear potential TLS environment variables
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

def fetch_daily_prices(ticker: str) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "historical" not in data:
        print(f"⚠️ No price data found for {ticker}")
        return pd.DataFrame()
        
    df = pd.DataFrame(data["historical"])
    df["symbol"] = ticker
    df["ingestion_timestamp"] = pd.Timestamp.now()
    df["record_source"] = "FMP_HISTORICAL_PRICES"
    return df

def main():
    all_prices = []
    for ticker in TICKERS:
        print(f"📥 Fetching daily prices for {ticker}...")
        df = fetch_daily_prices(ticker)
        if not df.empty:
            all_prices.append(df)
            
    if all_prices:
        combined_df = pd.concat(all_prices, ignore_index=True)
        combined_df.columns = [col.lower().replace(' ', '_') for col in combined_df.columns]
        
        # Truncate existing data to prevent PostgreSQL DDL dependency drop error
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
            conn.execute(text("TRUNCATE TABLE raw.raw_fmp_daily_prices;"))
        
        # Append fresh combined prices safely
        combined_df.to_sql(
            name="raw_fmp_daily_prices",
            con=engine,
            schema="raw",
            if_exists="append",
            index=False
        )
        print(f"✅ Successfully ingested {len(combined_df)} price records into raw.raw_fmp_daily_prices")

def run_price_ingestion():
    print("📥 Starting Daily Price Ingestion from FMP...")
    all_prices = []
    for ticker in TICKERS:
        print(f"📥 Fetching daily prices for {ticker}...")
        df = fetch_daily_prices(ticker)
        if not df.empty:
            all_prices.append(df)
            
    if all_prices:
        combined_df = pd.concat(all_prices, ignore_index=True)
        combined_df.columns = [col.lower().replace(' ', '_') for col in combined_df.columns]
        
        # Truncate existing data to prevent PostgreSQL DDL dependency drop error
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
            conn.execute(text("TRUNCATE TABLE raw.raw_fmp_daily_prices;"))
        
        # Append fresh combined prices safely
        combined_df.to_sql(
            name="raw_fmp_daily_prices",
            con=engine,
            schema="raw",
            if_exists="append",
            index=False
        )
        print(f"✅ Successfully ingested {len(combined_df)} price records into raw.raw_fmp_daily_prices")

    print("✅ Daily Price Ingestion Complete.")

if __name__ == "__main__":
    run_price_ingestion()