import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# -----------------------
# STATIC S&P 500 LIST
# -----------------------
SP500 = [
    "AAPL","MSFT","AMZN","NVDA","META","GOOGL","GOOG","TSLA","BRK-B","JPM",
    "JNJ","V","XOM","PG","UNH","HD","MA","LLY","AVGO","MRK",
    "PEP","KO","COST","ABBV","ADBE","CRM","NFLX","WMT","ORCL","BAC"
    # 🔹 Expand to full S&P 500 if desired
]

# -----------------------
# DATA FETCH
# -----------------------
def get_data(symbol, timeframe):
    period_map = {
        "Daily": ("6mo", "1d"),
        "Weekly": ("2y", "1wk"),
        "Monthly": ("10y", "1mo")
    }
    period, interval = period_map[timeframe]

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False
    )

    return df.dropna()

# -----------------------
# STRAT CANDLE LOGIC
# -----------------------
def strat_type(prev, curr):
    if curr.High < prev.High and curr.Low > prev.Low:
        return "1"
    if curr.High > prev.High and curr.Low >= prev.Low:
        return "2U"
    if curr.Low < prev.Low and curr.High <= prev.High:
        return "2D"
    if curr.High > prev.High and curr.Low < prev.Low:
        return "3"
    return None

# -----------------------
# UI
# -----------------------
st.title("📊 STRAT S&P 500 Scanner")

timeframe = st.selectbox(
    "Timeframe",
    ["Daily", "Weekly", "Monthly"]
)

current_patterns = st.multiselect(
    "Current Candle Pattern",
    ["1", "2U", "2D", "3"],
    default=["2U", "2D"]
)

previous_patterns = st.multiselect(
    "Previous Candle Pattern (Optional)",
    ["1", "2U", "2D", "3"],
    default=[]
)

run_scan = st.button("🚀 Run Scanner")

# -----------------------
# SCANNER
# -----------------------
if run_scan:
    results = []

    with st.spinner("Scanning S&P 500 stocks..."):
        for symbol in SP500:
            try:
                df = get_data(symbol, timeframe)

                # Ensure enough candles
                if len(df) < 4:
                    continue

                # USE LAST COMPLETED CANDLE
                prev2 = df.iloc[-4]
                prev1 = df.iloc[-3]   # previous candle
                curr = df.iloc[-2]    # current completed candle

                prev_pattern = strat_type(prev2, prev1)
                curr_pattern = strat_type(prev1, curr)

                if curr_pattern not in current_patterns:
                    continue

                if previous_patterns and prev_pattern not in previous_patterns:
                    continue

                results.append({
                    "Symbol": symbol,
                    "Previous Candle": prev_pattern,
                    "Current Candle": curr_pattern,
                    "Close": round(curr.Close, 2),
                    "High": round(curr.High, 2),
                    "Low": round(curr.Low, 2)
                })

            except Exception:
                continue

    if results:
        st.success(f"Found {len(results)} matches")
        st.dataframe(
            pd.DataFrame(results),
            use_container_width=True
        )
    else:
        st.warning("No matches found")

st.caption("STRAT methodology | Data: Yahoo Finance")
