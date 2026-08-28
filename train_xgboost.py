# filepath: train_xgboost.py

import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, roc_auc_score

os.environ.pop("CURL_CA_BUNDLE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "quant_vault_db")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

SECTOR_MAP = {
    'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'NVDA': 'Tech', 
    'AMZN': 'Consumer', 'META': 'Tech', 'TSLA': 'Consumer', 'AMD': 'Tech',
    'JPM': 'Financials', 'BAC': 'Financials', 'GS': 'Financials', 'MS': 'Financials',
    'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare', 'ABBV': 'Healthcare',
    'WMT': 'Consumer', 'PG': 'Consumer', 'CAT': 'Industrial', 'DIS': 'Communication', 
    'XOM': 'Energy', 'CVX': 'Energy'
}

# filepath: train_xgboost.py

def load_feature_store() -> pd.DataFrame:
    query = """
    SELECT 
        feature_date,
        symbol,
        dist_sma_20,
        dist_sma_50,
        vol_20d,
        rsi_14,
        current_ratio,
        debt_ratio,
        pe_ratio,
        net_profit_margin,
        return_on_equity,
        target_5d_return,
        target_5d_class
    FROM info_mart.fct_company_quarterly_features  -- <--- Updated from raw_vault_info_mart
    ORDER BY feature_date ASC
    """
    df = pd.read_sql(query, engine)
    df['sector'] = df['symbol'].map(SECTOR_MAP).fillna('Other')
    return df

def train_and_evaluate():
    print("📊 Loading multi-sector feature store...")
    df = load_feature_store()
    
    fundamental_cols = ['current_ratio', 'debt_ratio', 'pe_ratio', 'net_profit_margin', 'return_on_equity']
    technical_cols = ['dist_sma_20', 'dist_sma_50', 'vol_20d', 'rsi_14']
    
    for col in fundamental_cols:
        df[f"{col}_z"] = df.groupby('sector')[col].transform(lambda x: (x - x.mean()) / (x.std() + 1e-6))
    
    df['daily_median_return'] = df.groupby('feature_date')['target_5d_return'].transform('median')
    df['target_alpha_class'] = (df['target_5d_return'] > df['daily_median_return']).astype(int)
    
    feature_cols = [f"{col}_z" for col in fundamental_cols] + technical_cols
    
    df['feature_date'] = pd.to_datetime(df['feature_date'])
    train_mask = df['feature_date'] < '2025-01-01'
    test_mask = df['feature_date'] >= '2025-01-01'
    
    X_train, y_train = df.loc[train_mask, feature_cols], df.loc[train_mask, 'target_alpha_class']
    X_test, y_test = df.loc[test_mask, feature_cols], df.loc[test_mask, 'target_alpha_class']
    
    print(f"📈 Training Samples: {len(X_train)} | Test Samples: {len(X_test)}")
    
    model = XGBClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=1.5,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    
    # --- Advanced Friction & Turnover Backtest ---
    test_df = df.loc[test_mask].copy()
    test_df['prob'] = probs
    
    # Top 20% Quantile Long Allocation Signal
    test_df['signal'] = test_df.groupby('feature_date')['prob'].transform(
        lambda x: (x >= x.quantile(0.80)).astype(int)
    )
    
    # Pivot matrix (Dates x Tickers) to calculate daily turnover
    weights_df = test_df.pivot(index='feature_date', columns='symbol', values='signal').fillna(0)
    # Normalize weights so sum of portfolio weights equals 1.0 (100% invested) on active days
    weights_df = weights_df.div(weights_df.sum(axis=1).replace(0, 1), axis=0)
    
    # Daily Portfolio Turnover: sum of absolute weight changes
    turnover_df = weights_df.diff().abs().sum(axis=1).fillna(0)
    
    # Daily Gross Returns
    returns_df = test_df.pivot(index='feature_date', columns='symbol', values='target_5d_return') / 5.0
    daily_gross_ret = (weights_df * returns_df).sum(axis=1)
    daily_market_ret = returns_df.mean(axis=1)
    
    # Execution Friction: 10 basis points (0.10% or 0.0010) per traded dollar
    COST_BPS = 0.0010 
    daily_friction_cost = turnover_df * COST_BPS
    daily_net_ret = daily_gross_ret - daily_friction_cost
    
    # Cumulative Performance
    cum_gross = (1 + daily_gross_ret).cumprod() - 1
    cum_net = (1 + daily_net_ret).cumprod() - 1
    cum_market = (1 + daily_market_ret).cumprod() - 1
    
    # Sharpe Calculations
    sharpe_gross = (daily_gross_ret.mean() / (daily_gross_ret.std() + 1e-6)) * np.sqrt(252)
    sharpe_net = (daily_net_ret.mean() / (daily_net_ret.std() + 1e-6)) * np.sqrt(252)
    
    print("\n================ Realistic Backtest Results (With Friction) ================")
    print(f"📊 Market Benchmark Total Return: {cum_market.iloc[-1]*100:.2f}%")
    print(f"📈 Top-Quantile GROSS Return: {cum_gross.iloc[-1]*100:.2f}% | Sharpe: {sharpe_gross:.2f}")
    print(f"💸 Top-Quantile NET Return (10bps fee): {cum_net.iloc[-1]*100:.2f}% | Sharpe: {sharpe_net:.2f}")
    print(f"🔄 Average Daily Portfolio Turnover: {turnover_df.mean()*100:.2f}%")
    print(f"📉 Cumulative Friction Drag: {(cum_gross.iloc[-1] - cum_net.iloc[-1])*100:.2f}%")

if __name__ == "__main__":
    train_and_evaluate()