from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="ARC_SILK | Forex Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); padding: 1rem; border-radius: .75rem;}
    .risk-note {padding: .85rem 1rem; border-radius: .65rem; border: 1px solid rgba(220,170,100,.5);}
</style>
""", unsafe_allow_html=True)

st.title("⚡ ARC_SILK")
st.subheader("SILKOUS Forex Intelligence")
st.warning(
    "PAPER ANALYSIS ONLY — No broker connection, live orders, or guaranteed trading signals. "
    "Use historical data for research, not as a promise of future results."
)

with st.sidebar:
    st.header("Analysis settings")
    pair = st.selectbox("Instrument label", ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "Other"])
    if pair == "Other":
        pair = st.text_input("Enter instrument label", value="CUSTOM").strip().upper() or "CUSTOM"
    equity = st.number_input("Demo account balance ($)", min_value=0.0, value=500.0, step=50.0)
    risk_pct = st.slider("Illustrative risk budget (%)", min_value=0.1, max_value=2.0, value=0.25, step=0.05)
    fast_window = st.number_input("Fast moving average", min_value=2, max_value=200, value=20, step=1)
    slow_window = st.number_input("Slow moving average", min_value=3, max_value=500, value=50, step=1)
    if fast_window >= slow_window:
        st.warning("For a conventional moving-average comparison, the fast window should be smaller than the slow window.")

risk_budget = equity * risk_pct / 100
c1, c2, c3 = st.columns(3)
c1.metric("Demo balance", f"${equity:,.2f}")
c2.metric("Illustrative risk budget", f"${risk_budget:,.2f}")
c3.metric("Risk setting", f"{risk_pct:.2f}%")
st.caption("Risk budget is an arithmetic estimate only. It does not calculate position size, leverage, spread, fees, slippage, or stop-loss execution.")

st.markdown("### Historical price analysis")
st.write("Upload a CSV containing a **close** column. Optional columns: **date/time**, **open**, **high**, **low**, and **volume**. Rows should be in chronological order.")
uploaded = st.file_uploader("Historical price data (CSV)", type=["csv"])

if uploaded is None:
    st.info("Upload a historical CSV to view price trends, summary statistics, and drawdown.")
    st.markdown("#### CSV example")
    st.code("date,open,high,low,close\n2026-01-01,1.1000,1.1050,1.0980,1.1030\n2026-01-02,1.1030,1.1080,1.1010,1.1060", language="csv")
else:
    try:
        df = pd.read_csv(uploaded)
        df.columns = [str(col).strip().lower() for col in df.columns]
        if "close" not in df.columns:
            st.error("CSV is missing the required 'close' column.")
            st.stop()

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        original_rows = len(df)
        df = df.dropna(subset=["close"]).copy()
        df = df[df["close"] > 0].copy()
        if len(df) < max(3, int(slow_window)):
            st.error(f"Not enough valid positive close prices. Need at least {max(3, int(slow_window))} rows for the selected slow moving average; found {len(df)}.")
            st.stop()

        date_col = next((c for c in ["datetime", "timestamp", "date", "time"] if c in df.columns), None)
        if date_col:
            parsed_dates = pd.to_datetime(df[date_col], errors="coerce", utc=True)
            if parsed_dates.notna().sum() > 0:
                df["_date"] = parsed_dates
                df = df.sort_values("_date").reset_index(drop=True)
                chart_index = "_date"
            else:
                chart_index = None
                st.warning(f"Could not parse '{date_col}' as dates; using CSV row order.")
        else:
            chart_index = None
            st.caption("No date/time column found; analysis follows the CSV row order.")

        df["fast_ma"] = df["close"].rolling(int(fast_window)).mean()
        df["slow_ma"] = df["close"].rolling(int(slow_window)).mean()
        df["period_return_pct"] = df["close"].pct_change() * 100
        running_peak = df["close"].cummax()
        df["drawdown_pct"] = (df["close"] / running_peak - 1) * 100

        latest = df.iloc[-1]
        previous_fast = df["fast_ma"].iloc[-2] if len(df) > 1 else float("nan")
        previous_slow = df["slow_ma"].iloc[-2] if len(df) > 1 else float("nan")

        st.markdown(f"#### {pair} overview")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latest close", f"{latest['close']:.5f}")
        m2.metric(f"SMA {int(fast_window)}", f"{latest['fast_ma']:.5f}")
        m3.metric(f"SMA {int(slow_window)}", f"{latest['slow_ma']:.5f}")
        m4.metric("Max drawdown in file", f"{df['drawdown_pct'].min():.2f}%")
        if original_rows != len(df):
            st.caption(f"Data quality: {original_rows - len(df)} row(s) removed due to invalid or non-positive close prices.")

        if pd.isna(latest["fast_ma"]) or pd.isna(latest["slow_ma"]):
            st.info("Trend candidate unavailable until both moving averages have enough observations.")
        elif latest["fast_ma"] > latest["slow_ma"]:
            st.success("Trend candidate: BULLISH — fast moving average is above slow moving average.")
        elif latest["fast_ma"] < latest["slow_ma"]:
            st.info("Trend candidate: BEARISH — fast moving average is below slow moving average.")
        else:
            st.info("Trend candidate: NEUTRAL — moving averages are equal.")
        if pd.notna(previous_fast) and pd.notna(previous_slow):
            if previous_fast <= previous_slow and latest["fast_ma"] > latest["slow_ma"]:
                st.write("Possible upward moving-average crossover in the latest row.")
            elif previous_fast >= previous_slow and latest["fast_ma"] < latest["slow_ma"]:
                st.write("Possible downward moving-average crossover in the latest row.")

        plot_df = df.tail(500).copy()
        if chart_index:
            plot_df = plot_df.set_index(chart_index)
        st.markdown("#### Price and moving averages")
        st.line_chart(plot_df[["close", "fast_ma", "slow_ma"]].rename(columns={
            "close": "Close", "fast_ma": f"SMA {int(fast_window)}", "slow_ma": f"SMA {int(slow_window)}"
        }))
        st.markdown("#### Recent observations")
        display_cols = ([date_col] if date_col else []) + ["close", "fast_ma", "slow_ma", "period_return_pct", "drawdown_pct"]
        st.dataframe(df[display_cols].tail(20).round(6), use_container_width=True, hide_index=True)

        with st.expander("Data quality and method notes"):
            st.write(f"- Valid close observations: {len(df):,}")
            st.write(f"- Earliest to latest rows shown: up to the last 500 observations.")
            st.write("- Maximum drawdown is calculated from the uploaded close-price sequence, without deposits, withdrawals, fees, or position sizing.")
            st.write("- Moving-average comparisons are descriptive candidates only; they are not backtested or validated trading signals.")
            st.write("- CSV timestamps are parsed as UTC when a recognizable date/time column is present.")
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError, TypeError) as exc:
        st.error(f"Could not process this CSV: {exc}")
    except Exception as exc:
        st.error(f"Unexpected analysis error ({type(exc).__name__}). Check the CSV format and try again.")

st.divider()
st.caption("ARC_SILK • Historical data only • Paper mode • No orders executed")
