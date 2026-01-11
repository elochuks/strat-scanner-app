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

    sp500_url = (
        "https://raw.githubusercontent.com/"
        "datasets/s-and-p-500-companies/master/data/constituents.csv"
    )
    sp500_df = pd.read_csv(sp500_url)
    tickers.update(sp500_df["Symbol"].dropna())

    tickers.update([
        "SPY","QQQ","IWM","DIA",
        "XLF","XLK","XLE","XLV","XLY","XLP",
        "TLT","IEF","HYG",
        "GLD","SLV",
        "VXX","TQQQ","SQQQ"
    ])

    tickers.update(["^GSPC","^NDX","^DJI","^RUT","^VIX"])

    return sorted(tickers)

TICKERS = load_tickers()

# =====================================================
# STRAT CANDLE LOGIC (CORRECT)
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
    "Timeframe",
    ["Daily", "Weekly", "Monthly", "4-Hour"]
)

interval_map = {
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo",
    "4-Hour": "1h",
}

available_patterns = ["1 (Inside)", "2U", "2D", "3 (Outside)", "Undefined"]

prev_patterns = st.multiselect(
    "Previous Candle Pattern",
    available_patterns,
    default=available_patterns
)

curr_patterns = st.multiselect(
    "Current Candle Pattern",
    available_patterns,
    default=available_patterns
)

LOOKBACK = st.slider(
    "Lookback Candles (closed)",
    min_value=3,
    max_value=20,
    value=10
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
                if timeframe == "4-Hour" and ticker.startswith("^"):
                    continue

                data = yf.download(
                    ticker,
                    period="9mo",
                    interval=interval_map[timeframe],
                    progress=False
                )

                if data.empty or len(data) < LOOKBACK + 2:
                    continue

                if timeframe == "4-Hour":
                    data = (
                        data.resample("4H")
                        .agg({
                            "Open":"first",
                            "High":"max",
                            "Low":"min",
                            "Close":"last",
                            "Volume":"sum"
                        })
                        .dropna()
                    )

                for i in range(-LOOKBACK, -1):
                    prev_prev = data.iloc[i - 1]
                    prev = data.iloc[i]
                    curr = data.iloc[i + 1]

                    prev_candle = strat_type(prev_prev, prev)
                    curr_candle = strat_type(prev, curr)

                    if (
                        prev_candle in prev_patterns
                        and curr_candle in curr_patterns
                    ):
                        results.append({
                            "Ticker": ticker,
                            "Prev Candle": prev_candle,
                            "Current Candle": curr_candle,
                            "Direction": "Up" if curr["Close"] > curr["Open"] else "Down",
                            "Close": round(curr["Close"], 2)
                        })
                        break

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(df)} matches")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No matches found — increase lookback or widen filters.")
