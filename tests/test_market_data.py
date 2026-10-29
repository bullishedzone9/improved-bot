import gzip
import json
import unittest

from market_data import load_historical_upload


class MarketDataUploadTests(unittest.TestCase):
    def test_reads_compressed_ohlc_json_and_normalizes_fields(self):
        payload = gzip.compress(json.dumps([
            {"ts": 1767225600, "o": 1.1, "h": 1.12, "l": 1.09, "c": 1.11, "v": 23}
        ]).encode())
        frame = load_historical_upload("EURUSD_2026.json.gz", payload)
        self.assertEqual(frame.loc[0, "open"], 1.1)
        self.assertEqual(frame.loc[0, "high"], 1.12)
        self.assertEqual(frame.loc[0, "low"], 1.09)
        self.assertEqual(frame.loc[0, "close"], 1.11)
        self.assertEqual(frame.loc[0, "volume"], 23)
        self.assertTrue(str(frame.loc[0, "date"]).startswith("2026-01-01"))

    def test_rejects_invalid_gzip_json(self):
        with self.assertRaisesRegex(ValueError, "gzip JSON"):
            load_historical_upload("bad.json.gz", b"not a gzip file")


if __name__ == "__main__":
    unittest.main()
