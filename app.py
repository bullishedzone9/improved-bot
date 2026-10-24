from __future__ import annotations

import math
import pandas as pd
import streamlit as st
from live_quotes import fetch_quote_payload, validate_quote

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

st.markdown("### Live Forex market snapshot")
st.caption("Quotes are supplied by a third-party market-data API. Feed availability and quote freshness depend on that provider; this is not a broker execution feed.")
live_pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
live_pair = st.selectbox("Live quote pair", live_pairs, index=0, key="live_quote_pair")
if st.button("Refresh live quote", key="refresh_live_quote"):
    st.cache_data.clear()

@st.cache_data(ttl=15, show_spinner=False)
def fetch_live_quote(symbol: str) -> dict:
    payload = fetch_quote_payload(symbol)
    return validate_quote(payload, symbol)


try:
    quote = fetch_live_quote(live_pair)
    q1, q2, q3 = st.columns(3)
    q1.metric("Bid / last / mid", f"{quote['bid']:.5f}" if quote["bid"] is not None else "Unavailable")
    q2.metric("Ask", f"{quote['ask']:.5f}" if quote["ask"] is not None else "Unavailable")
    spread = quote["ask"] - quote["bid"] if quote["ask"] is not None and quote["bid"] is not None else None
    q3.metric("Displayed spread", f"{spread:.5f}" if spread is not None else "Unavailable")
    st.caption(f"Provider time: {quote['timestamp']} · Retrieved: {quote['received_at']} · Source: {quote['source']}")
    if not quote["timestamp_verified"]:
        st.warning("This provider response has no usable market timestamp. Price freshness cannot be verified; do not rely on this quote for trading decisions.")
    else:
        st.success("Provider timestamp passed the configured freshness check. Compare against your broker before making decisions.")
    st.warning("Snapshot only: no live trading or broker orders are enabled.")
except Exception as exc:
    st.error(f"Live quote validation failed for {live_pair}: {type(exc).__name__}: {exc}")
    st.info("No unverified or simulated fallback price is displayed. Historical analysis remains available.")

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

        removed_rows = original_rows - len(df)
        if removed_rows:
            st.warning(f"Data quality: removed {removed_rows} row(s) with missing, non-numeric, or non-positive close prices.")

        # When OHLC columns are supplied, reject contradictory candles rather
        # than quietly calculating indicators from malformed market data.
        if all(col in df.columns for col in ["open", "high", "low", "close"]):
            ohlc = df[["open", "high", "low", "close"]]
            invalid_ohlc = (
                ohlc.isna().any(axis=1)
                | (df["high"] < df[["open", "close", "low"]].max(axis=1))
                | (df["low"] > df[["open", "close", "high"]].min(axis=1))
                | (df["high"] < df["low"])
                | (df[["open", "high", "low"]] <= 0).any(axis=1)
            )
            if invalid_ohlc.any():
                st.error(
                    f"CSV contains {int(invalid_ohlc.sum())} invalid OHLC row(s). "
                    "Check that prices are positive, High is at least Open/Close/Low, "
                    "and Low is at most Open/Close/High."
                )
                st.stop()

        date_col = next((c for c in ["datetime", "timestamp", "date", "time"] if c in df.columns), None)
        if date_col:
            parsed_dates = pd.to_datetime(df[date_col], errors="coerce", utc=True)
            invalid_dates = parsed_dates.isna()
            if invalid_dates.any():
                st.error(
                    f"CSV contains {int(invalid_dates.sum())} unparseable or missing value(s) "
                    f"in the '{date_col}' column. Correct the timestamps before analysis."
                )
                st.stop()
            if parsed_dates.duplicated().any():
                duplicate_count = int(parsed_dates.duplicated(keep=False).sum())
                st.error(
                    f"CSV contains {duplicate_count} rows with duplicate timestamps in '{date_col}'. "
                    "Resolve duplicate times so returns and backtest periods are unambiguous."
                )
                st.stop()
            df["_date"] = parsed_dates
            df = df.sort_values("_date").reset_index(drop=True)
            chart_index = "_date"
        else:
            chart_index = None
            st.warning("No date/time column found; analysis follows CSV row order. Ensure rows are chronological.")

        if len(df) < max(3, int(slow_window)):
            st.error(f"Not enough valid positive close prices. Need at least {max(3, int(slow_window))} rows for the selected slow moving average; found {len(df)}.")
            st.stop()

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
        st.markdown("#### Price and moving averages")
        # Use an explicit quantitative axis so mobile rendering cannot choose
        # a misleading range. Drop only missing MA points; keep Close visible
        # from the beginning of the selected window.
        import altair as alt

        if chart_index:
            plot_df["_chart_x"] = plot_df[chart_index]
            x_encoding = alt.X("_chart_x:T", title="Date", axis=alt.Axis(labelOverlap=True, labelAngle=0))
        else:
            plot_df["_chart_x"] = range(len(plot_df))
            x_encoding = alt.X("_chart_x:Q", title="Observation")

        chart_long = plot_df[["_chart_x", "close", "fast_ma", "slow_ma"]].melt(
            id_vars="_chart_x", var_name="series", value_name="price"
        ).dropna(subset=["price"])
        series_names = {
            "close": "Close",
            "fast_ma": f"SMA {int(fast_window)}",
            "slow_ma": f"SMA {int(slow_window)}",
        }
        chart_long["series"] = chart_long["series"].map(series_names)
        y_min = float(chart_long["price"].min())
        y_max = float(chart_long["price"].max())
        padding = max((y_max - y_min) * 0.08, abs(y_max) * 0.0001, 1e-8)
        price_chart = (
            alt.Chart(chart_long)
            .mark_line()
            .encode(
                x=x_encoding,
                y=alt.Y(
                    "price:Q",
                    title="Price",
                    scale=alt.Scale(domain=[y_min - padding, y_max + padding], zero=False, nice=False),
                ),
                color=alt.Color("series:N", title="Series"),
                tooltip=[
                    alt.Tooltip("_chart_x:T" if chart_index else "_chart_x:Q", title="Date" if chart_index else "Observation"),
                    alt.Tooltip("series:N", title="Series"),
                    alt.Tooltip("price:Q", title="Price", format=".5f"),
                ],
            )
            .properties(height=320)
            .interactive()
        )
        st.altair_chart(price_chart, use_container_width=True)
        st.markdown("#### Historical strategy backtest")
        st.caption("Research only: long when fast SMA is above slow SMA; otherwise cash. Positions are delayed by one row to reduce look-ahead bias. Costs are charged on entries and exits.")
        from backtest import run_moving_average_backtest

        results = run_moving_average_backtest(
            df["close"], df["fast_ma"], df["slow_ma"], float(cost_bps)
        )
        equity_curve = results["equity_curve"]
        benchmark_curve = results["benchmark_curve"]
        strategy_total = results["strategy_return"]
        benchmark_total = results["benchmark_return"]
        backtest_drawdown = results["drawdown"]
        completed_exits = results["completed_trades"]
        trade_returns = results["trade_returns"]
        positions = results["position"]
        open_long_at_end = bool(len(positions) and int(positions.iloc[-1]) == 1)
        eligible_periods = int(results["benchmark_period_returns"].ne(0).sum())
        # Count eligibility from the strategy position timeline, including
        # eligible flat/cash periods; this is more informative than counting
        # non-zero benchmark returns, since a valid market return can be zero.
        valid_ma = df["fast_ma"].notna() & df["slow_ma"].notna()
        eligible_periods = int(valid_ma.shift(1, fill_value=False).sum())

        st.caption(
            f"Evaluation window: {eligible_periods:,} eligible return period(s) after moving-average warm-up. "
            "Strategy and buy-and-hold benchmark use the same eligible window."
        )
        metrics = st.columns(2)
        metrics[0].metric("Strategy total return (after assumed costs)", f"{strategy_total * 100:.2f}%")
        metrics[1].metric("Buy-and-hold return (same window)", f"{benchmark_total * 100:.2f}%")
        metrics = st.columns(3)
        metrics[0].metric("Strategy max drawdown", f"{backtest_drawdown.min() * 100:.2f}%")
        metrics[1].metric("Completed long trades", str(completed_exits))
        metrics[2].metric("Position at end of sample", "OPEN LONG" if open_long_at_end else "CASH")
        if trade_returns:
            win_rate = 100 * sum(value > 0 for value in trade_returns) / len(trade_returns)
            st.write(f"Completed-trade win rate, after assumed costs: **{win_rate:.1f}%**.")
        else:
            st.write("Completed-trade win rate is unavailable because no long-position trade has completed in this sample.")
        if open_long_at_end:
            st.info(
                "A long position remains open at the end of this sample. Its mark-to-market return is included "
                "in the strategy equity curve, but it is excluded from completed-trade count and completed-trade win rate."
            )
        equity_plot = pd.DataFrame({"Strategy equity (start = 1.0)": equity_curve, "Buy-and-hold equity (start = 1.0)": benchmark_curve})
        if chart_index:
            equity_plot.index = df[chart_index]
        st.line_chart(equity_plot.tail(500))
        st.caption(f"Assumed one-way cost: {float(cost_bps):.1f} basis points per entry or exit. Excludes variable slippage, financing, leverage and execution constraints. Results are compounded returns on a normalized 1.0 starting equity, not account-dollar projections. Historical results are not predictions or evidence of future profitability.")

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
st.caption("ARC_SILK • Live quote snapshot + historical research • Paper mode • No orders executed")
