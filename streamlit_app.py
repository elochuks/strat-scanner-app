import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS
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
        tickers.update(sp500_df["Symbol"].dropna().astype(str).tolist())
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

    indexes = [
        "^GSPC",
        "^NDX",
        "^DJI",
        "^RUT",
        "^VIX",
    ]

    tickers.update(etfs)
    tickers.update(indexes)

    cleaned = []
    for ticker in tickers:
        ticker = ticker.strip().replace(".", "-")
        if ticker:
            cleaned.append(ticker)

    if not cleaned:
        raise RuntimeError("No tickers loaded")

    return sorted(set(cleaned))


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

    candle_color = "Green" if curr_c >= curr_o else "Red"

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
# DATA FUNCTION
# =====================================================
@st.cache_data(ttl=3600)
def get_data(ticker, timeframe):
    interval_map = {
        "Daily": "1d",
        "Weekly": "1wk",
        "Monthly": "1mo",
    }

    period_map = {
        "Daily": "1y",
        "Weekly": "3y",
        "Monthly": "10y",
    }

    df = yf.Ticker(ticker).history(
        period=period_map[timeframe],
        interval=interval_map[timeframe],
        auto_adjust=False
    )

    if df.empty:
        return pd.DataFrame()

    required_cols = ["Open", "High", "Low", "Close", "Volume"]

    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    return df[required_cols].dropna()


# =====================================================
# RELATIVE VOLUME
# =====================================================
def calculate_rvol(df):
    if len(df) < 22:
        return None

    current_volume = float(df.iloc[-2]["Volume"])
    avg_volume = float(df.iloc[-22:-2]["Volume"].mean())

    if avg_volume == 0:
        return None

    return round(current_volume / avg_volume, 2)


# =====================================================
# FTFC
# =====================================================
def get_ftfc(ticker, close_price):
    ftfc_result = []

    try:
        monthly_data = yf.Ticker(ticker).history(
            period="5y",
            interval="1mo",
            auto_adjust=False
        )

        if not monthly_data.empty:
            current_month_open = float(monthly_data.iloc[-1]["Open"])

            if close_price > current_month_open:
                ftfc_result.append("M: Bullish")
            elif close_price < current_month_open:
                ftfc_result.append("M: Bearish")
            else:
                ftfc_result.append("M: Neutral")

    except Exception:
        ftfc_result.append("M: N/A")

    try:
        weekly_data = yf.Ticker(ticker).history(
            period="1y",
            interval="1wk",
            auto_adjust=False
        )

        if not weekly_data.empty:
            current_week_open = float(weekly_data.iloc[-1]["Open"])

            if close_price > current_week_open:
                ftfc_result.append("W: Bullish")
            elif close_price < current_week_open:
                ftfc_result.append("W: Bearish")
            else:
                ftfc_result.append("W: Neutral")

    except Exception:
        ftfc_result.append("W: N/A")

    return ", ".join(ftfc_result) if ftfc_result else "N/A"


# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers: S&P 500 + ETFs + Indexes")

timeframe = st.selectbox(
    "Select Timeframe",
    ["Daily", "Weekly", "Monthly"]
)

available_patterns = [
    "1 (Inside)",
    "3 (Outside)",
    "2U Red",
    "2U Green",
    "2D Red",
    "2D Green",
    "Undefined"
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

show_debug = st.checkbox("Show Debug Info", value=False)

scan_button = st.button("Run Scanner")

# =====================================================
# SCANNER
# =====================================================
if scan_button:
    results = []
    debug_rows = []
    errors = []

    progress = st.progress(0)

    with st.spinner("Scanning market..."):
        for i, ticker in enumerate(TICKERS):
            try:
                data = get_data(ticker, timeframe)

                if data.empty or len(data) < 4:
                    errors.append({
                        "Ticker": ticker,
                        "Error": "Not enough usable data"
                    })
                    continue

                # Use closed candles only
                prev_prev = data.iloc[-4]
                prev = data.iloc[-3]
                curr = data.iloc[-2]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                debug_rows.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle
                })

                if prev_candle not in prev_patterns:
                    continue

                if curr_candle not in curr_patterns:
                    continue

                open_price = float(curr["Open"])
                high_price = float(curr["High"])
                low_price = float(curr["Low"])
                close_price = float(curr["Close"])
                volume = int(curr["Volume"])

                ftfc_str = get_ftfc(ticker, close_price)

                results.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle,
                    "Direction": "Up" if close_price >= open_price else "Down",
                    "Open": round(open_price, 2),
                    "High": round(high_price, 2),
                    "Low": round(low_price, 2),
                    "Close Price": round(close_price, 2),
                    "Volume": volume,
                    "RVOL": calculate_rvol(data),
                    "FTFC": ftfc_str,
                })

            except Exception as e:
                errors.append({
                    "Ticker": ticker,
                    "Error": str(e)
                })

            progress.progress((i + 1) / len(TICKERS))

    if results:
        df = pd.DataFrame(results)

        st.success(f"Found {len(df)} matching tickers")

        st.subheader("All Matches")
        st.dataframe(df, use_container_width=True)

        bullish_df = df[
            df["Current Candle"].isin(
                ["2U Green", "1 (Inside)", "3 (Outside)"]
            )
        ]

        bearish_df = df[
            df["Current Candle"].isin(
                ["2D Red", "3 (Outside)"]
            )
        ]

        st.subheader("Bullish Candidates")
        st.dataframe(bullish_df, use_container_width=True)

        st.subheader("Bearish Candidates")
        st.dataframe(bearish_df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Results as CSV",
            csv,
            "strat_scan_results.csv",
            "text/csv",
        )

    else:
        st.warning("No tickers matched the selected STRAT criteria.")

    if show_debug:
        if debug_rows:
            debug_df = pd.DataFrame(debug_rows)

            st.subheader("Current Candle Pattern Counts")
            st.dataframe(
                debug_df["Current Candle"]
                .value_counts()
                .reset_index(),
                use_container_width=True
            )

            st.subheader("Previous Candle Pattern Counts")
            st.dataframe(
                debug_df["Previous Candle"]
                .value_counts()
                .reset_index(),
                use_container_width=True
            )

            st.subheader("Debug Rows")
            st.dataframe(debug_df, use_container_width=True)

        if errors:
            st.subheader("Errors")
            st.dataframe(pd.DataFrame(errors), use_container_width=True)
