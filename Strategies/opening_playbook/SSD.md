# Strategy Specification Document (SSD)
## Strategy ID
opening_playbook

## Objective
Trade high-quality opening moves (continuation/fade) only when premarket conditions + catalyst justify participation.

## Universe / Eligibility
- Liquid names only
- Must meet “tradable today” filters (gap %, premarket volume, catalyst)
- Otherwise: NO TRADE

## Market Regime / When it runs
- Premarket scan + plan before open
- Executes during first-minutes opening window per playbook

## Signal / Setup
- Classify each symbol as: Continuation / Fade / No Trade
- Entry logic is mechanical (rule-based), not discretionary

## Risk Controls
- Max position size (per symbol + total)
- Max slippage
- Stop distance
- Time-based kill switch (exit if not working quickly)

## Execution
- Use precomputed plan; do not “think” during execution
- If constraints violated: do not place order

## Monitoring
- Track slippage, fill quality, stopouts, and latency per session

## Failure Modes / Invalidations
- No real catalyst
- Thin liquidity / wide spreads
- Excessive slippage or repeated partial fills
- Regime change (edge disappears)
