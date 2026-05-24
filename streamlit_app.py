import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()

    try:
        sp500_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")

    curated_etfs = [
        "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "IVV",
        "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI",
        "XLB", "XLU", "XLRE", "ARKK", "SMH", "SOXX", "TLT",
        "HYG", "GLD", "SLV", "USO"
    ]

    major_indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]

    tickers.update(curated_etfs)
    tickers.update(major_indexes)

    return sorted(tickers)


TICKERS = load_tickers()


def candle_color(row):
    if row["Close"] > row["Open"]:
        return "Green"
    elif row["Close"] < row["Open"]:
        return "Red"
    else:
        return "Neutral"


def strat_candle_type(current, previous):
    color = candle_color(current)

    if current["High"] < previous["High"] and current["Low"] > previous["Low"]:
        return "Inside Candle"

    if current["High"] > previous["High"] and current["Low"] < previous["Low"]:
        return "Outside Candle"

    if current["High"] > previous["High"] and current["Low"] >= previous["Low"]:
        if color == "Green":
            return "2U Green"
        elif color == "Red":
            return "2U Red"

    if current["Low"] < previous["Low"] and current["High"] <= previous["High"]:
        if color == "Green":
            return "2D Green"
        elif color == "Red":
            return "2D Red"

    return "Other"


def get_direction(candle_type):
    if candle_type in ["2U Green", "2D Green"]:
        return "Bullish"
    elif candle_type in ["2U Red", "2D Red"]:
        return "Bearish"
    elif candle_type == "Inside Candle":
        return "Neutral / Consolidation"
    elif candle_type == "Outside Candle":
        return "Expansion"
    else:
        return "Other"


@st.cache_data(ttl=1800)
def fetch_data(ticker, period, interval):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False
        )

        if df.empty or len(df) < 3:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        return df

    except Exception:
        return None


st.title("STRAT Stock Scanner")

st.write("Scan S&P 500 stocks, curated ETFs, and major indexes for STRAT candle patterns.")

timeframe_options = {
    "Daily": {"period": "6mo", "interval": "1d"},
    "Weekly": {"period": "2y", "interval": "1wk"},
    "Monthly": {"period": "5y", "interval": "1mo"},
    "Hourly": {"period": "60d", "interval": "1h"},
    "4 Hour": {"period": "6mo", "interval": "4h"},
}

selected_timeframe = st.selectbox(
    "Select Timeframe",
    list(timeframe_options.keys())
)

patterns = [
    "Inside Candle",
    "Outside Candle",
    "2U Green",
    "2U Red",
    "2D Green",
    "2D Red"
]

previous_patterns = st.multiselect(
    "Choose Previous Candle Pattern",
    patterns,
    default=[]
)

current_patterns = st.multiselect(
    "Choose Current Candle Pattern",
    patterns,
    default=[]
)

match_logic = st.radio(
    "Scan Logic",
    ["Previous OR Current", "Previous AND Current"],
    index=0
)

max_tickers = st.slider(
    "Number of tickers to scan",
    min_value=25,
    max_value=len(TICKERS),
    value=min(100, len(TICKERS)),
    step=25
)

run_scan = st.button("Run Scanner")

if run_scan:
    if not previous_patterns and not current_patterns:
        st.warning("Select at least one previous or current candle pattern.")
    else:
        results = []

        tf = timeframe_options[selected_timeframe]
        scan_list = TICKERS[:max_tickers]

        progress = st.progress(0)
        status = st.empty()

        for i, ticker in enumerate(scan_list):
            status.write(f"Scanning {ticker}...")

            df = fetch_data(ticker, tf["period"], tf["interval"])

            if df is None or len(df) < 3:
                progress.progress((i + 1) / len(scan_list))
                continue

            prior_reference = df.iloc[-3]
            previous_candle = df.iloc[-2]
            current_candle = df.iloc[-1]

            previous_type = strat_candle_type(previous_candle, prior_reference)
            current_type = strat_candle_type(current_candle, previous_candle)

            previous_match = previous_type in previous_patterns
            current_match = current_type in current_patterns

            if match_logic == "Previous OR Current":
                matched = previous_match or current_match
            else:
                matched = previous_match and current_match

            if matched:
                results.append({
                    "Ticker": ticker,
                    "Previous Candle": previous_type,
                    "Current Candle": current_type,
                    "Direction": get_direction(current_type),
                    "Close Price": round(float(current_candle["Close"]), 2)
                })

            progress.progress((i + 1) / len(scan_list))

        status.empty()

        results_df = pd.DataFrame(results)

        if not results_df.empty:
            st.success(f"Found {len(results_df)} matching tickers.")
            st.dataframe(results_df, use_container_width=True)
        else:
            st.warning("No tickers matched the selected STRAT criteria.")
