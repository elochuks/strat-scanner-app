import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# ----------------------------
# S&P 500 SYMBOL LIST (STATIC)
# ----------------------------
SP500 = [
    "AAPL","MSFT","AMZN","NVDA","META","GOOGL","GOOG","TSLA","BRK-B","JPM",
    "JNJ","V","XOM","PG","UNH","HD","MA","LLY","AVGO","MRK",
    "PEP","KO","COST","ABBV","ADBE","CRM","NFLX","WMT","ORCL","BAC"
    # ⬆ Add full S&P 500 list here if desired
]

# ----------------------------
# DATA FETCHING
# ----------------------------
def fetch_data(symbol, interval):
    period_map = {
        "Daily": "6mo",
        "Weekly": "2y",
        "Monthly": "10y"
    }

    interval_map = {
        "Daily": "1d",
        "Weekly": "1wk",
        "Monthly": "1mo"
    }

    df = yf.download(
        symbol,
        period=period_map[interval],
        interval=interval_map[interval],
        progress=False
    )

    return df.dropna()

# ----------------------------
# STRAT LOGIC
# ----------------------------
def strat_pattern(df):
    if len(df) < 2:
        return None

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    if curr.High < prev.High and curr.Low > prev.Low:
        return "1"
    if curr.High > prev.High and curr.Low >= prev.Low:
        return "2U"
    if curr.Low < prev.Low and curr.High <= prev.High:
        return "2D"
    if curr.High > prev.High and curr.Low < prev.Low:
        return "3"

    return None


def strat_reversal(df):
    if len(df) < 3:
        return None

    c1 = df.iloc[-3]
    c2 = df.iloc[-2]
    c3 = df.iloc[-1]

    # 2-1-2 Bullish
    if (
        c2.High < c1.High and c2.Low > c1.Low and
        c3.High > c2.High
    ):
        return "2-1-2U"

    # 2-1-2 Bearish
    if (
        c2.High < c1.High and c2.Low > c1.Low and
        c3.Low < c2.Low
    ):
        return "2-1-2D"

    return None

# ----------------------------
# STREAMLIT UI
# ----------------------------
st.title("📊 STRAT Market Scanner")

timeframe = st.selectbox(
    "Select Timeframe",
    ["Daily", "Weekly", "Monthly"]
)

patterns_selected = st.multiselect(
    "Select STRAT Patterns",
    ["1", "2U", "2D", "3", "2-1-2U", "2-1-2D"],
    default=["2U", "2D"]
)

scan_button = st.button("🚀 Run Scan")

# ----------------------------
# SCANNER
# ----------------------------
if scan_button:
    results = []

    with st.spinner("Scanning S&P 500 stocks..."):
        for symbol in SP500:
            try:
                df = fetch_data(symbol, timeframe)

                base_pattern = strat_pattern(df)
                reversal_pattern = strat_reversal(df)

                detected = base_pattern or reversal_pattern

                if detected in patterns_selected:
                    results.append({
                        "Symbol": symbol,
                        "Pattern": detected,
                        "Close": round(df.iloc[-1].Close, 2),
                        "High": round(df.iloc[-1].High, 2),
                        "Low": round(df.iloc[-1].Low, 2)
                    })

            except Exception:
                continue

    if results:
        st.success(f"Found {len(results)} matches")
        st.dataframe(pd.DataFrame(results))
    else:
        st.warning("No patterns found")

st.caption("Powered by STRAT methodology | Data: Yahoo Finance")
