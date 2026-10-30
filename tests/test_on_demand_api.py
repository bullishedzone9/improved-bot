import os
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from on_demand_agent.api import app

TOKEN = "test-only-agent-token-that-is-long-enough-123456"
client = TestClient(app)


def valid_payload():
    now = datetime.now(timezone.utc)
    candles = []
    for i in range(60):
        close = 1.1000 + i * 0.00001
        candles.append({
            "time": (now - timedelta(minutes=15 * (60 - i + 1))).isoformat(),
            "open": close,
            "high": close + 0.001,
            "low": close - 0.001,
            "close": close,
            "volume": 100,
        })
    return {
        "symbol": "EURUSD",
        "timeframe": "M15",
        "candles": candles,
        "bid": 1.1010,
        "ask": 1.1012,
        "point": 0.0001,
        "spread_points": 2,
        "quote_time": now.isoformat(),
        "daily_loss_percent": 0,
    }


class ScreeningApiTests(unittest.TestCase):
    def setUp(self):
        self.old_token = os.environ.get("ARC_SILK_AGENT_API_TOKEN")
        os.environ["ARC_SILK_AGENT_API_TOKEN"] = TOKEN

    def tearDown(self):
        if self.old_token is None:
            os.environ.pop("ARC_SILK_AGENT_API_TOKEN", None)
        else:
            os.environ["ARC_SILK_AGENT_API_TOKEN"] = self.old_token

    def test_health_reports_execution_disabled(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["order_execution"], "disabled")

    def test_screen_requires_bearer_token(self):
        response = client.post("/v1/screen", json=valid_payload())
        self.assertEqual(response.status_code, 401)

    def test_screen_endpoint_is_read_only(self):
        response = client.post(
            "/v1/screen",
            json=valid_payload(),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["execution"], "NOT_AVAILABLE")
        self.assertEqual(body["result"]["status"], "NO_TRADE")
        self.assertNotIn("order_id", body)

    def test_stale_quote_is_rejected_as_no_trade(self):
        payload = valid_payload()
        payload["quote_time"] = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        response = client.post(
            "/v1/screen",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["reason"], "STALE_QUOTE")

    def test_non_chronological_candles_rejected(self):
        payload = valid_payload()
        payload["candles"][10], payload["candles"][11] = payload["candles"][11], payload["candles"][10]
        response = client.post(
            "/v1/screen",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(response.status_code, 422)

    def test_naive_timestamp_rejected(self):
        payload = valid_payload()
        payload["quote_time"] = "2026-10-30T10:00:00"
        response = client.post(
            "/v1/screen",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
