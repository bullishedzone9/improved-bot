"""Static safety regression checks for the demo-only MT4 EA (not an MQL4 compiler)."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "mt4" / "ARC_SILK_AutoTrader.mq4"

REQUIRED = (
    "input bool   EnableDemoTrading = false",
    "if(!AccountDemo())",
    "RiskPercent = 0.5",
    "MaxDailyLossPercent = 2.0",
    "MODE_SPREAD",
    "MODE_STOPLEVEL",
    "AccountFreeMarginCheck",
    "OrderSend(",
    "sl, tp",
    "CurrentPositionCount() >= 1",
    "g_dailyLocked",
    "iATR(",
)
FORBIDDEN = ("OrderClose(", "OrderModify(", "AccountDemo()) return true")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in source]
    present = [item for item in FORBIDDEN if item in source]
    has_escaped_newline = "\\n" in source
    if missing or present or has_escaped_newline:
        raise SystemExit(
            "EA safety static check failed; "
            f"missing={missing}; forbidden={present}; "
            f"literal_escaped_newline={has_escaped_newline}"
        )
    print("MT4 EA static safety checks passed (not a MetaEditor compile).")


if __name__ == "__main__":
    main()
