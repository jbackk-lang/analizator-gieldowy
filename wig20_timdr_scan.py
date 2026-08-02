import numpy as np
import pandas as pd
import yfinance as yf

# Import mostu GSF
from src.core.gsf_bridge import compute_gsf_field_score

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


def timdr_gsf_analyze(
    ticker: str, gsf_data: dict, period: str = "1y"
) -> dict | None:
  df = yf.download(
      ticker, period=period, interval="1d", auto_adjust=True, progress=False
  )

  if df is None or len(df) < 50:
    return None

  close = df["Close"].squeeze()
  high = df["High"].squeeze()
  low = df["Low"].squeeze()

  ret = close.pct_change().dropna()
  if ret.empty:
    return None

  # Lokalny skalar TIMDR
  sharpe = (ret.mean() / ret.std() * np.sqrt(252)) if ret.std() != 0 else 0
  sharpe_n = 1 / (1 + np.exp(-sharpe))
  winrate_n = (ret > 0).mean()
  cummax = close.cummax()
  dd = (close - cummax) / cummax
  dd_n = 1 + dd.min()

  R_local = 0.4 * sharpe_n + 0.3 * winrate_n + 0.3 * max(0, dd_n)

  # --- INTEGRACJA GSF ---
  R_GSF = gsf_data.get("R_GSF", 0.5)

  # Hybrydowy Skalar Rezonansu (Global 30% + Local 70%)
  R_final = float(0.70 * R_local + 0.30 * R_GSF)

  # Kalkulacja ATR (14)
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
      .dropna()
  )

  atr = float(tr.iloc[-1])
  last_price = float(close.iloc[-1])

  # Decyzja Inwestycyjna z Uwzględnieniem Pola GSF
  if gsf_data.get("status") == "GLOBAL_RISK_OFF" and R_final < 0.60:
    dec = "TRZYMAJ (BLOKADA GSF)"
    position = "0%"
  elif R_final > 0.75:
    dec = "SILNE KUPUJ"
    position = "100%"
  elif R_final > 0.60:
    dec = "KUPUJ"
    position = "100%"
  elif R_final > 0.45:
    dec = "TRZYMAJ"
    position = "50%"
  else:
    dec = "SPRZEDAJ"
    position = "0%"

  return {
      "ticker": ticker,
      "cena": round(last_price, 2),
      "R_local": round(float(R_local), 4),
      "R_GSF": round(float(R_GSF), 4),
      "R_final": round(float(R_final), 4),
      "decyzja": dec,
      "pozycja": position,
      "SL": round(last_price - 1.5 * atr, 2),
      "TP": round(last_price + 2.0 * atr, 2),
  }


def main():
  print("=== URUCHAMIANIE INTEGRACJI TIMDR + GSF ===")
  print("1. Pobieranie parametrów pola globalnego GSF...")

  gsf_data = compute_gsf_field_score()
  print(f" Stan Pola GSF: {gsf_data['status']} | R_GSF = {gsf_data['R_GSF']}\n")

  print("2. Skanowanie walorów WIG20...")
  results = []
  for t in WIG20:
    try:
      r = timdr_gsf_analyze(t, gsf_data)
      if r:
        results.append(r)
    except Exception as e:
      print(f"❌ Błąd dla {t}: {e}")

  if results:
    df_res = pd.DataFrame(results).sort_values("R_final", ascending=False)
    print("\n" + "=" * 80)
    print("=== PODSUMOWANIE INTEGRACJI GSF + TIMDR (WIG20) ===")
    print("=" * 80)
    print(df_res.to_string(index=False))
    df_res.to_csv("wig20_gsf_timdr_scan.csv", index=False)
    print("\n Zapisano raport w pliku: wig20_gsf_timdr_scan.csv")


if __name__ == "__main__":
  main()
