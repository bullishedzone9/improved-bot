import tempfile
import unittest
from pathlib import Path

from research_data import load_ohlc_csv


class HistoricalOHLCLoadTests(unittest.TestCase):
    def load_text(self, text):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        try:
            tmp.write(text)
            tmp.close()
            return load_ohlc_csv(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_loads_valid_chronological_ohlc(self):
        frame = self.load_text(
            "date,open,high,low,close,volume\n"
            "2025-01-01,1.1,1.2,1.0,1.15,10\n"
            "2025-01-02,1.15,1.25,1.1,1.2,11\n"
        )
        self.assertEqual(len(frame), 2)
        self.assertTrue(frame["date"].is_monotonic_increasing)

    def test_rejects_missing_columns(self):
        with self.assertRaisesRegex(ValueError, "Missing required"):
            self.load_text("date,close\n2025-01-01,1.2\n")

    def test_rejects_unsorted_or_duplicate_dates(self):
        with self.assertRaisesRegex(ValueError, "chronological"):
            self.load_text("date,open,high,low,close\n2025-01-02,1,2,.5,1.5\n2025-01-01,1,2,.5,1.5\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load_text("date,open,high,low,close\n2025-01-01,1,2,.5,1.5\n2025-01-01,1,2,.5,1.5\n")

    def test_rejects_bad_price_values(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            self.load_text("date,open,high,low,close\n2025-01-01,1,2,0,1.5\n")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.load_text("date,open,high,low,close\n2025-01-01,1,inf,.5,1.5\n")

    def test_rejects_invalid_ohlc_relationship(self):
        with self.assertRaisesRegex(ValueError, "OHLC relationship"):
            self.load_text("date,open,high,low,close\n2025-01-01,1,1.1,.9,1.2\n")


if __name__ == "__main__":
    unittest.main()
