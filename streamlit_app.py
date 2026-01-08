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
    # Add full list if needed
]

# -----------------------------
# STRAT CANDLE LOGIC
# -----------------------------
def strat_type(prev, curr):
    # Make sure values are scalars
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

# 1️⃣ Select timeframe
timeframe = st.selectbox("Select Timeframe", ["Daily", "Weekly", "Monthly"])

interval_map = {
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo"
}

# 2️⃣ Select STRAT pattern(s)
available_patterns = ["1 (Inside)", "2U", "2D", "3 (Outside)"]
selected_patterns = st.multiselect(
    "Select STRAT Candle Pattern(s) to Scan",
    options=available_patterns,
    default=available_patterns  # default all patterns
)

# 3️⃣ Run button
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

                if data.shape[0] < 3:
                    continue

                # Last 3 candles
                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                # Only append if current candle matches selected patterns
                if curr_candle in selected_patterns:
                    results.append({
                        "Ticker": ticker,
                        "Previous Candle": prev_candle,
                        "Current Candle": curr_candle,
                        "Direction": "Up" if curr["Close"].item() > curr["Open"].item() else "Down",
                        "Close Price": round(curr["Close"].item(), 2)
                    })

            except Exception as e:
                st.write(f"Error downloading {ticker}: {e}")
                continue

    # Display results
    if results:
        df = pd.DataFrame(results)
        st.success(f"Scan complete — {len(df)} stocks found matching selected STRAT pattern(s)")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No stocks found matching the selected STRAT pattern(s).")
