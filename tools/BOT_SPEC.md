STEP 01 - IPS Constraints Checklist
Purpose: lock the bot's trading universe and hard constraints so every trade is checked against IPS rules
before execution.
1) Eligible asset classes (allowed universe)
[ ] Equities
[ ] ETFs (including credit ETFs such as LQD/HYG)
[ ] Listed options (equity / index / ETF)
[ ] Futures (equity index, rates/treasuries, commodities, FX)
[ ] FX spot and FX forwards
[ ] Volatility derivatives (e.g., VIX futures/options)
[ ] Crypto spot and derivatives only if explicitly permitted
[ ] Cross-asset macro instruments implied by signals (must still be in the allowed list above)
2) Prohibited instruments / behaviors (hard NOs)
[ ] OTC penny stocks
[ ] Illiquid OTC derivatives without transparent pricing
[ ] Binary options
[ ] Any algorithmic behavior designed to influence market prices
[ ] Naked short options
[ ] Excessive leverage beyond the fund's risk constraints
[ ] Rehypothecation of fund assets unless explicitly authorized in writing
3) Execution restrictions I must obey
Order types / routing
[ ] Allowed order types: Market, Limit, IOC/FOK, TWAP/VWAP, Iceberg, Pegged, Stop-limit only (no stop-market)
[ ] No market orders in thinly traded assets
[ ] No aggressive crossing during wide spreads
[ ] Prefer marketable limits over pure market orders (slippage control)
Time windows / auctions
[ ] Avoid trading in first 5 minutes after open and last 5 minutes before close
[ ] Exception only if strategy explicitly requires auction participation and liquidity conditions justify it
Dark pools
[ ] Use only if venue is regulated, has sufficient post-trade transparency, and no information leakage is detected
Best execution / monitoring
[ ] Enforce best execution: price improvement, low impact, reliable fills, minimal slippage, consistency across
venues
[ ] Enforce participation/impact gates (e.g., interval volume limits; reject trades with forecast impact above
threshold)
[ ] Run ongoing TCA and act on persistent underperformance (broker/venue review)
Make it enforceable (fill in the blanks)
[ ] CRYPTO_ALLOWED: true/false
Page 2
[ ] THIN_LIQUIDITY_RULE: block market orders if ADV < ____ OR top-of-book size < ____ OR spread > ____
bps
[ ] WIDE_SPREAD_RULE: treat as wide if spread > ____ bps OR spread > ____ x 20-day average
[ ] NO-TRADE WINDOWS (timezone): ____ to ____ (open), ____ to ____ (close)
[ ] DARK POOL POLICY: only venues on approved list; block if leakage_score > ____
Implementation hook: Put these rules into a config file (e.g., ips_rules.yaml). Before sending any order, run a
pre-trade compliance check that either (1) approves the order or (2) blocks it and logs the exact reason.
