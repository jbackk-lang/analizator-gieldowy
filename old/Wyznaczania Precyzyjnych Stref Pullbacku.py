import numpy as np
import pandas as pd
import yfinance as yf

BANKING_TICKERS = ["PKO.WA", "PEO.WA", "SPL.WA", "MBK.WA", "ALR.WA"]


def calculate_entry_zones(tickers):
  results = []
  for t in tickers:
    df = yf.download(t, period="6mo", interval="1d", progress=False)
    if df.empty:
      continue

    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()

    # Wyznaczenie ATR(14) i EMA(20)
    tr = (
        pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        )
        .max(axis=1)
        .rolling(14)
        .mean()
    )

    atr = float(tr.iloc[-1])
    ema20 = float(close.ewm(span=20).mean().iloc[-1])
    last_close = float(close.iloc[-1])

    # Optymalna strefa wejścia (korekta do EMA20 / wsparcia ATR)
    entry_opt = max(ema20, last_close - 0.8 * atr)
    sl = entry_opt - 1.5 * atr
    tp = entry_opt + 2.5 * atr
    rr = (tp - entry_opt) / (entry_opt - sl)

    results.append({
        "Ticker": t,
        "Cena": round(last_close, 2),
        "Optymalne Wejście": round(entry_opt, 2),
        "SL": round(sl, 2),
        "TP": round(tp, 2),
        "R/R Ratio": round(rr, 2),
    })

  return pd.DataFrame(results)


# Uruchomienie kalkulatora wejść:
# print(calculate_entry_zones(BANKING_TICKERS))
