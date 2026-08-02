"""Skaner WIG20 - Hybrydowy Model TIMDR/GIA z Integracją Sektorową GSF (Global Financial System).

Wersja zintegrowana: Jedno-plikowe rozwiązanie z pełną analityką makro,
rezonansu i zarządzania ryzykiem.
"""

from typing import Any, Dict
import numpy as np
import pandas as pd
import yfinance as yf

# ==============================================================================
# 1. KONFIGURACJA SEKTORÓW I DANYCH MAKRORYNKOWYCH (GSF)
# ==============================================================================

GSF_GLOBAL_ASSETS = {
    "VIX": "^VIX",  # Indeks strachu / Zmienność globalna
    "US10Y": "^TNX",  # Rentowność obligacji US 10Y
    "EURUSD": "EURUSD=X",  # Płynność USD / Kurs EUR-USD
    "COPPER": "HG=F",  # Miedź (KGHM)
    "BRENT": "BZ=F",  # Ropa Brent (PKN Orlen)
}

GPW_SECTOR_MAP = {
    "KGH.WA": "MINING_COPPER",
    "PKN.WA": "ENERGY_OIL",
    "PGE.WA": "UTILITIES",
    "TPE.WA": "UTILITIES",
    "PKO.WA": "BANKING",
    "PEO.WA": "BANKING",
    "SPL.WA": "BANKING",
    "MBK.WA": "BANKING",
    "ALR.WA": "BANKING",
    "KRU.WA": "FINANCIAL_SERVICES",
    "ALE.WA": "GENERAL_TECH",
    "CDR.WA": "GENERAL_TECH",
    "DNP.WA": "RETAIL",
    "LPP.WA": "RETAIL",
    "BDX.WA": "CONSTRUCTION",
    "ZAB.WA": "RETAIL",
}

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


# ==============================================================================
# 2. SILNIK GSF (GLOBAL FINANCIAL SYSTEM)
# ==============================================================================


def fetch_gsf_macro_data(period: str = "6mo") -> pd.DataFrame:
  """Pobiera dane rynkowe dla aktywów makroekonomicznych GSF."""
  try:
    data = yf.download(
        list(GSF_GLOBAL_ASSETS.values()),
        period=period,
        interval="1d",
        progress=False,
    )["Close"]
    return data
  except Exception as e:
    print(f"⚠️ Błąd pobierania danych GSF Macro: {e}")
    return pd.DataFrame()


def compute_base_gsf_score(macro_df: pd.DataFrame) -> Dict[str, float]:
  """Oblicza bazowy, globalny skalar spójności pola GSF (R_GSF_base)."""
  if macro_df.empty:
    return {"R_GSF_base": 0.50, "status": "NEUTRAL_FALLBACK"}

  try:
    vix_last = float(macro_df["^VIX"].iloc[-1])
    vix_score = 1.0 / (1.0 + np.exp((vix_last - 20.0) / 4.0))

    eurusd_ret = macro_df["EURUSD=X"].pct_change(20).iloc[-1]
    usd_score = 1.0 / (1.0 + np.exp(-eurusd_ret * 10.0))

    us10y_last = float(macro_df["^TNX"].iloc[-1])
    yield_score = 1.0 / (1.0 + np.exp((us10y_last - 4.2) / 0.5))

    R_GSF_base = float(0.40 * vix_score + 0.35 * usd_score + 0.25 * yield_score)
    R_GSF_base = max(0.0, min(1.0, R_GSF_base))

    return {
        "R_GSF_base": round(R_GSF_base, 4),
        "vix_score": round(float(vix_score), 4),
        "usd_score": round(float(usd_score), 4),
        "yield_score": round(float(yield_score), 4),
    }
  except Exception:
    return {"R_GSF_base": 0.50, "status": "CALCULATION_ERROR"}


def compute_sectoral_gsf_score(
    ticker: str, macro_df: pd.DataFrame, base_gsf: Dict[str, float]
) -> Dict[str, Any]:
  """Wylicza skorygowany skalar R_GSF_sector z uwzględnieniem wag sektorowych dla GPW."""
  R_base = base_gsf.get("R_GSF_base", 0.50)
  sector = GPW_SECTOR_MAP.get(ticker, "GENERAL")

  if macro_df.empty:
    return {"R_GSF_sector": R_base, "sector": sector}

  try:
    copper_ret_20d = macro_df["HG=F"].pct_change(20).iloc[-1]
    copper_score = 1.0 / (1.0 + np.exp(-copper_ret_20d * 8.0))

    brent_ret_20d = macro_df["BZ=F"].pct_change(20).iloc[-1]
    brent_score = 1.0 / (1.0 + np.exp(-brent_ret_20d * 6.0))

    us10y_ret_20d = macro_df["^TNX"].pct_change(20).iloc[-1]
    banking_yield_score = 1.0 / (1.0 + np.exp(-us10y_ret_20d * 5.0))

    if sector == "MINING_COPPER":
      R_sector = (
          0.60 * copper_score
          + 0.20 * base_gsf.get("usd_score", 0.5)
          + 0.20 * R_base
      )
    elif sector == "ENERGY_OIL":
      R_sector = (
          0.55 * brent_score
          + 0.25 * base_gsf.get("vix_score", 0.5)
          + 0.20 * R_base
      )
    elif sector == "BANKING":
      R_sector = (
          0.50 * banking_yield_score
          + 0.30 * base_gsf.get("vix_score", 0.5)
          + 0.20 * R_base
      )
    else:
      R_sector = R_base

    R_sector = max(0.0, min(1.0, float(R_sector)))
    return {"R_GSF_sector": round(R_sector, 4), "sector": sector}

  except Exception:
    return {"R_GSF_sector": R_base, "sector": sector}


# ==============================================================================
# 3. SILNIK ANALIZY LOKALNEJ TIMDR
# ==============================================================================


def timdr_gsf_analyze(
    ticker: str, macro_df: pd.DataFrame, base_gsf: dict, period: str = "1y"
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

  # Metryki lokalne TIMDR
  sharpe = (ret.mean() / ret.std() * np.sqrt(252)) if ret.std() != 0 else 0
  sharpe_n = 1 / (1 + np.exp(-sharpe))
  winrate_n = (ret > 0).mean()

  cummax = close.cummax()
  dd = (close - cummax) / cummax
  dd_n = 1 + dd.min()

  R_local = 0.4 * sharpe_n + 0.3 * winrate_n + 0.3 * max(0, dd_n)

  # Włączenie komponentu sektorowego GSF
  sec_gsf = compute_sectoral_gsf_score(ticker, macro_df, base_gsf)
  R_GSF_sector = sec_gsf["R_GSF_sector"]

  # Hybrydowy Skalar Rezonansu (70% Lokalny TIMDR + 30% Sektorowy GSF)
  R_final = float(0.70 * R_local + 0.30 * R_GSF_sector)

  # Obliczanie ATR (14) dla wyznaczenia SL i TP
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

  if tr.empty:
    return None

  atr = float(tr.iloc[-1])
  last_price = float(close.iloc[-1])

  # Silnik rekomendacyjny i kontroli ryzyka
  if R_final > 0.75:
    dec = "SILNE KUPUJ"
    pos = "100%"
  elif R_final > 0.60:
    dec = "KUPUJ"
    pos = "100%"
  elif R_final > 0.45:
    dec = "TRZYMAJ"
    pos = "50%"
  elif R_final > 0.35:
    dec = "SPRZEDAJ"
    pos = "0%"
  else:
    dec = "SILNE SPRZEDAJ"
    pos = "0%"

  return {
      "ticker": ticker,
      "sektor": sec_gsf["sector"],
      "cena": round(last_price, 2),
      "R_local": round(float(R_local), 4),
      "R_GSF": round(float(R_GSF_sector), 4),
      "R_final": round(float(R_final), 4),
      "decyzja": dec,
      "alokacja": pos,
      "SL": round(last_price - 1.5 * atr, 2),
      "TP": round(last_price + 2.0 * atr, 2),
  }


# ==============================================================================
# 4. GŁÓWNA PĘTLA EXECUTORA SKANERA
# ==============================================================================


def main():
  print("=" * 80)
  print("   SKANER WIG20 (TIMDR / GIA + SEKTOROWY SILNIK GSF)")
  print("=" * 80)

  print("\n1. Pobieranie danych dla makro-pola GSF (VIX, US10Y, EUR/USD, Ropa, Miedź)...")
  macro_df = fetch_gsf_macro_data(period="6mo")
  base_gsf = compute_base_gsf_score(macro_df)
  print(f" ✓ Bazowy Skalar Pole GSF (R_GSF_base): {base_gsf.get('R_GSF_base')}")

  print("\n2. Rozpoczynam skanowanie walorów indeksu WIG20...\n")
  results = []

  for t in WIG20:
    try:
      r = timdr_gsf_analyze(t, macro_df, base_gsf)
      if r:
        results.append(r)
        print(
            f"  ✓ {t:<7} | Sektor: {r['sektor']:<16} | R_final: {r['R_final']} |"
            f" {r['decyzja']} ({r['alokacja']})"
        )
      else:
        print(f"  ⚠️ Pomiędzy: {t} (Niewystarczające dane)")
    except Exception as e:
      print(f"  ❌ Błąd przetwarzania dla {t}: {e}")

  if results:
    df_res = pd.DataFrame(results).sort_values("R_final", ascending=False)

    print("\n" + "=" * 95)
    print("=== PODSUMOWANIE SKANOWANIA WIG20 (TIMDR + GSF SEKTOROWY) ===")
    print("=" * 95)
    print(df_res.to_string(index=False))

    output_file = "wig20_gsf_timdr_scan.csv"
    df_res.to_csv(output_file, index=False)
    print(f"\n Zapisano pełny raport w pliku: {output_file}")
  else:
    print("\n❌ Brak wyników do wyświetlenia.")


if __name__ == "__main__":
  main()
