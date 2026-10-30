"""Prepare HistData M1 CSV as normalized, complete M15 OHLC CSV."""
import argparse
import json

from histdata_import import load_histdata_m1, resample_complete_m15


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert HistData M1 CSV to normalized UTC M15")
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    args = parser.parse_args()
    try:
        m1, source_report = load_histdata_m1(args.input_csv)
        m15, resample_report = resample_complete_m15(m1)
        m15.to_csv(args.output_csv, index=False)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"source": source_report, "resample": resample_report,
                      "output_csv": args.output_csv}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
