# Deploy ARC_SILK Forex Intelligence from an Android phone

This guide deploys the Python **paper-analysis dashboard**. It does not compile the MQL4 Expert Advisor, connect to Exness, or place trades.

## Deploy with Streamlit Community Cloud

1. Open https://share.streamlit.io/ in your phone browser and sign in with the GitHub account that can access `bullishedzone9/improved-bot`.
2. Choose **Create app** (wording may vary).
3. Select repository `bullishedzone9/improved-bot`.
4. Select branch `fix/mt4-ea-demo-safety` to test the current pull-request version.
5. Set the main file path to `app.py`.
6. Deploy and wait for the build to finish. If the platform asks for a Python version, use Python 3.10 or a newer version supported by the host.
7. Open the resulting app URL on your phone.

If the repository or branch is not offered, verify that the signed-in GitHub account has access and that the branch exists. Do not make the pull request merge just to deploy a test copy.

## Load real historical candles

1. Download a completed historical file from a reputable source. Confirm symbol, timeframe, date range, timezone, data type, and licence.
2. In the dashboard, use the historical file uploader and select a supported `.csv`, `.json.gz`, `.parquet`, or `.pq` file.
3. Check the displayed dataset summary and row-removal count before running the EMA/ATR paper backtest.
4. Keep a record of the file/source, instrument, timeframe, date range, and backtest assumptions alongside the result.

The dashboard's instrument label is user-selected; it does not independently prove the uploaded file's symbol or timeframe. Avoid simulated/demo candles for performance conclusions. Backtest results are estimates and may omit real spreads, financing, slippage, broker-specific contract details, and execution effects.

## Safety and limitations

- The Python engine is paper-only: it does not send broker orders.
- The MT4 EA remains demo-only and disabled by default.
- GitHub Actions source-safety checks are not a MetaEditor compilation.
- Before any EA release, compile it in MetaEditor and test it in MT4 Strategy Tester and on a demo account.
- Never place broker passwords, API keys, or account credentials in source files or public repository settings.
