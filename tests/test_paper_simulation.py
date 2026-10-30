import unittest

from on_demand_agent.paper import simulate_paper_trade


class PaperSimulationTests(unittest.TestCase):
    def simulate(self, **overrides):
        args = dict(
            direction="BUY",
            stop_price=99.0,
            target_price=102.0,
            future_candles=[{"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5}],
            starting_equity=10000.0,
            risk_percent=0.25,
        )
        args.update(overrides)
        return simulate_paper_trade(**args)

    def test_take_profit(self):
        result = self.simulate(future_candles=[
            {"open": 100.0, "high": 102.5, "low": 99.5, "close": 102.2}
        ])
        self.assertEqual(result.status, "SIMULATED")
        self.assertEqual(result.exit_reason, "TAKE_PROFIT")
        self.assertAlmostEqual(result.gross_r, 2.0)
        self.assertAlmostEqual(result.pnl, 50.0)

    def test_stop_loss(self):
        result = self.simulate(future_candles=[
            {"open": 100.0, "high": 100.5, "low": 98.5, "close": 99.0}
        ])
        self.assertEqual(result.exit_reason, "STOP_LOSS")
        self.assertAlmostEqual(result.gross_r, -1.0)
        self.assertAlmostEqual(result.pnl, -25.0)

    def test_both_levels_touched_stop_wins_conservatively(self):
        result = self.simulate(future_candles=[
            {"open": 100.0, "high": 103.0, "low": 98.0, "close": 101.0}
        ])
        self.assertEqual(result.exit_reason, "STOP_FIRST_BOTH_TOUCHED")
        self.assertAlmostEqual(result.gross_r, -1.0)

    def test_gap_through_stop_uses_worse_open_fill(self):
        result = self.simulate(future_candles=[
            {"open": 98.0, "high": 99.0, "low": 97.0, "close": 98.5}
        ])
        self.assertEqual(result.exit_reason, "STOP_GAP")
        self.assertAlmostEqual(result.exit_price, 98.0)
        self.assertAlmostEqual(result.gross_r, -2.0)

    def test_transaction_costs_reduce_net_result(self):
        result = self.simulate(
            costs_r=0.1,
            future_candles=[{"open": 100.0, "high": 102.5, "low": 99.5, "close": 102.0}],
        )
        self.assertAlmostEqual(result.gross_r, 2.0)
        self.assertAlmostEqual(result.net_r, 1.9)
        self.assertAlmostEqual(result.pnl, 47.5)

    def test_daily_loss_lock_rejects_trade(self):
        result = self.simulate(daily_loss_percent=1.0)
        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.reason, "DAILY_LOSS_LOCK")

    def test_risk_cap_is_enforced(self):
        result = self.simulate(risk_percent=0.5)
        self.assertEqual(result.reason, "INVALID_EQUITY_OR_RISK")

    def test_invalid_levels_rejected(self):
        result = self.simulate(stop_price=101.0, target_price=102.0)
        self.assertEqual(result.reason, "INVALID_BUY_LEVELS_OR_GAP_PAST_TARGET")

    def test_empty_future_candles_rejected(self):
        result = self.simulate(future_candles=[])
        self.assertEqual(result.reason, "NO_FUTURE_CANDLES")


if __name__ == "__main__":
    unittest.main()
