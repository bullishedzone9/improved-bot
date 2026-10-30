import unittest
import pandas as pd
import numpy as np

from ea_backtest import EAResearchConfig, run_ea_aligned_backtest


class EAAlignedBacktestTests(unittest.TestCase):
    def sample(self, n=400):
        dates = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
        # Smooth deterministic oscillation produces both EMA cross directions.
        close = 1.1 + np.linspace(0, 0.01, n) + 0.003 * np.sin(np.arange(n) / 8)
        return pd.DataFrame({
            "date": dates, "open": close,
            "high": close + 0.0005, "low": close - 0.0005, "close": close
        })

    def test_returns_research_report_and_strategy_identity(self):
        report = run_ea_aligned_backtest(self.sample())
        self.assertEqual(report["status"], "RESEARCH_ONLY")
        self.assertEqual(report["strategy"], "MT4_EMA_CROSS_ATR_SL_TP_APPROXIMATION")
        self.assertIn("assumptions", report)

    def test_rejects_invalid_ohlc(self):
        data = self.sample()
        data.loc[10, "high"] = data.loc[10, "low"] - 0.1
        with self.assertRaisesRegex(ValueError, "invalid OHLC high"):
            run_ea_aligned_backtest(data)

    def test_rejects_unsorted_timestamps(self):
        data = self.sample()
        data.loc[20, "date"], data.loc[21, "date"] = data.loc[21, "date"], data.loc[20, "date"]
        with self.assertRaisesRegex(ValueError, "chronological"):
            run_ea_aligned_backtest(data)

    def test_config_rejects_excessive_risk(self):
        with self.assertRaisesRegex(ValueError, "risk_percent"):
            run_ea_aligned_backtest(self.sample(), EAResearchConfig(risk_percent=1.0))


if __name__ == "__main__":
    unittest.main()
