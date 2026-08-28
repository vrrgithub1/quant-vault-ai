# filepath: orchestration/daily_flow.py

import os
import sys
import subprocess
from prefect import flow, task
from datetime import timedelta

# Ensure project root is in Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing script entry points
from ingestion.load_daily_prices import run_price_ingestion
from ingestion.load_financial_ratios import run_ratio_ingestion
from ingestion.load_company_embeddings import run_embeddings_ingestion
from train_xgboost import train_and_evaluate

@task(name="Ingest Daily Market Prices", retries=3, retry_delay_seconds=30)
def task_ingest_prices():
    """Fetches latest daily technicals and prices from FMP API."""
    print("🚀 Task 1: Ingesting Daily Prices...")
    run_price_ingestion()

@task(name="Ingest Financial Ratios", retries=3, retry_delay_seconds=30)
def task_ingest_ratios():
    """Fetches latest quarterly financial ratios from FMP API."""
    print("🚀 Task 2: Ingesting Financial Ratios...")
    run_ratio_ingestion()

@task(name="Execute dbt Data Vault Transformations")
def task_run_dbt():
    """Executes dbt models across staging, raw_vault, business_vault, and info_mart schemas."""
    print("🚀 Task 3: Running dbt Models...")
    dbt_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dbt_project")
    result = subprocess.run(["dbt", "run"], cwd=dbt_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"dbt run failed:\n{result.stderr}")
    print(result.stdout)

@task(name="Generate & Store Vector Text Embeddings")
def task_generate_embeddings():
    """Fetches company press releases and stores pgvector 384-dim embeddings."""
    print("🚀 Task 4: Generating Semantic Embeddings...")
    run_embeddings_ingestion()

@task(name="Run Quantitative XGBoost Inference & Backtest")
def task_run_ml_inference():
    """Scores alpha probabilities and evaluates friction-adjusted backtest."""
    print("🚀 Task 5: Running ML Alpha Inference...")
    train_and_evaluate()

@flow(name="Quant Vault AI: Daily Orchestration Pipeline")
def daily_quant_pipeline():
    """Main Orchestrated End-to-End Pipeline for Quant Vault AI."""
    print("⚡ Starting Daily Quant Vault AI Execution Flow...")
    
    # 1. Concurrent API Ingestion
    task_ingest_prices()
    task_ingest_ratios()
    
    # 2. Data Vault Modeling via dbt
    task_run_dbt()
    
    # 3. Vector Embeddings
    task_generate_embeddings()
    
    # 4. ML Model Inference & Allocation Signals
    task_run_ml_inference()
    
    print("✅ Daily Flow Execution Completed Successfully!")

if __name__ == "__main__":
    daily_quant_pipeline()