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

    try:
        sp500_url = (
            "https://raw.githubusercontent.com/"
            "datasets/s-and-p-500-companies/master/data/constituents.csv"
        )
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")

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

    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)

    return sorted(tickers)


TICKERS = load_tickers()

# =====================================================
# STRAT CANDLE LOGIC
# =====================================================
def strat_type(prev, curr):
    candle_color = "Green" if curr["Close"] > curr["Open"] else "Red"

    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
        return "1 (Inside)"
    elif curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3 (Outside)"
    elif curr["High"] > prev["High"]:
        return f"2U {candle_color}"
    elif curr["Low"] < prev["Low"]:
        return f"2D {candle_color}"
    else:
        return "Undefined"


# =====================================================
# FTFC CONTINUITY LOGIC
# =====================================================
def candle_color(df):
    if df.empty or len(df) < 1:
        return None
    last = df.iloc[-1]
    return "Green" if last["Close"] > last["Open"] else "Red"


def ftfc_status(ticker):
    try:
        weekly = yf.download(ticker, period="1y", interval="1wk", progress=False)
        monthly = yf.download(ticker, period="2y", interval="1mo", progress=False)

        wk_color = candle_color(weekly)
        mo_color = candle_color(monthly)

        if wk_color == "Green" and mo_color == "Green":
            return "Bullish FTFC"
        elif wk_color == "Red" and mo_color == "Red":
            return "Bearish FTFC"
        else:
            return "Mixed"
    except Exception:
        return "Mixed"


# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers")

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
                )

                if data.empty or len(data) < 3:
                    continue

                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if (
                    prev_candle in prev_patterns
                    and curr_candle in curr_patterns
                ):
                    results.append({
                        "Ticker": ticker,
                        "Previous Candle": prev_candle,
                        "Current Candle": curr_candle,
                        "FTFC": ftfc_status(ticker),
                        "Direction": "Up" if curr["Close"] > curr["Open"] else "Down",
                        "Close Price": round(float(curr["Close"]), 2),
                    })

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(df)} matching tickers")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No tickers matched the selected STRAT criteria.")
