import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():

    tickers = [
        "AAPL","MSFT","NVDA","AMZN","META","GOOGL",
        "TSLA","AMD","NFLX","AVGO","JPM","BAC",
        "XOM","CVX","UNH","WMT","HD","COST",
        "SPY","QQQ","IWM","DIA","XLF","XLK",
        "XLE","XLV","XLI","XLY","XLP","GLD",
        "SLV","TLT","SQQQ","TQQQ"
    ]

    return sorted(set(tickers))


TICKERS = load_tickers()

# =====================================================
# STRAT LOGIC
# =====================================================
def strat_type(prev, curr):

    prev_high = float(prev["High"])
    prev_low = float(prev["Low"])

    curr_high = float(curr["High"])
    curr_low = float(curr["Low"])

    curr_open = float(curr["Open"])
    curr_close = float(curr["Close"])

    candle_color = "Green" if curr_close >= curr_open else "Red"

    # INSIDE
    if curr_high < prev_high and curr_low > prev_low:
        return "1 Inside"

    # OUTSIDE
    elif curr_high > prev_high and curr_low < prev_low:
        return "3 Outside"

    # 2U
    elif curr_high > prev_high:
        return f"2U {candle_color}"

    # 2D
    elif curr_low < prev_low:
        return f"2D {candle_color}"

    else:
        return "Undefined"


# =====================================================
# GET DATA
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

    interval = interval_map[timeframe]
    period = period_map[timeframe]

    df = yf.Ticker(ticker).history(
        period=period,
        interval=interval,
        auto_adjust=False
    )

    if df.empty:
        return pd.DataFrame()

    needed_cols = ["Open", "High", "Low", "Close", "Volume"]

    if not all(col in df.columns for col in needed_cols):
        return pd.DataFrame()

    return df[needed_cols].dropna()


# =====================================================
# RVOL
# =====================================================
def calculate_rvol(df):

    if len(df) < 22:
        return None

    current_volume = float(df.iloc[-2]["Volume"])

    avg_volume = float(
        df.iloc[-22:-2]["Volume"].mean()
    )

    if avg_volume == 0:
        return None

    return round(current_volume / avg_volume, 2)


# =====================================================
# FTFC
# =====================================================
def get_ftfc(ticker, close_price):

    result = []

    try:
        weekly = yf.Ticker(ticker).history(
            period="1y",
            interval="1wk"
        )

        if not weekly.empty:

            week_open = float(weekly.iloc[-1]["Open"])

            if close_price > week_open:
                result.append("W Bullish")
            else:
                result.append("W Bearish")

    except:
        pass

    try:
        monthly = yf.Ticker(ticker).history(
            period="5y",
            interval="1mo"
        )

        if not monthly.empty:

            month_open = float(monthly.iloc[-1]["Open"])

            if close_price > month_open:
                result.append("M Bullish")
            else:
                result.append("M Bearish")

    except:
        pass

    return " | ".join(result)


# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")

st.write(f"Scanning {len(TICKERS)} liquid tickers")

timeframe = st.selectbox(
    "Select Timeframe",
    ["Daily", "Weekly", "Monthly"]
)

patterns = [
    "1 Inside",
    "2U Green",
    "2U Red",
    "2D Green",
    "2D Red",
    "3 Outside",
    "Undefined"
]

selected_patterns = st.multiselect(
    "Current Candle Pattern",
    options=patterns,
    default=patterns
)

show_debug = st.checkbox(
    "Show Debug",
    value=True
)

scan_button = st.button("Run Scanner")

# =====================================================
# SCANNER
# =====================================================
if scan_button:

    results = []
    debug_rows = []
    errors = []

    progress = st.progress(0)

    for i, ticker in enumerate(TICKERS):

        try:

            df = get_data(ticker, timeframe)

            if df.empty or len(df) < 4:
                continue

            # Use CLOSED candles only
            prev = df.iloc[-3]
            curr = df.iloc[-2]

            current_pattern = strat_type(prev, curr)

            debug_rows.append({
                "Ticker": ticker,
                "Pattern": current_pattern
            })

            if current_pattern not in selected_patterns:
                continue

            close_price = float(curr["Close"])

            results.append({

                "Ticker": ticker,

                "Pattern": current_pattern,

                "Direction":
                    "Up"
                    if close_price >= float(curr["Open"])
                    else "Down",

                "Open": round(float(curr["Open"]), 2),

                "High": round(float(curr["High"]), 2),

                "Low": round(float(curr["Low"]), 2),

                "Close": round(close_price, 2),

                "RVOL": calculate_rvol(df),

                "FTFC": get_ftfc(
                    ticker,
                    close_price
                ),
            })

        except Exception as e:

            errors.append({
                "Ticker": ticker,
                "Error": str(e)
            })

        progress.progress(
            (i + 1) / len(TICKERS)
        )

    # =====================================================
    # RESULTS
    # =====================================================
    if results:

        results_df = pd.DataFrame(results)

        st.success(
            f"Found {len(results_df)} matching tickers"
        )

        st.dataframe(
            results_df,
            use_container_width=True
        )

        csv = results_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download CSV",
            csv,
            "strat_scan_results.csv",
            "text/csv"
        )

    else:
        st.warning(
            "No tickers matched the selected STRAT criteria."
        )

    # =====================================================
    # DEBUG
    # =====================================================
    if show_debug:

        if debug_rows:

            debug_df = pd.DataFrame(debug_rows)

            st.subheader("Pattern Counts")

            st.dataframe(
                debug_df["Pattern"]
                .value_counts()
                .reset_index(),
                use_container_width=True
            )

            st.subheader("Debug Rows")

            st.dataframe(
                debug_df,
                use_container_width=True
            )

        if errors:

            st.subheader("Errors")

            st.dataframe(
                pd.DataFrame(errors),
                use_container_width=True
            )
