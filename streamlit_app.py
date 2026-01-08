import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# -----------------------------
# S&P 500 LIST (sample)
# -----------------------------
SP500 = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","TSLA","BRK-B","JPM","JNJ",
    "V","PG","UNH","HD","MA","XOM","LLY","AVGO","PEP","COST",
]

# -----------------------------
# STRAT CANDLE LOGIC
# -----------------------------
def strat_type(prev, curr):
    # Ensure all values are scalar
    prev_h = prev["High"].item() if hasattr(prev["High"], "item") else prev["High"]
    prev_l = prev["Low"].item() if hasattr(prev["Low"], "item") else prev["Low"]
    curr_h = curr["High"].item() if hasattr(curr["High"], "item") else curr["High"]
    curr_l = curr["Low"].item() if hasattr(curr["Low"], "item") else curr["Low"]

    if curr_h < prev_h and curr_l > prev_l:
        return "1 (Inside)"
    elif curr_h > prev_h and curr_l < prev_l:
        return "3 (Outside)"
    elif curr_h > prev_h:
        return "2U"
    elif curr_l < prev_l:
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

                # Must have at least 3 rows to compute previous/current candles
                if data.shape[0] < 3:
                    continue

                # Use last 3 rows
                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                results.append({
                    "Ticker": ticker,
                    "Previous Candle": strat_type(prev_prev, prev),
                    "Current Candle": strat_type(prev, curr),
                    "Direction": "Up" if curr["Close"].item() > curr["Open"].item() else "Down",
                    "Close Price": round(curr["Close"].item(), 2)
                })

            except Exception as e:
                st.write(f"Error downloading {ticker}: {e}")
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Scan complete — {len(df)} stocks found")
        st.dataframe(df, use_container_width=True)

        if "Current Candle" in df.columns:
            st.subheader("🔍 Filter Results")
            candle_filter = st.multiselect(
                "Filter by Current Candle",
                options=df["Current Candle"].unique()
            )
            if candle_filter:
                st.dataframe(
                    df[df["Current Candle"].isin(candle_filter)],
                    use_container_width=True
                )
    else:
        st.warning("No stock data available for the selected timeframe.")
