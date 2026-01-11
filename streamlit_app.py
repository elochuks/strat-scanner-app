import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()

    # S&P 500
    sp500_url = (
        "https://raw.githubusercontent.com/"
        "datasets/s-and-p-500-companies/master/data/constituents.csv"
    )
    sp500_df = pd.read_csv(sp500_url)
    tickers.update(sp500_df["Symbol"].dropna())

    # ETFs
    tickers.update([
        "SPY","QQQ","IWM","DIA",
        "XLF","XLK","XLE","XLV","XLY","XLP",
        "TLT","IEF","HYG",
        "GLD","SLV",
        "VXX","TQQQ","SQQQ"
    ])

    # Indexes (daily+ only)
    tickers.update(["^GSPC","^NDX","^DJI","^RUT","^VIX"])

    return sorted(tickers)

TICKERS = load_tickers()

# =====================================================
# STRAT LOGIC (CORRECT)
# =====================================================
def strat_type(prev, curr):
    ph, pl = prev["High"], prev["Low"]
    ch, cl = curr["High"], curr["Low"]

    if ch < ph and cl > pl:
        return "1 (Inside)"
    if ch > ph and cl < pl:
        return "3 (Outside)"
    if ch > ph and cl >= pl:
        return "2U"
    if cl < pl and ch <= ph:
        return "2D"
    return "Undefined"

# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers")

timeframe = st.selectbox(
    "Select Timeframe",
    ["Daily", "Weekly", "Monthly", "4-Hour"]
)

interval_map = {
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo",
    "4-Hour": "1h",  # handled via resample
}

available_patterns = ["1 (Inside)", "2U", "2D", "3 (Outside)"]

prev_patterns = st.multiselect(
    "Previous Candle",
    available_patterns,
    default=available_patterns
)

curr_patterns = st.multiselect(
    "Current Candle",
    available_patterns,
    default=available_patterns
)

scan = st.button("Run Scanner")

# =====================================================
# SCANNER
# =====================================================
if scan:
    results = []

    with st.spinner("Scanning market..."):
        for ticker in TICKERS:
            try:
                # Skip indexes on intraday
                if timeframe == "4-Hour" and ticker.startswith("^"):
                    continue

                data = yf.download(
                    ticker,
                    period="6mo",
                    interval=interval_map[timeframe],
                    progress=False
                )

                if data.empty or len(data) < 3:
                    continue

                # 4H resample
                if timeframe == "4-Hour":
                    data = (
                        data
                        .resample("4H")
                        .agg({
                            "Open":"first",
                            "High":"max",
                            "Low":"min",
                            "Close":"last",
                            "Volume":"sum"
                        })
                        .dropna()
                    )

                prev_prev, prev, curr = data.iloc[-3], data.iloc[-2], data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if prev_candle in prev_patterns and curr_candle in curr_patterns:
                    results.append({
                        "Ticker": ticker,
                        "Prev": prev_candle,
                        "Current": curr_candle,
                        "Close": round(curr["Close"], 2),
                        "Direction": "Up" if curr["Close"] > curr["Open"] else "Down"
                    })

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(df)} matches")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No matches found.")
