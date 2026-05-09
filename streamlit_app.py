import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="STRAT Scanner with Alerts", layout="wide")

# -----------------------------
# Ticker loader (S&P 500 + ETFs + Indexes)
# -----------------------------
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()
    try:
        sp500_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except:
        st.warning("Failed to load S&P 500 tickers")

    # Curated ETFs
    etfs = [
        "SPY","QQQ","DIA","IWM","XLF","XLK","XLE","XLY","XLP","XLV",
        "XLI","XLB","XLRE","XLU","XLC","TLT","IEF","HYG","LQD",
        "GLD","SLV","TQQQ","SQQQ"
    ]
    tickers.update(etfs)

    # Indexes
    indexes = ["^GSPC","^NDX","^DJI","^RUT","^VIX"]
    tickers.update(indexes)

    return sorted(tickers)

TICKERS = load_tickers()
st.caption(f"Loaded {len(TICKERS)} tickers")

# -----------------------------
# STRAT logic
# -----------------------------
def strat_candle(prev, curr):
    if curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3 (Outside)"
    elif curr["High"] <= prev["High"] and curr["Low"] >= prev["Low"]:
        return "1 (Inside)"
    elif curr["High"] > prev["High"]:
        return "2U"
    elif curr["Low"] < prev["Low"]:
        return "2D"
    return "Unknown"

# Bullish/Bearish mapping
BULLISH = ["2U","3 (Outside)"]
BEARISH = ["2D","1 (Inside)"]

# -----------------------------
# Timeframes
# -----------------------------
TIMEFRAMES = {
    "4H": ("60m","60d"),
    "Daily": ("1d","1y"),
    "2 Day": ("2d","2y"),
    "Weekly": ("1wk","5y"),
    "2 Week": ("2wk","10y"),
    "Monthly": ("1mo","15y"),
    "3 Month": ("3mo","20y")
}

STRAT_PATTERNS = ["1 (Inside)","2U","2D","3 (Outside)"]

# -----------------------------
# UI
# -----------------------------
st.title("📊 STRAT Scanner with Alerts")

col1, col2, col3 = st.columns(3)
with col1:
    timeframe = st.selectbox("Timeframe", TIMEFRAMES.keys())
with col2:
    prev_patterns = st.multiselect("Previous Candle STRAT", STRAT_PATTERNS, default=STRAT_PATTERNS)
with col3:
    curr_patterns = st.multiselect("Current Candle STRAT", STRAT_PATTERNS, default=STRAT_PATTERNS)

run_scan = st.button("Run Scanner")

# -----------------------------
# Scanner
# -----------------------------
if run_scan:
    interval, period = TIMEFRAMES[timeframe]
    results = []

    progress = st.progress(0)
    total = len(TICKERS)

    for i, ticker in enumerate(TICKERS):
        progress.progress((i+1)/total)
        try:
            df = yf.download(ticker, interval=interval, period=period, progress=False)
            if df.empty or len(df)<3: continue
            df = df.dropna()
            prev = df.iloc[-3]
            curr = df.iloc[-2]
            prev_strat = strat_candle(df.iloc[-4], prev)
            curr_strat = strat_candle(prev, curr)
            if prev_strat in prev_patterns and curr_strat in curr_patterns:
                # Determine alert type
                if curr_strat in BULLISH:
                    alert_type = "Bullish"
                elif curr_strat in BEARISH:
                    alert_type = "Bearish"
                else:
                    alert_type = "Neutral"

                results.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_strat,
                    "Current Candle": curr_strat,
                    "Timeframe": timeframe,
                    "Alert": alert_type
                })
        except:
            continue
    progress.empty()

    # -----------------------------
    # Display results with alerts
    # -----------------------------
    if results:
        df_results = pd.DataFrame(results)
        st.success(f"Found {len(df_results)} matching tickers")

        for _, row in df_results.iterrows():
            if row["Alert"]=="Bullish":
                st.success(f"{row['Ticker']} — {row['Current Candle']} ({row['Alert']})")
            elif row["Alert"]=="Bearish":
                st.error(f"{row['Ticker']} — {row['Current Candle']} ({row['Alert']})")
            else:
                st.info(f"{row['Ticker']} — {row['Current Candle']} ({row['Alert']})")

        st.dataframe(df_results, use_container_width=True)
    else:
        st.warning("No matches found.")
