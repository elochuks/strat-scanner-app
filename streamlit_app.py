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

    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]

    tickers.update(etfs)
    tickers.update(indexes)

    return sorted(tickers)


TICKERS = load_tickers()

# =====================================================
# DATA HELPERS
# =====================================================
def flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def resample_ohlcv(df, rule):
    df = df.copy()

    return (
        df.resample(rule)
        .agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        })
        .dropna()
    )


@st.cache_data(ttl=3600)
def get_data(ticker, timeframe):
    if timeframe == "4-Hour":
        df = yf.download(
            ticker,
            period="60d",
            interval="1h",
            progress=False,
            auto_adjust=False,
        )
        df = flatten_columns(df)
        df = resample_ohlcv(df, "4h")

    elif timeframe == "2-Day":
        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        df = flatten_columns(df)
        df = resample_ohlcv(df, "2D")

    elif timeframe == "Daily":
        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        df = flatten_columns(df)

    elif timeframe == "2-Week":
        df = yf.download(
            ticker,
            period="2y",
            interval="1wk",
            progress=False,
            auto_adjust=False,
        )
        df = flatten_columns(df)
        df = resample_ohlcv(df, "2W")

    elif timeframe == "Weekly":
        df = yf.download(
            ticker,
            period="2y",
            interval="1wk",
            progress=False,
            auto_adjust=False,
        )
        df = flatten_columns(df)

    elif timeframe == "Monthly":
        df = yf.download(
            ticker,
            period="5y",
            interval="1mo",
            progress=False,
            auto_adjust=False,
        )
        df = flatten_columns(df)

    elif timeframe == "3-Month":
        df = yf.download(
            ticker,
            period="10y",
            interval="1mo",
            progress=False,
            auto_adjust=False,
        )
        df = flatten_columns(df)
        df = resample_ohlcv(df, "3ME")

    else:
        return pd.DataFrame()

    required_cols = ["Open", "High", "Low", "Close", "Volume"]

    if df.empty:
        return pd.DataFrame()

    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    return df.dropna()


# =====================================================
# STRAT LOGIC
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


def get_ftfc(ticker, close_price):
    result = []

    try:
        monthly = yf.download(
            ticker,
            period="2y",
            interval="1mo",
            progress=False,
            auto_adjust=False,
        )
        monthly = flatten_columns(monthly)

        if not monthly.empty:
            month_open = float(monthly.iloc[-1]["Open"])

            if close_price > month_open:
                result.append("M: Bullish")
            elif close_price < month_open:
                result.append("M: Bearish")
            else:
                result.append("M: Neutral")
    except Exception:
        result.append("M: N/A")

    try:
        weekly = yf.download(
            ticker,
            period="1y",
            interval="1wk",
            progress=False,
            auto_adjust=False,
        )
        weekly = flatten_columns(weekly)

        if not weekly.empty:
            week_open = float(weekly.iloc[-1]["Open"])

            if close_price > week_open:
                result.append("W: Bullish")
            elif close_price < week_open:
                result.append("W: Bearish")
            else:
                result.append("W: Neutral")
    except Exception:
        result.append("W: N/A")

    return ", ".join(result) if result else "N/A"


def calculate_rvol(df):
    if len(df) < 21:
        return None

    current_volume = float(df.iloc[-2]["Volume"])
    avg_volume = float(df["Volume"].iloc[-21:-1].mean())

    if avg_volume == 0:
        return None

    return round(current_volume / avg_volume, 2)


# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers: S&P 500 + ETFs + Indexes")

timeframe = st.selectbox(
    "Select Timeframe",
    ["4-Hour", "2-Day", "Daily", "2-Week", "Weekly", "Monthly", "3-Month"],
)

available_patterns = [
    "1 (Inside)",
    "3 (Outside)",
    "2U Red",
    "2U Green",
    "2D Red",
    "2D Green",
    "Undefined",
]

st.subheader("STRAT Pattern Filters")

prev_patterns = st.multiselect(
    "Previous Closed Candle Pattern",
    options=available_patterns,
    default=available_patterns,
)

curr_patterns = st.multiselect(
    "Current Closed Candle Pattern",
    options=available_patterns,
    default=["2U Green", "2D Red", "1 (Inside)", "3 (Outside)"],
)

show_errors = st.checkbox("Show ticker errors", value=False)

scan_button = st.button("Run Scanner")

# =====================================================
# SCANNER
# =====================================================
if scan_button:
    results = []
    errors = []

    progress = st.progress(0)

    with st.spinner("Scanning market..."):
        for i, ticker in enumerate(TICKERS):
            try:
                data = get_data(ticker, timeframe)

                # Need at least 4 candles because we avoid the live candle
                if data.empty or len(data) < 4:
                    continue

                # Use only CLOSED candles
                prev_prev = data.iloc[-4]
                prev = data.iloc[-3]
                curr = data.iloc[-2]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if prev_candle not in prev_patterns:
                    continue

                if curr_candle not in curr_patterns:
                    continue

                close_price = float(curr["Close"])
                open_price = float(curr["Open"])
                high_price = float(curr["High"])
                low_price = float(curr["Low"])

                direction = "Up" if close_price > open_price else "Down"

                ftfc = get_ftfc(ticker, close_price)
                rvol = calculate_rvol(data)

                results.append({
                    "Ticker": ticker,
                    "Timeframe": timeframe,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle,
                    "Direction": direction,
                    "Open": round(open_price, 2),
                    "High": round(high_price, 2),
                    "Low": round(low_price, 2),
                    "Close": round(close_price, 2),
                    "RVOL": rvol,
                    "FTFC": ftfc,
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

        bullish_df = df[df["Current Candle"].str.contains("2U Green|1 \\(Inside\\)|3 \\(Outside\\)", regex=True)]
        bearish_df = df[df["Current Candle"].str.contains("2D Red", regex=True)]

        st.subheader("All Matches")
        st.dataframe(df, use_container_width=True)

        st.subheader("Bullish / Watchlist Candidates")
        st.dataframe(bullish_df, use_container_width=True)

        st.subheader("Bearish Candidates")
        st.dataframe(bearish_df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Results as CSV",
            csv,
            "strat_scan_results.csv",
            "text/csv",
            key="download-csv"
        )

    else:
        st.warning("No tickers matched the selected STRAT criteria.")

    if show_errors and errors:
        st.subheader("Errors")
        st.dataframe(pd.DataFrame(errors), use_container_width=True)
