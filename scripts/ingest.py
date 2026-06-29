import yfinance as yf
import duckdb
import pandas as pd

# --- Config ---
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"]
PERIOD = "6mo"   # 6 months of daily data
DB_PATH = "data/stocks.db"

# --- Fetch data ---
def fetch_data(tickers, period):
    print(f"Fetching data for {len(tickers)} tickers...")
    all_data = []
    for ticker in tickers:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        # Flatten multi-level columns
        df.columns = [col[0].lower().replace(" ", "_") if isinstance(col, tuple) else col.lower() for col in df.columns]
        df["ticker"] = ticker
        df.reset_index(inplace=True)
        df.rename(columns={"Date": "date"}, inplace=True)
        all_data.append(df)
    return pd.concat(all_data, ignore_index=True)

# --- Load into DuckDB ---
def load_to_db(df, db_path):
    con = duckdb.connect(db_path)
    con.execute("DROP TABLE IF EXISTS ohlcv")
    con.execute("""
        CREATE TABLE ohlcv AS
        SELECT * FROM df
    """)
    count = con.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0]
    print(f"Loaded {count} rows into {db_path}")
    con.close()

if __name__ == "__main__":
    df = fetch_data(TICKERS, PERIOD)
    load_to_db(df, DB_PATH)
    print("Done!")