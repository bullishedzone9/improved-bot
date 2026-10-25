import importlib
import os
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

TEST_TOKEN = "test-token-that-is-long-enough-for-bridge-auth"
os.environ["ARC_SILK_BRIDGE_TOKEN"] = TEST_TOKEN

import bridge_service.main as bridge_main
bridge_main = importlib.reload(bridge_main)


class MT4BridgeServiceTests(unittest.TestCase):
    def setUp(self):
        bridge_main._latest = None
        bridge_main._received_monotonic = None
        self.client = TestClient(bridge_main.app)
        self.payload = {
            "schema_version": "1",
            "event_time": datetime.now(timezone.utc).isoformat(),
            "symbol": "EURUSD",
            "bid": 1.1000,
            "ask": 1.1002,
            "spread_points": 2.0,
            "sequence": 1,
        }

    def test_health_does_not_require_auth(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "read_only")

    def test_telemetry_requires_auth(self):
        response = self.client.post("/mt4/telemetry", json=self.payload)
        self.assertEqual(response.status_code, 401)

    def test_latest_quote_requires_auth(self):
        response = self.client.get("/mt4/latest")
        self.assertEqual(response.status_code, 401)

    def test_valid_quote_is_accepted_and_only_quote_fields_are_returned(self):
        payload = dict(self.payload, balance=12345, equity=12000, account_number="private")
        response = self.client.post(
            "/mt4/telemetry",
            json=payload,
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["accepted"])

        latest = self.client.get(
            "/mt4/latest",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        self.assertEqual(latest.status_code, 200)
        result = latest.json()["quote"]
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertNotIn("balance", result)
        self.assertNotIn("equity", result)
        self.assertNotIn("account_number", result)
        self.assertIn("received_at", result)

    def test_invalid_quote_is_rejected(self):
        payload = dict(self.payload, ask=1.0990)
        response = self.client.post(
            "/mt4/telemetry",
            json=payload,
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        self.assertEqual(response.status_code, 422)

    def test_latest_quote_unavailable_before_first_receipt(self):
        response = self.client.get(
            "/mt4/latest",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        self.assertEqual(response.status_code, 404)

    def test_oversized_payload_is_rejected(self):
        response = self.client.post(
            "/mt4/telemetry",
            content=b"x" * (bridge_main.MAX_BODY_BYTES + 1),
            headers={
                "Authorization": f"Bearer {TEST_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
