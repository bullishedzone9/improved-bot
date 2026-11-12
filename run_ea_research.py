"""CLI for the MT4 EMA/ATR research approximation."""
import argparse
import json

from research_data import load_ohlc_csv
from ea_backtest import EAResearchConfig, run_ea_aligned_backtest


def main() -> int:
    parser = argparse.ArgumentParser(description="Research-only MT4 EMA/ATR approximation")
    parser.add_argument("csv")
    parser.add_argument("--spread-points", type=float, required=True)
    parser.add_argument("--point", type=float, required=True)
    parser.add_argument("--risk-percent", type=float, default=0.25)
    args = parser.parse_args()
    try:
        frame = load_ohlc_csv(args.csv)
        report = run_ea_aligned_backtest(
            frame, EAResearchConfig(spread_points=args.spread_points,
                                    point=args.point, risk_percent=args.risk_percent)
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    report["source_file"] = args.csv
    report["date_start_utc"] = frame.date.iloc[0].isoformat()
    report["date_end_utc"] = frame.date.iloc[-1].isoformat()
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main)
