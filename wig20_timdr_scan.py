import pandas as pd
import numpy as np
import yfinance as yf

# Aktualna i poprawna lista tickerów z GPW dla indeksu WIG20
WIG20 = [
    "ALE.WA",
    "ALR.WA",
    "BDX.WA",
    "CDR.WA",
    "DNP.WA",
    "KGH.WA",
    "KRU.WA",
    "KTY.WA",
    "LPP.WA",
    "MBK.WA",
    "PEO.WA",
    "PCO.WA",
    "PGE.WA",
    "PKN.WA",
    "PKO.WA",
    "PZU.WA",
    "SPL.WA",
    "TPE.WA",
    "ZAB.WA",
]


def timdr_analyze(ticker: str, period: str = "1y") -> dict | None:
  df = yf.download(
      ticker, period=period, interval="1d", auto_adjust=True, progress=False
  )

  if df is None or len(df) < 50:
    return None

  # Zabezpieczenie przed wielopoziomowym indeksem kolumn (MultiIndex) z yfinance
  close = df["Close"].squeeze()
  high = df["High"].squeeze()
  low = df["Low"].squeeze()

  ret = close.pct_change().dropna()
  if ret.empty:
    return None

  # Metryki finansowe i normalizacja
  sharpe = (ret.mean() / ret.std() * np.sqrt(252)) if ret.std() != 0 else 0
  sharpe_n = 1 / (1 + np.exp(-sharpe))
  winrate_n = (ret > 0).mean()

  cummax = close.cummax()
  dd = (close - cummax) / cummax
  dd_n = 1 + dd.min()

  R_total = 0.4 * sharpe_n + 0.3 * winrate_n + 0.3 * max(0, dd_n)

  # Kalkulacja wskaźnika ATR (14)
  high_low = high - low
  high_close = (high - close.shift()).abs()
  low_close = (low - close.shift()).abs()

  tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
  atr_series = tr.rolling(14).mean().dropna()

  if atr_series.empty:
    return None

  atr = float(atr_series.iloc[-1])
  last_price = float(close.iloc[-1])

  # Mechanika decyzyjna na podstawie rezonansu TIMDR
  if R_total > 0.75:
    dec = "SILNE KUPUJ"
  elif R_total > 0.60:
    dec = "KUPUJ"
  elif R_total > 0.50:
    dec = "TRZYMAJ"
  elif R_total > 0.40:
    dec = "SPRZEDAJ"
  else:
    dec = "SILNE SPRZEDAJ"

  return {
      "ticker": ticker,
      "cena": round(last_price, 2),
      "R_total": round(float(R_total), 4),
      "decyzja": dec,
      "SL": round(last_price - 1.5 * atr, 2),
      "TP": round(last_price + 2.0 * atr, 2),
  }


def main():
  print(" Rozpoczynam skanowanie spółek WIG20...\n")
  results = []

  for t in WIG20:
    try:
      r = timdr_analyze(t)
      if r:
        results.append(r)
        print(f"✓ Sformatowano: {t} | R_total: {r['R_total']} | {r['decyzja']}")
      else:
        print(f"⚠️ Pominiecie {t} (Brak wystarczającej liczby danych)")
    except Exception as e:
      print(f"❌ Błąd przetwarzania {t}: {e}")

  if results:
    df_res = pd.DataFrame(results).sort_values("R_total", ascending=False)

    print("\n" + "=" * 65)
    print("=== PODSUMOWANIE SKANOWANIA WIG20 (TIMDR) ===")
    print("=" * 65)
    print(df_res.to_string(index=False))

    df_res.to_csv("wig20_timdr_scan.csv", index=False)
    print("\n Zapisano pełny raport w pliku: wig20_timdr_scan.csv")
  else:
    print("\n❌ Brak wyników — sprawdź połączenie internetowe.")


if __name__ == "__main__":
  main()