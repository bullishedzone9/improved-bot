"""Run ARC_SILK fixed-parameter holdout research on an OHLC CSV export."""
from __future__ import annotations

import argparse
import json

from research_data import load_ohlc_csv
from walk_forward import evaluate_walk_forward


def main() -> int:
    parser = argparse.ArgumentParser(description="Research-only chronological holdout backtest")
    parser.add_argument("csv", help="Historical OHLC CSV with date,open,high,low,close columns")
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--cost-bps", type=float, default=2.0,
                        help="Estimated cost per side in basis points; must be justified by broker data")
    args = parser.parse_args()
    try:
        data = load_ohlc_csv(args.csv)
        report = evaluate_walk_forward(
            data["close"], fast_window=args.fast, slow_window=args.slow,
            train_fraction=args.train_fraction, cost_bps=args.cost_bps,
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    report["source_file"] = args.csv
    report["date_start_utc"] = data["date"].iloc[0].isoformat()
    report["date_end_utc"] = data["date"].iloc[-1].isoformat()
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
