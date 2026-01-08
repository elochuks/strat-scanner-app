import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# -----------------------------
# Get S&P 500 tickers
# -----------------------------
@st.cache_data
def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    return tables[0]["Symbol"].tolist()

# -----------------------------
# Resample timeframe
# -----------------------------
def resample_data(df, timeframe):
    if timeframe == "Weekly":
        return df.resample("W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()
    if timeframe == "Monthly":
        return df.resample("M").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()
    return df  # Daily

# -----------------------------
# STRAT Candle Classification
# -----------------------------
def strat_type(prev, curr):
    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
        return "1"
    if curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3"
    if curr["High"] > prev["High"]:
        return "2u"
    if curr["Low"] < prev["Low"]:
        return "2d"
    return None

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📊 STRAT Scanner – S&P 500")

timeframe = st.selectbox("Select Timeframe", ["Daily", "Weekly", "Monthly"])
patterns = st.multiselect(
    "Select STRAT Candle Types",
    ["1", "2u", "2d", "3"],
    default=["1", "2u", "2d", "3"]
)

scan_btn = st.button("Run Scan")

# -----------------------------
# Scanner Execution
# -----------------------------
if scan_btn:
    tickers = get_sp500()
    results = []

    progress = st.progress(0)
    status = st.empty()

    for i, ticker in enumerate(tickers):
        try:
            data = yf.download(ticker, period="6mo", interval="1d", progress=False)

            if len(data) < 3:
                continue

            data = resample_data(data, timeframe)

            if len(data) < 2:
                continue

            prev = data.iloc[-2]
            curr = data.iloc[-1]

            candle = strat_type(prev, curr)

            if candle in patterns:
                results.append({
                    "Ticker": ticker,
                    "STRAT": candle,
                    "High": round(curr["High"], 2),
                    "Low": round(curr["Low"], 2),
                    "Close": round(curr["Close"], 2)
                })

        except Exception:
            pass

        progress.progress((i + 1) / len(tickers))
        status.text(f"Scanning {ticker}")

    progress.empty()
    status.empty()

    if results:
        st.success(f"Found {len(results)} matching stocks")
        st.dataframe(pd.DataFrame(results))
    else:
        st.warning("No matches found")
