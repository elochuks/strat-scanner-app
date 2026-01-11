import streamlit as st
import yfinance as yf
import pandas as pd
from yahoo_fin import stock_info as si

st.set_page_config(page_title="STRAT Scanner – Full S&P 500", layout="wide")
st.title("📊 STRAT Scanner – Full S&P 500 Scan")

# -----------------------------------
# Get S&P 500 Tick List Automatically
# -----------------------------------
@st.cache_data
def get_sp500_tickers():
    try:
        tickers = si.tickers_sp500()
        return tickers
    except Exception as e:
        st.error(f"Failed to fetch S&P 500 list: {e}")
        return []

sp500_tickers = get_sp500_tickers()

st.write(f"Total S&P 500 tickers loaded: {len(sp500_tickers)}")

# -----------------------------------
# Timeframe Selector
# -----------------------------------
TIMEFRAME_MAP = {
    "Daily": ("1d", "6mo"),
    "Weekly": ("1wk", "2y"),
    "Monthly": ("1mo", "10y"),
}

timeframe = st.selectbox("Select Timeframe", list(TIMEFRAME_MAP.keys()))

# -----------------------------------
# STRAT Classification
# -----------------------------------
def strat_type(curr, prev):
    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
        return "1"
    elif curr["High"] > prev["High"] and curr["Low"] >= prev["Low"]:
        return "2U"
    elif curr["Low"] < prev["Low"] and curr["High"] <= prev["High"]:
        return "2D"
    elif curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3"
    else:
        return None

# -----------------------------------
# Scanner Logic
# -----------------------------------
if st.button("🚀 Run Scanner"):
    results = {"Bullish": {}, "Bearish": {}}
    interval, period = TIMEFRAME_MAP[timeframe]

    with st.spinner("Scanning S&P 500…"):
        for ticker in sp500_tickers:
            try:
                df = yf.download(ticker, interval=interval, period=period, progress=False)
                if df.shape[0] < 3:
                    continue

                prev = df.iloc[-3]
                curr = df.iloc[-2]
                nextc = df.iloc[-1]

                prev_type = strat_type(curr, prev)
                curr_type = strat_type(nextc, curr)
                combo = f"{prev_type} → {curr_type}"

                if combo in ["1 → 2U", "2D → 2U", "3 → 2U"]:
                    results["Bullish"].setdefault(combo, []).append(ticker)
                elif combo in ["1 → 2D", "2U → 2D", "3 → 2D"]:
                    results["Bearish"].setdefault(combo, []).append(ticker)

            except Exception as e:
                st.warning(f"{ticker} error: {e}")

    # -----------------------------------
    # Displaying Results
    # -----------------------------------
    st.success("Scan Complete!")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟢 Bullish STRAT Results")
        if results["Bullish"]:
            for combo, tkrs in results["Bullish"].items():
                st.markdown(f"**{combo}**")
                st.write(", ".join(tkrs))
        else:
            st.write("No bullish setups found.")

    with col2:
        st.subheader("🔴 Bearish STRAT Results")
        if results["Bearish"]:
            for combo, tkrs in results["Bearish"].items():
                st.markdown(f"**{combo}**")
                st.write(", ".join(tkrs))
        else:
            st.write("No bearish setups found.")
