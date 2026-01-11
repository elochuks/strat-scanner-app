import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO

st.set_page_config(page_title="STRAT Scanner", layout="wide")
st.title("📊 STRAT Scanner – Full S&P 500")

# -----------------------------------
# SAFE S&P 500 LOADER
# -----------------------------------
@st.cache_data
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        df = pd.read_html(StringIO(r.text))[0]
        return [t.replace(".", "-") for t in df["Symbol"]]
    except Exception:
        return ["AAPL","MSFT","AMZN","NVDA","META","GOOGL","TSLA","JPM","JNJ","XOM"]

tickers = get_sp500_tickers()
st.caption(f"Loaded {len(tickers)} tickers")

# -----------------------------------
# Timeframe
# -----------------------------------
TIMEFRAME_MAP = {
    "Daily": ("1d", "6mo"),
    "Weekly": ("1wk", "3y"),
    "Monthly": ("1mo", "15y"),
}

timeframe = st.selectbox("Select Timeframe", TIMEFRAME_MAP.keys())

# -----------------------------------
# STRAT LOGIC (RELAXED + CORRECT)
# -----------------------------------
def strat_type(curr, prev):
    if curr.High <= prev.High and curr.Low >= prev.Low:
        return "1"
    if curr.High > prev.High and curr.Low >= prev.Low:
        return "2U"
    if curr.Low < prev.Low and curr.High <= prev.High:
        return "2D"
    if curr.High > prev.High and curr.Low < prev.Low:
        return "3"
    return None

# -----------------------------------
# SCAN
# -----------------------------------
if st.button("🚀 Run Scanner"):

    bullish = {}
    bearish = {}

    interval, period = TIMEFRAME_MAP[timeframe]
    progress = st.progress(0)

    for i, ticker in enumerate(tickers):
        try:
            df = yf.download(
                ticker,
                interval=interval,
                period=period,
                progress=False,
                auto_adjust=True
            )

            # 🚨 IMPORTANT: REMOVE LIVE CANDLE
            df = df.iloc[:-1]

            if len(df) < 3:
                continue

            c1 = df.iloc[-3]  # candle before setup
            c2 = df.iloc[-2]  # setup candle
            c3 = df.iloc[-1]  # trigger candle

            t1 = strat_type(c2, c1)
            t2 = strat_type(c3, c2)

            if not t1 or not t2:
                continue

            combo = f"{t1} → {t2}"

            if t2 == "2U":
                bullish.setdefault(combo, []).append(ticker)
            elif t2 == "2D":
                bearish.setdefault(combo, []).append(ticker)

        except Exception:
            pass

        progress.progress((i + 1) / len(tickers))

    progress.empty()

    # -----------------------------------
    # DISPLAY
    # -----------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟢 Bullish STRAT Combos")
        if bullish:
            for combo, names in bullish.items():
                st.markdown(f"**{combo}**")
                st.write(", ".join(names))
        else:
            st.write("No bullish setups found.")

    with col2:
        st.subheader("🔴 Bearish STRAT Combos")
        if bearish:
            for combo, names in bearish.items():
                st.markdown(f"**{combo}**")
                st.write(", ".join(names))
        else:
            st.write("No bearish setups found.")
