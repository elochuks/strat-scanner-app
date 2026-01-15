import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS (HARDENED & CLOUD-SAFE)
# LOAD TICKERS
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
    except Exception:
        pass

    # -----------------------------
    # ETFs (curated, stable list)
    # -----------------------------
    etfs = [
        # Index ETFs
        "SPY", "IVV", "VOO", "QQQ", "DIA", "IWM",

        # Sector ETFs
        "XLF", "XLK", "XLE", "XLY", "XLP", "XLV",
        "XLI", "XLB", "XLRE", "XLU", "XLC",

        # Growth / Value
        "VUG", "VTV", "IWF", "IWD",

        # Bonds
        "TLT", "IEF", "SHY", "LQD", "HYG",

        # Commodities
        "GLD", "SLV", "USO", "UNG",

        # Volatility / Inverse
        "VXX", "SQQQ", "TQQQ"
        "SPY","IVV","VOO","QQQ","DIA","IWM",
        "XLF","XLK","XLE","XLY","XLP","XLV",
        "XLI","XLB","XLRE","XLU","XLC",
        "VUG","VTV","IWF","IWD",
        "TLT","IEF","SHY","LQD","HYG",
        "GLD","SLV","USO","UNG",
        "VXX","SQQQ","TQQQ"
    ]
    tickers.update(etfs)

    # -----------------------------
    # Indexes (Yahoo symbols)
    # -----------------------------
    indexes = [
        "^GSPC",  # S&P 500
        "^NDX",   # Nasdaq 100
        "^DJI",   # Dow Jones
        "^RUT",   # Russell 2000
        "^VIX",   # Volatility Index
    ]
    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)

    # -----------------------------
    # Final cleanup
    # -----------------------------
    tickers = sorted(tickers)

    if not tickers:
        raise RuntimeError("No tickers loaded")

    return tickers
    return sorted(tickers)


TICKERS = load_tickers()

# =====================================================
# STRAT CANDLE LOGIC WITH COLOR
# STRAT CANDLE LOGIC
# =====================================================
def strat_type(prev, curr):
    prev_h = float(prev["High"])
    prev_l = float(prev["Low"])
    curr_h = float(curr["High"])
    curr_l = float(curr["Low"])
    curr_o = float(curr["Open"])
    curr_c = float(curr["Close"])

    # Determine candle color
    candle_color = "Green" if curr_c > curr_o else "Red"

    # STRAT logic
    if curr_h < prev_h and curr_l > prev_l:
    candle_color = "Green" if curr["Close"] > curr["Open"] else "Red"

    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
        return "1 (Inside)"
    elif curr_h > prev_h and curr_l < prev_l:
    if curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3 (Outside)"
    elif curr_h > prev_h:
        return f"2U {candle_color}"  # 2U Red / 2U Green
    elif curr_l < prev_l:
        return f"2D {candle_color}"  # 2D Red / 2D Green
    else:
        return "Undefined"
    if curr["High"] > prev["High"]:
        return f"2U {candle_color}"
    if curr["Low"] < prev["Low"]:
        return f"2D {candle_color}"
    return "Undefined"


# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers (S&P 500 + ETFs + Indexes)")
st.caption(f"Scanning **{len(TICKERS)}** tickers")

# Timeframes
timeframe = st.selectbox(
    "Select Timeframe",
    ["4-Hour", "2-Day", "Daily", "2-Week", "Weekly", "Monthly", "3-Month"],
    ["4-Hour", "2-Day", "Daily", "2-Week", "Weekly", "Monthly", "3-Month"]
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

# STRAT patterns with color options
available_patterns = [
    "1 (Inside)", "3 (Outside)",
    "2U Red", "2U Green",
    "2D Red", "2D Green"
]
patterns = ["1 (Inside)", "3 (Outside)", "2U Red", "2U Green", "2D Red", "2D Green"]

st.subheader("STRAT Pattern Filters")

prev_patterns = st.multiselect(
    "Previous Candle Patterns",
    options=available_patterns,
    default=available_patterns,
    "Previous Candle Patterns", patterns, patterns
)

curr_patterns = st.multiselect(
    "Current Candle Patterns",
    options=available_patterns,
    default=available_patterns,
    "Current Candle Patterns", patterns, patterns
)

st.subheader("FTFC Filters")

ftfc_alignment_only = st.checkbox(
    "Show only M + W aligned (FTFC)",
    value=False,
    help="Only show tickers where Monthly and Weekly continuity agree"
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
                # Download main interval data
                # -----------------------
                # STRAT TIMEFRAME DATA
                # -----------------------
                data = yf.download(
                    ticker,
                    period="9mo",
                    interval=interval_map[timeframe],
                    progress=False,
                    auto_adjust=False,
                )

                if data.empty or len(data) < 3:
                    continue

                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if (
                    (not prev_patterns or prev_candle in prev_patterns)
                    and (not curr_patterns or curr_candle in curr_patterns)
                ):

                    # -----------------------
                    # Calculate FTFC (Timeframe Continuity)
                    # -----------------------
                    ftfc_result = []

                    # Monthly data
                    monthly_data = yf.download(
                        ticker, period="12mo", interval="1mo", progress=False, auto_adjust=False
                    )
                    if not monthly_data.empty:
                        current_month_open = monthly_data.iloc[-1]["Open"]
                        if float(curr["Close"]) > float(current_month_open):
                            ftfc_result.append("M: Bullish")
                        elif float(curr["Close"]) < float(current_month_open):
                            ftfc_result.append("M: Bearish")

                    # Weekly data
                    weekly_data = yf.download(
                        ticker, period="12mo", interval="1wk", progress=False, auto_adjust=False
                    )
                    if not weekly_data.empty:
                        current_week_open = weekly_data.iloc[-1]["Open"]
                        if float(curr["Close"]) > float(current_week_open):
                            ftfc_result.append("W: Bullish")
                        elif float(curr["Close"]) < float(current_week_open):
                            ftfc_result.append("W: Bearish")

                    ftfc_str = ", ".join(ftfc_result) if ftfc_result else "N/A"

                    # Append result with FTFC
                    results.append(
                        {
                            "Ticker": ticker,
                            "Previous Candle": prev_candle,
                            "Current Candle": curr_candle,
                            "Direction": "Up" if float(curr["Close"]) > float(curr["Open"]) else "Down",
                            "Close Price": round(float(curr["Close"]), 2),
                            "FTFC": ftfc_str,  # New column
                        }
                    )
                if prev_candle not in prev_patterns or curr_candle not in curr_patterns:
                    continue

                current_close = float(curr["Close"])

                # -----------------------
                # FTFC (MONTHLY + WEEKLY)
                # -----------------------
                ftfc = []
                ftfc_states = {}

                weekly = yf.download(
                    ticker, period="6mo", interval="1wk", progress=False
                )
                if not weekly.empty:
                    w_open = weekly.iloc[-1]["Open"]
                    ftfc_states["W"] = "Bullish" if current_close > w_open else "Bearish"
                    ftfc.append(f"W: {ftfc_states['W']}")

                monthly = yf.download(
                    ticker, period="12mo", interval="1mo", progress=False
                )
                if not monthly.empty:
                    m_open = monthly.iloc[-1]["Open"]
                    ftfc_states["M"] = "Bullish" if current_close > m_open else "Bearish"
                    ftfc.append(f"M: {ftfc_states['M']}")

                # -----------------------
                # FTFC ALIGNMENT FILTER
                # -----------------------
                if ftfc_alignment_only:
                    if len(ftfc_states) < 2:
                        continue
                    if ftfc_states["M"] != ftfc_states["W"]:
                        continue

                # -----------------------
                # RESULTS
                # -----------------------
                results.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle,
                    "Direction": "Up" if curr["Close"] > curr["Open"] else "Down",
                    "Close Price": round(current_close, 2),
                    "FTFC": ", ".join(ftfc),
                })

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(df)} matching tickers")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No tickers matched the selected STRAT criteria.")
