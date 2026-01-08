import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")
st.title("📊 STRAT Scanner (Daily / Weekly / Monthly)")

# -------------------------
# User Inputs
# -------------------------
tickers_input = st.text_area(
    "Enter tickers (comma-separated)",
    "AAPL,MSFT,NVDA,TSLA,SPY"
)

timeframe = st.selectbox(
    "Select timeframe",
    ["Daily", "Weekly", "Monthly"]
)

lookback = st.slider("Lookback candles", 10, 120, 40)

tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# -------------------------
# STRAT Candle Classification
# -------------------------
def classify_strat(df):
    df = df.copy()
    df["strat"] = ""

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        if curr.High <= prev.High and curr.Low >= prev.Low:
            df.iloc[i, df.columns.get_loc("strat")] = "1"
        elif curr.High > prev.High and curr.Low < prev.Low:
            df.iloc[i, df.columns.get_loc("strat")] = "3"
        elif curr.High > prev.High:
            df.iloc[i, df.columns.get_loc("strat")] = "2U"
        elif curr.Low < prev.Low:
            df.iloc[i, df.columns.get_loc("strat")] = "2D"

    return df

# -------------------------
# Resample for Weekly / Monthly
# -------------------------
def resample_ohlc(df, tf):
    if tf == "Weekly":
        return df.resample("W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

    if tf == "Monthly":
        return df.resample("M").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

    return df

# -------------------------
# Scan Logic
# -------------------------
results = []

if st.button("🔍 Run STRAT Scan"):
    with st.spinner("Scanning..."):
        for ticker in tickers:
            try:
                df = yf.download(
                    ticker,
                    period="2y",
                    interval="1d",
                    progress=False
                )

                if df.empty:
                    continue

                df = resample_ohlc(df, timeframe)
                df = df.tail(lookback)

                if len(df) < 3:
                    continue

                df = classify_strat(df)

                last = df.iloc[-1]
                prev = df.iloc[-2]
                prev2 = df.iloc[-3]

                signal = None

                # Inside Bar
                if last.strat == "1":
                    signal = "Inside Bar (1)"

                # 2-1-2 Bullish
                elif prev2.strat == "2D" and prev.strat == "1" and last.strat == "2U":
                    signal = "2-1-2 Bullish"

                # 2-1-2 Bearish
                elif prev2.strat == "2U" and prev.strat == "1" and last.strat == "2D":
                    signal = "2-1-2 Bearish"

                # Directional Break
                elif last.strat in ["2U", "2D"]:
                    signal = f"Directional Break ({last.strat})"

                if signal:
                    results.append({
                        "Ticker": ticker,
                        "Timeframe": timeframe,
                        "Signal": signal,
                        "Close": round(last.Close, 2),
                        "High": round(last.High, 2),
                        "Low": round(last.Low, 2)
                    })

            except Exception:
                st.warning(f"Error scanning {ticker}")

    if results:
        st.subheader("📈 Scan Results")
        st.dataframe(pd.DataFrame(results))
    else:
        st.info("No STRAT setups found.")
