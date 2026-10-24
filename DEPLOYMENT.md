# Deployment guide

## Recommended host: Streamlit Community Cloud

This repository runs a Streamlit server. Vercel's standard deployment model is not a direct fit for this app, so do not create a Vercel project for it without first changing the application architecture.

1. Sign in to Streamlit Community Cloud using the GitHub account that can access this repository.
2. Authorize Streamlit to access the private `bullishedzone9/improved-bot` repository when prompted.
3. Create a new app and select repository `bullishedzone9/improved-bot`, branch `main`, and main file path `app.py`.
4. Deploy and wait for the build to complete.
5. Open the app URL and verify that the dashboard renders, the CSV uploader appears, and the paper-analysis warning is visible.
6. Upload a test CSV with at least 50 positive numeric close prices (or lower the slow moving average first) and verify the chart and summary render.
7. Test a malformed CSV and a CSV without a `close` column; the app should show a useful error instead of crashing.

## Security and release checks

- The app is historical-data analysis only. It must not be represented as a live trading bot.
- Do not add broker credentials or private keys to source code or CSV files.
- If credentials are ever needed for a future feature, store them in the hosting provider's secret manager, never in Git.
- Keep the GitHub Actions checks passing before merging future changes.
- A deployment is not considered verified until its build succeeds and the hosted app is manually smoke-tested.

## Current deployment status

No hosting project or public app URL is configured in this repository yet. A repository commit does not mean the app is deployed.
