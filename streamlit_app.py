import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS (HARDENED & CLOUD-SAFE)
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()

    # -----------------------------
    # S&P 500 (stable & live)
    # -----------------------------
    try:
        sp500_url = (
            "https://raw.githubusercontent.com/"
            "datasets/s-and-p-500-companies/master/data/constituents.csv"
        )
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")

    # -----------------------------
    # ETFs (curated, stable list)
    # -----------------------------
    etfs = [
        "SPY", "IVV", "VOO", "QQQ", "DIA", "IWM",
        "XLF", "XLK", "XLE", "XLY", "XLP", "XLV",
        "XLI", "XLB", "XLRE", "XLU", "XLC",
        "VUG", "VTV", "IWF", "IWD",
        "TLT", "IEF", "SHY", "LQD", "HYG",
        "GLD", "SLV", "USO", "UNG",
        "VXX", "SQQQ", "TQQQ"
    ]
    tickers.update(etfs)

    # -----------------------------
    # Indexes (Yahoo symbols)
    # -----------------------------
    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)

    tickers = sorted(tickers)
    if not tickers:
        raise RuntimeError("No tickers loaded")

    return tickers

TICKERS = load_tickers()

# =====================================================
# STRAT CANDLE LOGIC WITH COLOR
# =====================================================
def strat_type(prev, curr):
    prev_h = float(prev["High"])
    prev_l = float(prev["Low"])
    curr_h = float(curr["High"])
    curr_l = float(curr["Low"])
    curr_o = float(curr["Open"])
    curr_c = float(curr["Close"])

    candle_color = "Green" if curr_c > curr_o else "Red"

    if curr_h < prev_h and curr_l > prev_l:
        return "1 (Inside)"
    elif curr_h > prev_h and curr_l < prev_l:
        return "3 (Outside)"
    elif curr_h > prev_h:
        return f"2U {candle_color}"
    elif curr_l < prev_l:
        return f"2D {candle_color}"
    else:
        return "Undefined"

# =====================================================
# DETERMINE FTFC (BULLISH / BEARISH / NEUTRAL)
# =====================================================
def get_ftfc(ticker):
    # Define multiple timeframes to check for FTFC
    tf_map = {
        "Monthly": "1mo",
        "Weekly": "1wk",
        "Daily": "1d",
        "4-Hour": "4h"
    }
    colors = []

    for name, interval in tf_map.items():
        try:
            data = yf.download(ticker, period="6mo", interval=interval, progress=False, auto_adjust=False)
            if data.empty:
                continue
            last_candle = data.iloc[-1]
            color = "Green" if last_candle["Close"] > last_candle["Open"] else "Red"
            colors.append(color)
        except Exception:
            continue

    if not colors:
        return "Neutral"

    if all(c == "Green" for c in colors):
        return "Bullish FTFC"
    elif all(c == "Red" for c in colors):
        return "Bearish FTFC"
    else:
        return "Neutral FTFC"

# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers (S&P 500 + ETFs + Indexes)")

timeframe = st.selectbox(
    "Select Timeframe",
    ["4-Hour", "2-Day", "Daily", "2-Week", "Weekly", "Monthly", "3-Month"],
)

interval_map = {
    "4-Hour": "4h",
    "2-Day": "2d",
    "Daily": "1d",
    "2-Week": "2wk",
    "Weekly": "1wk",
    "Monthly": "1mo",
    "3-Month": "3mo",
}

available_patterns = [
    "1 (Inside)", "3 (Outside)",
    "2U Red", "2U Green",
    "2D Red", "2D Green"
]

st.subheader("STRAT Pattern Filters")

prev_patterns = st.multiselect(
    "Previous Candle Patterns",
    options=available_patterns,
    default=available_patterns,
)

curr_patterns = st.multiselect(
    "Current Candle Patterns",
    options=available_patterns,
    default=available_patterns,
)

history_length = st.number_input(
    "Number of past candles to show", min_value=1, max_value=10, value=5
)

scan_button = st.button("Run Scanner")

# =====================================================
# SCANNER
# =====================================================
if scan_button:
    results = []

    with st.spinner("Scanning market..."):
        for ticker in TICKERS:
            try:
                data = yf.download(
                    ticker,
                    period="9mo",
                    interval=interval_map[timeframe],
                    progress=False,
                    auto_adjust=False,
                )

                if data.empty or len(data) < history_length + 1:
                    continue

                strat_history = []
                for i in range(-history_length - 1, 0):
                    prev = data.iloc[i - 1]
                    curr = data.iloc[i]
                    strat_history.append(strat_type(prev, curr))

                prev_candle = strat_history[-2]
                curr_candle = strat_history[-1]

                if (
                    (not prev_patterns or prev_candle in prev_patterns)
                    and (not curr_patterns or curr_candle in curr_patterns)
                ):
                    ftfc_status = get_ftfc(ticker)  # Get FTFC across multiple timeframes

                    results.append(
                        {
                            "Ticker": ticker,
                            "Previous Candle": prev_candle,
                            "Current Candle": curr_candle,
                            "Direction": "Up" if float(data.iloc[-1]["Close"]) > float(data.iloc[-1]["Open"]) else "Down",
                            "Close Price": round(float(data.iloc[-1]["Close"]), 2),
                            "Candle History": " → ".join(strat_history),
                            "FTFC": ftfc_status
                        }
                    )

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(df)} matching tickers")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No tickers matched the selected STRAT criteria.")
