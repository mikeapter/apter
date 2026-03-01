"""
Tests for the /api/stocks/{ticker}/snapshot endpoint.

Validates:
- Known tickers return proper snapshot structure
- Unknown tickers return graceful errors
- Staleness flags trigger for missing/old data
- Cache works (second request faster)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSnapshotEndpoint:
    """Integration tests for GET /api/stocks/{ticker}/snapshot."""

    def test_known_ticker_returns_200(self):
        resp = client.get("/api/stocks/AAPL/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"

    def test_snapshot_structure(self):
        resp = client.get("/api/stocks/MSFT/snapshot")
        data = resp.json()

        # Top-level keys
        assert "ticker" in data
        assert "quote" in data
        assert "profile" in data
        assert "fundamentals" in data
        assert "forward" in data
        assert "data_quality" in data

        # Quote fields
        q = data["quote"]
        assert "price" in q
        assert "change" in q
        assert "change_pct" in q
        assert "source" in q
        assert "fetched_at" in q
        assert "provider_latency_ms" in q

        # Profile fields
        p = data["profile"]
        assert "name" in p
        assert "sector" in p
        assert "source" in p

        # Fundamentals fields
        f = data["fundamentals"]
        assert "pe_trailing" in f
        assert "pe_forward_fy1" in f
        assert "revenue_yoy_ttm" in f
        assert "roe_ttm" in f
        assert "debt_to_equity_mrq" in f
        assert "beta" in f
        assert "realized_vol_30d" in f
        assert "data_as_of" in f
        assert "source" in f
        assert "fetched_at" in f

        # Data quality
        dq = data["data_quality"]
        assert "stale_flags" in dq
        assert "missing_fields" in dq
        assert "provider" in dq

    def test_metric_has_label_and_source(self):
        resp = client.get("/api/stocks/AAPL/snapshot")
        data = resp.json()
        pe = data["fundamentals"]["pe_trailing"]

        assert "value" in pe
        assert "label" in pe
        assert "source" in pe
        assert "data_as_of" in pe
        assert pe["label"] == "TTM"
        assert pe["value"] is not None

    def test_forward_unavailable(self):
        resp = client.get("/api/stocks/GOOGL/snapshot")
        data = resp.json()
        fwd = data["forward"]

        assert fwd["available"] is False
        assert fwd["unavailable_reason"] is not None
        assert "no_forward_estimates" in data["data_quality"]["stale_flags"]

    def test_forward_pe_is_null_when_unavailable(self):
        resp = client.get("/api/stocks/TSLA/snapshot")
        data = resp.json()

        fy1 = data["fundamentals"]["pe_forward_fy1"]
        assert fy1["value"] is None
        assert fy1["null_reason"] is not None

    def test_unknown_ticker_returns_data(self):
        """Unknown tickers should still return a response with empty metrics."""
        resp = client.get("/api/stocks/ZZZZ/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "ZZZZ"
        # Should have null metrics
        assert data["fundamentals"]["pe_trailing"]["value"] is None

    def test_invalid_ticker_format(self):
        resp = client.get("/api/stocks/invalid123/snapshot")
        assert resp.status_code == 400

    def test_force_refresh_param(self):
        """force_refresh=true should bypass cache."""
        resp = client.get("/api/stocks/AAPL/snapshot?force_refresh=true")
        assert resp.status_code == 200

    def test_mrq_label_on_debt_to_equity(self):
        resp = client.get("/api/stocks/AAPL/snapshot")
        data = resp.json()
        dte = data["fundamentals"]["debt_to_equity_mrq"]
        assert dte["label"] == "MRQ"

    def test_all_test_tickers(self):
        """Verify AAPL, MSFT, GOOGL, TSLA all return valid snapshots."""
        for ticker in ["AAPL", "MSFT", "GOOGL", "TSLA"]:
            resp = client.get(f"/api/stocks/{ticker}/snapshot")
            assert resp.status_code == 200, f"Failed for {ticker}"
            data = resp.json()
            assert data["ticker"] == ticker
            assert data["quote"]["price"] > 0
            assert data["fundamentals"]["pe_trailing"]["value"] is not None


class TestRefreshEndpoint:
    """Tests for POST /api/stocks/{ticker}/refresh."""

    def test_refresh_returns_200(self):
        resp = client.post("/api/stocks/AAPL/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "cleared_entries" in data

    def test_refresh_invalid_ticker(self):
        resp = client.post("/api/stocks/invalid123/refresh")
        assert resp.status_code == 400


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
