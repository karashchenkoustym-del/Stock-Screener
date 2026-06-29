import streamlit as st
import duckdb
import plotly.graph_objects as go
import os
import yfinance as yf
import pandas as pd

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"]

def bootstrap_db():
    os.makedirs("data", exist_ok=True)
    con = duckdb.connect(DB_PATH)
    all_data = []
    for ticker in TICKERS:
        df = yf.download(ticker, period="6mo", auto_adjust=True, progress=False)
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        df["ticker"] = ticker
        df.reset_index(inplace=True)
        df.rename(columns={"date": "date"}, inplace=True)
        all_data.append(df)
    combined = pd.concat(all_data, ignore_index=True)
    con.execute("DROP TABLE IF EXISTS ohlcv")
    con.execute("CREATE TABLE ohlcv AS SELECT * FROM combined")
    con.execute(open("scripts/indicators.sql").read())
    con.close()

if not os.path.exists(DB_PATH):
    with st.spinner("Fetching stock data for the first time..."):
        bootstrap_db()

DB_PATH = "data/stocks.db"

st.set_page_config(page_title="Stock Screener", layout="wide")
st.title("📈 Stock Screener")

con = duckdb.connect(DB_PATH, read_only=True)

# --- Sidebar filters ---
st.sidebar.header("Filters")
signal_filter = st.sidebar.multiselect(
    "Signal", ["Bullish", "Bearish", "Neutral"], default=["Bullish", "Bearish", "Neutral"]
)
rsi_min, rsi_max = st.sidebar.slider("RSI Range", 0, 100, (0, 100))
vol_min = st.sidebar.slider("Min Volume Ratio", 0.0, 5.0, 0.0)

# --- Latest snapshot ---
df = con.execute("""
    SELECT * FROM indicators
    WHERE date = (SELECT MAX(date) FROM indicators)
    ORDER BY ticker
""").fetchdf()

filtered = df[
    df["signal"].isin(signal_filter) &
    df["rsi"].between(rsi_min, rsi_max) &
    (df["volume_ratio"] >= vol_min)
]

st.subheader(f"Latest Snapshot — {df['date'].max().date()}")
st.dataframe(filtered, use_container_width=True)

# --- Price chart for selected ticker ---
st.subheader("Price & Moving Averages")
ticker = st.selectbox("Select ticker", sorted(df["ticker"].unique()))

history = con.execute("""
    SELECT date, price, ma_20, ma_50, rsi, volume_ratio
    FROM indicators
    WHERE ticker = ?
    ORDER BY date
""", [ticker]).fetchdf()

fig = go.Figure()
fig.add_trace(go.Scatter(x=history["date"], y=history["price"], name="Price", line=dict(color="white")))
fig.add_trace(go.Scatter(x=history["date"], y=history["ma_20"], name="MA 20", line=dict(color="orange", dash="dash")))
fig.add_trace(go.Scatter(x=history["date"], y=history["ma_50"], name="MA 50", line=dict(color="cyan", dash="dash")))
fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)

# --- RSI chart ---
st.subheader("RSI (14-day)")
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=history["date"], y=history["rsi"], name="RSI", line=dict(color="violet")))
fig2.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
fig2.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
fig2.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig2, use_container_width=True)

con.close()