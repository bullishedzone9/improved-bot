"""Static safety regression checks for the demo-only MT4 EA (not an MQL4 compiler)."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "mt4" / "ARC_SILK_AutoTrader.mq4"

REQUIRED = (
    "input bool            EnableDemoTrading = false;",
    "if(!IsDemo())",
    "if(!IsDemo() || !EnableDemoTrading",
    "RiskPercent > 0.5",
    "MaxDailyLossPercent > 2.0",
    "MODE_SPREAD",
    "MODE_STOPLEVEL",
    "AccountFreeMarginCheck",
    "OrderSend(",
    "SlippagePoints, sl, tp",
    "CountOpenPositionsByMagic() >= MaxOpenPositions",
    "GlobalVariableCheck(key)",
    "iATR(",
    "MathFloor((riskMoney / lossPerLot) / lotStep",
    "existing positions are not automatically closed",
)
FORBIDDEN = (
    "AccountDemo()",
    "OrderClose(",
    "OrderModify(",
    "EnableLiveTrading",
    "LiveTradingEnabled",
    "\\n",
)


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in source]
    present = [item for item in FORBIDDEN if item in source]

    # Lightweight delimiter check after stripping comments and string literals.
    import re

    without_comments = re.sub(r"//[^\\n]*|/\\*.*?\\*/", "", source, flags=re.S)
    without_strings = re.sub(r'"(?:\\\\.|[^"\\\\])*"', '""', without_comments)
    delimiter_errors = []
    for opening, closing in (("(", ")"), ("{", "}"), ("[", "]")):
        depth = 0
        for char in without_strings:
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth < 0:
                    delimiter_errors.append(f"unexpected {closing}")
                    break
        if depth != 0:
            delimiter_errors.append(f"unbalanced {opening}{closing}: depth={depth}")

    if missing or present or delimiter_errors:
        raise SystemExit(
            "EA safety static check failed; "
            f"missing={missing}; forbidden={present}; "
            f"delimiter_errors={delimiter_errors}"
        )
    print("MT4 EA static safety checks passed (not a MetaEditor compile).")


if __name__ == "__main__":
    main()
