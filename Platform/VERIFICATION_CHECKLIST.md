# Stock Page Data Pipeline — Verification Checklist

## Test Tickers
- [ ] AAPL — Technology, high ROE, has metrics
- [ ] MSFT — Technology, strong growth, has metrics
- [ ] GOOGL — Technology, moderate growth, has metrics
- [ ] TSLA — Consumer Discretionary, negative growth, high volatility

## Backend Verification

### 1. Snapshot Endpoint
- [ ] `GET /api/stocks/AAPL/snapshot` returns 200 with all fields
- [ ] `GET /api/stocks/MSFT/snapshot` returns 200 with all fields
- [ ] `GET /api/stocks/GOOGL/snapshot` returns 200 with all fields
- [ ] `GET /api/stocks/TSLA/snapshot` returns 200 with all fields
- [ ] `GET /api/stocks/ZZZZ/snapshot` returns 200 with null metrics (graceful unknown ticker)
- [ ] `GET /api/stocks/invalid123/snapshot` returns 400

### 2. Metric Labels
- [ ] `pe_trailing.label` == "TTM"
- [ ] `pe_forward_fy1.label` == "Forward FY1"
- [ ] `pe_forward_fy2.label` == "Forward FY2"
- [ ] `debt_to_equity_mrq.label` == "MRQ"
- [ ] `realized_vol_30d.label` == "30-Day"

### 3. Data Timestamps
- [ ] `fundamentals.data_as_of` shows period end date (e.g. "2025-12-31")
- [ ] `fundamentals.fetched_at` shows current UTC timestamp
- [ ] `quote.fetched_at` shows current UTC timestamp
- [ ] `quote.source` shows "apter_internal"

### 4. Forward Estimates
- [ ] `forward.available` == false (internal provider)
- [ ] `forward.unavailable_reason` is non-null
- [ ] `pe_forward_fy1.value` == null
- [ ] `pe_forward_fy1.null_reason` includes "unavailable"
- [ ] `data_quality.stale_flags` includes "no_forward_estimates"

### 5. Staleness Detection
- [ ] Fresh data (period_end within 120 days) → no "fundamentals_old" flag
- [ ] Simulate old data → "fundamentals_old" flag appears
- [ ] Missing fundamental data → null values with reasons

### 6. Cache Behavior
- [ ] First request computes fresh data
- [ ] Second request (within 60s) returns cached data
- [ ] `force_refresh=true` bypasses cache
- [ ] `POST /api/stocks/AAPL/refresh` clears cache for AAPL

### 7. AI Overview Updates
- [ ] `GET /api/stocks/AAPL/ai-overview` includes `data_quality` field
- [ ] `GET /api/stocks/AAPL/ai-overview` includes `data_as_of` field
- [ ] `GET /api/stocks/AAPL/ai-overview` includes `source` field
- [ ] Chat response includes "(TTM)" labels on metrics

## Frontend Verification

### 1. Stock Page Display
- [ ] Header shows price, change, market cap from snapshot
- [ ] Source/session line appears below price
- [ ] Fundamentals panel loads from `/api/stocks/{ticker}/snapshot`

### 2. Metric Labels in UI
- [ ] Each metric row has a colored label badge (TTM, MRQ, Forward FY1, etc.)
- [ ] TTM badges are blue
- [ ] MRQ badges are purple
- [ ] Forward badges are amber
- [ ] 30-Day badges are cyan

### 3. Data As Of Line
- [ ] "Data as of: {date}" visible at bottom of fundamentals panel
- [ ] "Fetched: {datetime}" visible
- [ ] "Source: {provider}" visible

### 4. Staleness Warnings
- [ ] When `fundamentals_old` flag present → amber warning icon appears
- [ ] Forward estimates unavailable → info message shown
- [ ] AI overview shows staleness notice when applicable

### 5. Forward Estimates
- [ ] Forward P/E rows show "N/A" with hover tooltip
- [ ] Info box says "Forward estimates unavailable with current data source"

## Provider Swap Test
To verify the provider abstraction works:
1. Open `Platform/api/app/services/market_data/providers.py`
2. In `get_provider()`, confirm it returns `InternalProvider()`
3. To swap: create a new class implementing `MarketDataProvider`
4. Change `get_provider()` to return your new class
5. All endpoints use the same interface — no other code changes needed

## Commands

### Run Backend Tests
```bash
cd Platform/api
pip install pytest httpx
python -m pytest tests/ -v
```

### Start Backend
```bash
cd Platform/api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Start Frontend
```bash
cd Platform/web
npm install
npm run dev
```

### Test Endpoints Manually
```bash
# Snapshot
curl http://localhost:8000/api/stocks/AAPL/snapshot | python -m json.tool

# Force refresh
curl http://localhost:8000/api/stocks/AAPL/snapshot?force_refresh=true | python -m json.tool

# AI overview
curl http://localhost:8000/api/stocks/AAPL/ai-overview | python -m json.tool

# Cache clear
curl -X POST http://localhost:8000/api/stocks/AAPL/refresh | python -m json.tool
```
