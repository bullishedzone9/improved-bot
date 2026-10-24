
import streamlit as st
import pandas as pd

st.set_page_config(page_title="ARC_SILK", page_icon="⚡")

st.title("⚡ ARC_SILK")
st.subheader("SILKOUS Forex Intelligence")
st.warning("PAPER MODE ONLY — No live trades or broker connection.")

equity = st.number_input(
    "Demo account balance ($)",
    min_value=10.0,
    value=500.0,
    step=50.0
)

risk_pct = st.slider(
    "Proposed risk per trade (%)",
    min_value=0.1,
    max_value=1.0,
    value=0.25,
    step=0.05
)

st.metric("Risk budget per trade", f"${equity * risk_pct / 100:.2f}")

pair = st.selectbox("Forex pair", ["EURUSD", "GBPUSD"])
uploaded = st.file_uploader("Upload historical price data (CSV)", type=["csv"])

if uploaded:
    try:
        df = pd.read_csv(uploaded)
        df.columns = [c.strip().lower() for c in df.columns]

        if "close" not in df.columns:
            st.error("Your CSV must contain a 'close' column.")
        else:
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["close"]).copy()

            if len(df) < 50:
                st.error("Please upload at least 50 valid price rows.")
            else:
                df["SMA20"] = df["close"].rolling(20).mean()
                df["SMA50"] = df["close"].rolling(50).mean()

                latest = df.iloc[-1]

                st.write(f"**Pair:** {pair}")
                st.metric("Latest uploaded close", f"{latest['close']:.5f}")
                st.line_chart(df[["close", "SMA20", "SMA50"]].tail(200))

                if latest["SMA20"] > latest["SMA50"]:
                    st.success("Trend candidate: BULLISH")
                elif latest["SMA20"] < latest["SMA50"]:
                    st.info("Trend candidate: BEARISH")
                else:
                    st.info("Trend candidate: NEUTRAL")

                st.caption(
                    "This is a basic moving-average candidate, not a "
                    "validated trading signal or a recommendation to trade."
                )
    except Exception as e:
        st.error(f"Could not read this file: {e}")
else:
    st.info("Upload historical forex prices to begin analysis.")

st.caption("ARC_SILK starter • Historical data only • No orders executed")
