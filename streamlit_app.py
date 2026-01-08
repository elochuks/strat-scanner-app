import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# -----------------------------
# S&P 500 LIST (static)
# -----------------------------
SP500 = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","TSLA","BRK-B","JPM","JNJ",
    "V","PG","UNH","HD","MA","XOM","LLY","AVGO","PEP","COST",
    # You can expand or replace with full list
]

# -----------------------------
# STRAT LOGIC
# -----------------------------
def strat_type(prev, curr):
    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
        return "1 (Inside)"
    elif curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3 (Outside)"
    elif curr["High"] > prev["High"]:
        return "2U"
    elif curr["Low"] < prev["Low"]:
        return "2D"
    else:
        return "Undefined"

# -----------------------------
# UI
# -----------------------------
st.title("📊 STRAT Candle Scanner (S&P 500)")

timeframe = st.selectbox(
    "Select Timeframe",
    ["Daily", "Weekly", "Monthly"]
)

interval_map = {
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo"
}

scan_button = st.button("Run Scanner")

# -----------------------------
# SCANNER
# -----------------------------
if scan_button:
    results = []

    with st.spinner("Scanning S&P 500 stocks..."):
        for ticker in SP500:
            try:
                data = yf.download(
                    ticker,
                    period="6mo",
                    interval=interval_map[timeframe],
                    progress=False
                )

                if len(data) < 3:
                    continue

                prev = data.iloc[-3]
                curr = data.iloc[-2]

                results.append({
                    "Ticker": ticker,
                    "Previous Candle": strat_type(data.iloc[-4], prev),
                    "Current Candle": strat_type(prev, curr),
                    "Direction": "Up" if curr["Close"] > curr["Open"] else "Down",
                    "Close Price": round(curr["Close"], 2)
                })

            except Exception:
                continue

    df = pd.DataFrame(results)
    st.success(f"Scan complete — {len(df)} stocks found")
    st.dataframe(df, use_container_width=True)

    # Optional filters
    st.subheader("🔍 Filter Results")
    candle_filter = st.multiselect(
        "Filter by Current Candle",
        df["Current Candle"].unique()
    )

    if candle_filter:
        st.dataframe(
            df[df["Current Candle"].isin(candle_filter)],
            use_container_width=True
        )
