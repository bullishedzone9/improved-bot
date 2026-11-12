# ARC_SILK — Phase 4: Chronological holdout research

## Added
`walk_forward.py` evaluates the existing fixed-parameter SMA long-or-cash strategy on an ordered history. It reports separate in-sample and out-of-sample total return, maximum drawdown, completed trades, win rate, profit factor and positive/negative period counts.

## Leakage control
The split is chronological. The last training observation is retained as a signal warm-up row for the out-of-sample run; its return is excluded from the test metrics. The signal generated at that close can first affect the next close-to-close return. No random shuffle and no parameter optimization occur.

## Limitations
- This is a single holdout split, not robust rolling walk-forward validation.
- Strategy is SMA long-or-cash; it does not model short trades.
- Cost is a fixed basis-point estimate per entry/exit. It does not model variable spread, swaps, financing, slippage, or broker fills.
- Input is close-price history; no intrabar stop/target path or contract-specific sizing is simulated here.
- Synthetic sample data is for software checks only and must not be treated as market evidence.
- No broker connection, order execution, or deployment is included.

## Test
```bash
python -m unittest tests.test_walk_forward -v
```
