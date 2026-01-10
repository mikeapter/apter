from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


from pathlib import Path
import sys

def main() -> int:
    try:
        import yfinance as yf
    except ImportError:
        print("Missing yfinance. Install it with:\n  pip install yfinance\n")
        return 2

    repo_root = Path(__file__).resolve().parents[1]  # BotTrader/
    data_dir = repo_root / "Data"
    data_dir.mkdir(parents=True, exist_ok=True)

    out_csv = data_dir / "SPY_daily.csv"

    # Pull enough history to include COVID 2020 and cover 5+ years
    # (2015→today includes 2020 and gives plenty of length for WF)
    df = yf.download("SPY", start="2015-01-01", auto_adjust=False, progress=False)

    if df is None or df.empty:
        print("Download failed or returned no data.")
        return 3

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })

    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index.name = "ts"
    df = df.reset_index()

    # ISO timestamp for your adapter
    df["ts"] = df["ts"].dt.strftime("%Y-%m-%d")

    df.to_csv(out_csv, index=False)
    print(f"Wrote: {out_csv}")
    print(f"Rows: {len(df)}  Range: {df['ts'].iloc[0]} -> {df['ts'].iloc[-1]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())