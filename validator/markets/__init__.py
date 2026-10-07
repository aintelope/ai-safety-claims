"""Per-market metric code. Each module's compute(rows) returns values keyed by the
qualification and bar ids in that market's contract; thresholds stay in the contract."""

from . import market_01, market_04

MODULES = {
    "market-01": market_01,
    "market-04": market_04,
}
