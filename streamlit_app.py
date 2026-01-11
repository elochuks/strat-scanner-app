import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO

# -----------------------------------
# App Config
# -----------------------------------
st.set_page_config(page_title="STRAT Scanner", layout="wide")
st.title("📊 STRAT Scanner – Full S&P 500")

# -----------------------------------
# SAFE S&P 500 LOADER (NO 403)
# -----------------------------------
@st.cache_data
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        tables = pd.read_html(StringIO(response.text))
        df = tables[0]

        tickers = df["Symbol"].tolist()
        tickers = [t.replace(".", "-") for t in tickers]
        return tickers

    except Exception:
        # 🔒 HARD FAIL-SAFE (never breaks app)
        st.warning("Live S&P 500 fetch blocked — using fallback list.")
        return [
            "AAPL","MSFT","AMZN","NVDA","GOOGL","META","BRK-B","TSLA","JPM","JNJ",
            "V","PG","UNH","HD","MA","XOM","LLY","AVGO","COST","PEP",
            "ABBV","KO","MRK","WMT","BAC","NFLX","ADBE","CRM","ORCL","CSCO",
            "CVX","ACN","MCD","AMD","QCOM","INTC","IBM","GE","CAT","HON",
            "SPGI","INTU","AMAT","BKNG","TMO","ISRG","GS","MS","RTX","DE"
        ]

sp500_tickers = get_sp500_tickers()
st.caption(f"Loaded {len(sp500_tickers)} tickers")

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
# STRAT Candle Logic
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
    return None

# -----------------------------------
# Run Scanner
# -----------------------------------
if st.button("🚀 Run Scanner"):

    results = {"Bullish": {}, "Bearish": {}}
    interval, period = TIMEFRAME_MAP[timeframe]

    progress = st.progress(0)

    with st.spinner("Scanning markets..."):
        for i, ticker in enumerate(sp500_tickers):
            try:
                df = yf.download(
                    ticker,
                    interval=interval,
                    period=period,
                    progress=False,
                    threads=False
                )

                if len(df) < 3:
                    continue

                prev = df.iloc[-3]
                curr = df.iloc[-2]
                last = df.iloc[-1]

                prev_type = strat_type(curr, prev)
                curr_type = strat_type(last, curr)

                if not prev_type or not curr_type:
                    continue

                combo = f"{prev_type} → {curr_type}"

                if combo in ["1 → 2U", "2D → 2U", "3 → 2U"]:
                    results["Bullish"].setdefault(combo, []).append(ticker)

                elif combo in ["1 → 2D", "2U → 2D", "3 → 2D"]:
                    results["Bearish"].setdefault(combo, []).append(ticker)

            except Exception:
                pass

            progress.progress((i + 1) / len(sp500_tickers))

    progress.empty()
    st.success("Scan Complete")

    # -----------------------------------
    # Results Display
    # -----------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟢 Bullish STRAT Combos")
        if results["Bullish"]:
            for combo, tickers in results["Bullish"].items():
                st.markdown(f"**{combo}**")
                st.write(", ".join(tickers))
        else:
            st.write("No bullish setups found.")

    with col2:
        st.subheader("🔴 Bearish STRAT Combos")
        if results["Bearish"]:
            for combo, tickers in results["Bearish"].items():
                st.markdown(f"**{combo}**")
                st.write(", ".join(tickers))
        else:
            st.write("No bearish setups found.")
