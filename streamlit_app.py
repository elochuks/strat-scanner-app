import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# -----------------------------
# LOAD S&P 500 FROM CSV
# -----------------------------
@st.cache_data
def load_sp500():
    url = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
    df = pd.read_csv(url)

    # Convert tickers for yfinance compatibility
    tickers = (
        df["Symbol"]
        .str.replace(".", "-", regex=False)  # BRK.B -> BRK-B
        .unique()
        .tolist()
    )
    return tickers

SP500 = load_sp500()

# -----------------------------
# STRAT CANDLE LOGIC
# -----------------------------
def strat_type(prev, curr):
    prev_h = prev["High"].item()
    prev_l = prev["Low"].item()
    curr_h = curr["High"].item()
    curr_l = curr["Low"].item()

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
st.title("📊 STRAT Candle Scanner — S&P 500")

# Timeframe selection
timeframe = st.selectbox(
    "Select Timeframe",
    ["4-Hour", "2-Day", "Daily", "2-Week", "Weekly", "Monthly", "3-Month"]
)

interval_map = {
    "4-Hour": "4h",
    "2-Day": "2d",
    "Daily": "1d",
    "2-Week": "2wk",
    "Weekly": "1wk",
    "Monthly": "1mo",
    "3-Month": "3mo"
}

# STRAT pattern options
available_patterns = ["1 (Inside)", "2U", "2D", "3 (Outside)"]

st.subheader("STRAT Pattern Filters")

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
                    period="12mo",
                    interval=interval_map[timeframe],
                    progress=False,
                    auto_adjust=False
                )

                if data.empty or len(data) < 3:
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
                        "Direction": "Up" if curr["Close"].item() > curr["Open"].item() else "Down",
                        "Close": round(curr["Close"].item(), 2)
                    })

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(df)} stocks matching criteria")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No stocks matched the selected STRAT criteria.")
