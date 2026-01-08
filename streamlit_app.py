import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# --------------------------------------------------
# LOAD SYMBOLS (S&P 500 + Indices + ETFs)
# --------------------------------------------------
@st.cache_data
def load_symbols():
    # S&P 500 CSV source
    sp500_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents_symbols.txt"
    sp500 = pd.read_csv(sp500_url, header=None)[0].tolist()

    # Yahoo Finance uses '-' instead of '.'
    sp500 = [s.replace(".", "-") for s in sp500]

    # Major Indices
    indices = [
        "^GSPC",   # S&P 500
        "^NDX",    # Nasdaq 100
        "^DJI",    # Dow Jones
        "^RUT",    # Russell 2000
        "^VIX"     # Volatility Index
    ]

    # Popular ETFs
    etfs = [
        "SPY", "QQQ", "IWM", "DIA",
        "XLK", "XLF", "XLE", "XLV",
        "XLY", "XLP", "SMH", "ARKK"
    ]

    return sorted(list(set(sp500 + indices + etfs)))

SYMBOLS = load_symbols()

# --------------------------------------------------
# STRAT LOGIC
# --------------------------------------------------
def strat_type(prev, curr):
    prev_h = float(prev["High"])
    prev_l = float(prev["Low"])
    curr_h = float(curr["High"])
    curr_l = float(curr["Low"])

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

# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("📊 STRAT Multi-Timeframe Scanner")

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

available_patterns = ["1 (Inside)", "2U", "2D", "3 (Outside)"]

st.subheader("STRAT Pattern Filters")

prev_patterns = st.multiselect(
    "Previous Candle Pattern(s)",
    available_patterns,
    default=available_patterns
)

curr_patterns = st.multiselect(
    "Current Candle Pattern(s)",
    available_patterns,
    default=available_patterns
)

scan_button = st.button("Run Scanner")

# --------------------------------------------------
# SCANNER
# --------------------------------------------------
if scan_button:
    results = []

    with st.spinner("Scanning symbols..."):
        for symbol in SYMBOLS:
            try:
                data = yf.download(
                    symbol,
                    period="12mo",
                    interval=interval_map[timeframe],
                    progress=False
                )

                if data is None or len(data) < 3:
                    continue

                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if ((not prev_patterns or prev_candle in prev_patterns) and
                    (not curr_patterns or curr_candle in curr_patterns)):

                    results.append({
                        "Symbol": symbol,
                        "Previous Candle": prev_candle,
                        "Current Candle": curr_candle,
                        "Direction": "Up" if curr["Close"] > curr["Open"] else "Down",
                        "Close": round(float(curr["Close"]), 2)
                    })

            except Exception:
                continue

    # --------------------------------------------------
    # RESULTS
    # --------------------------------------------------
    if results:
        df = pd.DataFrame(results).sort_values("Symbol")
        st.success(f"Found {len(df)} matches")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No matches found for selected criteria.")
