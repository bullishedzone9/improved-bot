import unittest
from unittest.mock import Mock, patch
import pandas as pd
import requests

from historical_sources import load_public_eurusd_h1


class PublicEurusdHistoryTests(unittest.TestCase):
    @patch("historical_sources.pd.read_parquet")
    @patch("historical_sources.requests.get")
    def test_normalizes_columns_and_sorts_timestamps(self, get, read_parquet):
        get.return_value = Mock(content=b"parquet", raise_for_status=Mock())
        read_parquet.return_value = pd.DataFrame({
            "Date": ["2024-01-02 01:00:00", "2024-01-02 00:00:00", "2024-01-02 02:00:00"],
            "Open": [1.2, 1.1, 1.3], "High": [1.21, 1.11, 1.31],
            "Low": [1.19, 1.09, 1.29], "Close": [1.205, 1.105, 1.305],
        })
        result = load_public_eurusd_h1()
        self.assertEqual(list(result["close"]), [1.105, 1.205, 1.305])
        self.assertIn("datetime", result.columns)
        get.assert_called_once()

    @patch("historical_sources.requests.get")
    def test_rejects_empty_download(self, get):
        get.return_value = Mock(content=b"", raise_for_status=Mock())
        with self.assertRaisesRegex(ValueError, "empty file"):
            load_public_eurusd_h1()

    @patch("historical_sources.pd.read_parquet")
    @patch("historical_sources.requests.get")
    def test_rejects_missing_ohlc_columns(self, get, read_parquet):
        get.return_value = Mock(content=b"parquet", raise_for_status=Mock())
        read_parquet.return_value = pd.DataFrame({"close": [1.1, 1.2, 1.3]})
        with self.assertRaisesRegex(ValueError, "missing required OHLC"):
            load_public_eurusd_h1()

    @patch("historical_sources.requests.get")
    def test_reports_download_errors(self, get):
        get.side_effect = requests.Timeout("timed out")
        with self.assertRaisesRegex(RuntimeError, "Could not download"):
            load_public_eurusd_h1()


if __name__ == "__main__":
    unittest.main()
