import tempfile
import unittest
from pathlib import Path

from histdata_import import load_histdata_m1, resample_complete_m15


class HistDataImportTests(unittest.TestCase):
    def make_csv(self, rows):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(rows)
        f.close()
        return Path(f.name)

    def test_parses_fixed_est_and_resamples_complete_m15(self):
        rows = []
        # 15 M1 bars from 00:00 EST become 05:00 UTC.
        for minute in range(15):
            rows.append(f"20240101 {minute:02d}00;1.1;1.2;1.0;1.1;0")
        path = self.make_csv("\n".join(rows))
        try:
            m1, meta = load_histdata_m1(path)
            m15, report = resample_complete_m15(m1)
            self.assertEqual(meta["source_timezone"], "EST fixed UTC-5, no DST")
            self.assertEqual(len(m15), 1)
            self.assertEqual(m15.date.iloc[0].hour, 5)
            self.assertEqual(report["m15_complete_bars"], 1)
        finally:
            path.unlink(missing_ok=True)

    def test_drops_incomplete_m15_buckets(self):
        rows = "\n".join(
            f"20240101 {minute:02d}00;1.1;1.2;1.0;1.1;0" for minute in range(14)
        )
        path = self.make_csv(rows)
        try:
            m1, _ = load_histdata_m1(path)
            with self.assertRaisesRegex(ValueError, "No complete"):
                resample_complete_m15(m1)
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_duplicate_timestamps(self):
        row = "20240101 000000;1.1;1.2;1.0;1.1;0"
        path = self.make_csv(row + "\n" + row)
        try:
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_histdata_m1(path)
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_invalid_ohlc(self):
        path = self.make_csv("20240101 000000;1.1;1.0;0.9;1.2;0")
        try:
            with self.assertRaisesRegex(ValueError, "Invalid OHLC high"):
                load_histdata_m1(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
