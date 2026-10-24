from __future__ import annotations

import math
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
    st.markdown("#### Backtest assumptions")
    cost_bps = st.number_input(
        "Estimated cost per position change (basis points)",
        min_value=0.0, max_value=100.0, value=2.0, step=0.5,
        help="Illustrative one-way cost charged when entering or exiting a position. One basis point is 0.01%; this is not a live broker quote.",
    )
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
use_demo = st.checkbox("Use built-in simulated demo data (no download needed)", value=False)

if uploaded is None and not use_demo:
    st.info("Upload a historical CSV or select the built-in simulated demo data to explore the dashboard.")
    st.markdown("#### CSV example")
    st.code("date,open,high,low,close\\n2026-01-01,1.1000,1.1050,1.0980,1.1030\\n2026-01-02,1.1030,1.1080,1.1010,1.1060", language="csv")
else:
    try:
        if use_demo:
            demo_rows = []
            close_price = 1.1000
            for i, date_value in enumerate(pd.date_range("2026-01-01", periods=65, freq="D")):
                open_price = close_price
                drift = 0.00018 + math.sin(i / 5) * 0.00012 + (-0.00008 if i % 7 == 0 else 0)
                close_price = max(0.8, close_price + drift)
                demo_rows.append({
                    "date": date_value,
                    "open": open_price,
                    "high": max(open_price, close_price) + 0.0007 + (i % 3) * 0.00005,
                    "low": min(open_price, close_price) - 0.0006 - (i % 4) * 0.00004,
                    "close": close_price,
                    "volume": 800 + (i * 37) % 600,
                })
            df = pd.DataFrame(demo_rows)
            st.info("Simulated demo prices are for interface testing only; they are not real market data.")
        else:
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
        st.markdown("#### Historical strategy backtest")
        st.caption("Research only: long when fast SMA is above slow SMA; otherwise cash. Positions are delayed by one row to reduce look-ahead bias. Costs are charged on entries and exits.")
        valid_signal = df["fast_ma"].notna() & df["slow_ma"].notna()
        signal = (df["fast_ma"] > df["slow_ma"]).where(valid_signal, False).astype(int)
        position = signal.shift(1).fillna(0).astype(int)
        market_return = df["close"].pct_change().fillna(0.0)
        position_change = position.diff().abs().fillna(position.abs())
        strategy_return = (position * market_return - position_change * (float(cost_bps) / 10000.0)).where(valid_signal, 0.0)
        equity_curve = (1.0 + strategy_return).cumprod()
        benchmark_curve = (1.0 + market_return.where(valid_signal, 0.0)).cumprod()
        backtest_drawdown = equity_curve / equity_curve.cummax() - 1.0
        completed_exits = int(((position.shift(1).fillna(0) == 1) & (position == 0) & valid_signal).sum())
        trade_returns = []
        entry_index = None
        for idx in range(len(df)):
            if not bool(valid_signal.iloc[idx]):
                continue
            current_position = int(position.iloc[idx])
            previous_position = int(position.iloc[idx - 1]) if idx > 0 else 0
            if current_position == 1 and previous_position == 0:
                entry_index = idx
            elif current_position == 0 and previous_position == 1 and entry_index is not None:
                trade_returns.append(float((1.0 + strategy_return.iloc[entry_index:idx + 1]).prod() - 1.0))
                entry_index = None
        strategy_total = float(equity_curve.iloc[-1] - 1.0)
        benchmark_total = float(benchmark_curve.iloc[-1] - 1.0)
        metrics = st.columns(4)
        metrics[0].metric("Strategy total return", f"{strategy_total * 100:.2f}%")
        metrics[1].metric("Buy-and-hold return", f"{benchmark_total * 100:.2f}%")
        metrics[2].metric("Strategy max drawdown", f"{backtest_drawdown.min() * 100:.2f}%")
        metrics[3].metric("Completed long trades", str(completed_exits))
        if trade_returns:
            win_rate = 100 * sum(value > 0 for value in trade_returns) / len(trade_returns)
            st.write(f"Completed-trade win rate, after assumed costs: **{win_rate:.1f}%**.")
        else:
            st.write("Completed-trade win rate is unavailable because no long-position trade has completed in this sample.")
        equity_plot = pd.DataFrame({"Strategy equity (start = 1.0)": equity_curve, "Buy-and-hold equity (start = 1.0)": benchmark_curve})
        if chart_index:
            equity_plot.index = df[chart_index]
        st.line_chart(equity_plot.tail(500))
        st.caption(f"Assumed one-way cost: {float(cost_bps):.1f} basis points per entry or exit. Excludes variable slippage, financing, leverage and execution constraints. Historical results are not predictions or evidence of future profitability.")

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
