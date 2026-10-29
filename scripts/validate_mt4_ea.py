"""Static safety regression checks for the demo-only MT4 EA (not an MQL4 compiler)."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "mt4" / "ARC_SILK_AutoTrader.mq4"

REQUIRED = (
    "input bool            EnableDemoTrading = false;",
    "if(!IsDemo())",
    "if(!IsDemo() || !EnableDemoTrading",
    "RiskPercent > 0.5",
    "MaxDailyLossPercent > 2.0",
    "(Ask - Bid) / Point",
    "MODE_STOPLEVEL",
    "AccountFreeMarginCheck",
    "OrderSend(",
    "SlippagePoints, sl, tp",
    "CountOpenPositionsByMagic() >= MaxOpenPositions",
    "GlobalVariableCheck(key)",
    "iATR(",
    "MathFloor((riskMoney / lossPerLot) / lotStep",
    "existing positions are not automatically closed",
    "new daily equity baseline established",
)
FORBIDDEN = (
    "AccountDemo()",
    "OrderClose(",
    "OrderModify(",
    "EnableLiveTrading",
    "LiveTradingEnabled",
    "\\n",
)


def strip_comments_and_strings(source: str) -> str:
    """Remove comments and quoted strings before checking delimiters."""
    out = []
    i = 0
    state = "code"
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                state = "line_comment"
                i += 2
                continue
            if char == "/" and nxt == "*":
                state = "block_comment"
                i += 2
                continue
            if char == '"':
                state = "string"
                i += 1
                continue
            out.append(char)
            i += 1
            continue
        if state == "line_comment":
            if char == "\n":
                out.append("\n")
                state = "code"
            i += 1
            continue
        if state == "block_comment":
            if char == "*" and nxt == "/":
                state = "code"
                i += 2
            else:
                i += 1
            continue
        if state == "string":
            if char == "\\":
                i += 2
            elif char == '"':
                state = "code"
                i += 1
            else:
                i += 1
    return "".join(out)


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in source]
    present = [item for item in FORBIDDEN if item in source]
    cleaned = strip_comments_and_strings(source)
    stack = []
    pairs = {")": "(", "}": "{", "]": "["}
    delimiter_errors = []
    for char in cleaned:
        if char in "({[":
            stack.append(char)
        elif char in ")}]":
            if not stack or stack[-1] != pairs[char]:
                delimiter_errors.append(f"unexpected {char}")
                break
            stack.pop()
    if stack:
        delimiter_errors.append(f"unclosed delimiters: {stack}")

    if missing or present or delimiter_errors:
        raise SystemExit(
            "EA safety static check failed; "
            f"missing={missing}; forbidden={present}; "
            f"delimiter_errors={delimiter_errors}"
        )
    print("MT4 EA static safety checks passed (not a MetaEditor compile).")


if __name__ == "__main__":
    main()
