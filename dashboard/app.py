# filepath: dashboard/app.py

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Quant Vault AI Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.sidebar.title("⚡ Quant Vault AI")
st.sidebar.markdown("**FastAPI REST Driven Dashboard**")
menu = st.sidebar.radio("Navigation", ["🔍 Semantic Vector Search", "📡 Production Signals", "📊 Portfolio Backtest"])

# -----------------------------------------------------------------------------
# PAGE 1: SEMANTIC VECTOR SEARCH (VIA FASTAPI)
# -----------------------------------------------------------------------------
if menu == "🔍 Semantic Vector Search":
    st.header("🔍 REST-Driven Semantic Vector Search")
    st.caption("Fetches vector similarity search results via FastAPI (`/api/v1/search`).")

    query_text = st.text_input("Enter Semantic Search Query:", value="AI cloud infrastructure growth and generative intelligence")
    top_k = st.slider("Top Results Count", min_value=1, max_value=10, value=3)

    if st.button("Query API", type="primary"):
        with st.spinner("Requesting FastAPI REST endpoint..."):
            try:
                response = requests.get(
                    f"{API_BASE_URL}/search", 
                    params={"query": query_text, "top_k": top_k}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    st.success(f"Successfully retrieved {len(results)} matches from API!")
                    
                    for idx, item in enumerate(results):
                        with st.expander(f"📌 #{idx+1} | Stock: {item['symbol']} (Similarity: {item['cosine_similarity']:.4f})", expanded=True):
                            st.write(f"**Press Release Summary:** {item['summary_text']}")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("P/E Ratio", f"{item['pe_ratio']:.2f}" if item['pe_ratio'] else "N/A")
                            c2.metric("Return on Equity", f"{item['return_on_equity']:.2%}" if item['return_on_equity'] else "N/A")
                            c3.metric("RSI (14-day)", f"{item['rsi_14']:.2f}" if item['rsi_14'] else "N/A")
                else:
                    st.error(f"API Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Failed to connect to FastAPI server at {API_BASE_URL}: {e}")

# -----------------------------------------------------------------------------
# PAGE 2: LATEST SIGNALS (VIA FASTAPI)
# -----------------------------------------------------------------------------
elif menu == "📡 Production Signals":
    st.header("📡 Live Model Alpha Signals")
    st.caption("Fetches real-time stock allocation signals via FastAPI (`/api/v1/signals/latest`).")

    if st.button("Fetch Latest Signals", type="primary"):
        try:
            response = requests.get(f"{API_BASE_URL}/signals/latest")
            if response.status_code == 200:
                signals = response.json()
                df_sig = pd.DataFrame(signals)
                
                st.dataframe(df_sig, use_container_width=True)
                
                fig = px.bar(
                    df_sig, x="symbol", y="predicted_alpha_prob", color="action",
                    title="Model Predicted Alpha Probability by Ticker",
                    labels={"predicted_alpha_prob": "Alpha Probability"}
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error fetching signals from API: {e}")

# -----------------------------------------------------------------------------
# PAGE 3: BACKTEST RESULTS SUMMARY
# -----------------------------------------------------------------------------
elif menu == "📊 Portfolio Backtest":
    st.header("📊 Out-of-Sample Performance Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gross Return", "97.05%", "Gross Sharpe: 4.76")
    col2.metric("Net Return (10bps Fee)", "72.16%", "Net Sharpe: 3.82")
    col3.metric("Benchmark Return", "49.24%", "Equal-Weighted")
    col4.metric("Daily Turnover", "33.22%", "Friction Drag: 24.88%")