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
def candle_color(candle):
    return "Green" if candle["Close"].item() > candle["Open"].item() else "Red"

def strat_type(prev, curr):
    prev_h = prev["High"].item()
    prev_l = prev["Low"].item()
    curr_h = curr["High"].item()
    curr_l = curr["Low"].item()

    color = candle_color(curr)

    # Inside bar
    if curr_h < prev_h and curr_l > prev_l:
        return "1 (Inside)"

    # Outside bar
    if curr_h > prev_h and curr_l < prev_l:
        return "3 (Outside)"

    # Directional
    if curr_h > prev_h:
        return f"2U {color}"

    if curr_l < prev_l:
        return f"2D {color}"

    return "Undefined"

# -----------------------------
# UI
# -----------------------------
st.title("📊 STRAT Candle Scanner (S&P 500)")

# Timeframe selection
timeframe = st.selectbox(
    "Select Timeframe",
    ["2-Day", "Daily", "2-Week", "Weekly", "Monthly"]
)

interval_map = {
    "2-Day": "2d",
    "Daily": "1d",
    "2-Week": "2wk",
    "Weekly": "1wk",
    "Monthly": "1mo"
}

# STRAT pattern options
available_patterns = [
    "1 (Inside)",
    "2U Green", "2U Red",
    "2D Green", "2D Red",
    "3 (Outside)"
]

st.subheader("Select STRAT Candle Patterns")

prev_patterns = st.multiselect(
    "Previous Candle Patterns",
    options=available_patterns,
    default=available_patterns
)

curr_patterns = st.multiselect(
    "Current Candle Patterns",
    options=available_patterns,
    default=available_patterns
)

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

                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if ((not prev_patterns or prev_candle in prev_patterns) and
                    (not curr_patterns or curr_candle in curr_patterns)):
                    results.append({
                        "Ticker": ticker,
                        "Previous Candle": prev_candle,
                        "Current Candle": curr_candle,
                        "Candle Color": candle_color(curr),
                        "Close Price": round(curr["Close"].item(), 2)
                    })

            except Exception as e:
                st.write(f"Error downloading {ticker}: {e}")
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Scan complete — {len(df)} stocks found")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No stocks matched the selected STRAT patterns.")
