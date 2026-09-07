"""Skaner WIG20 - Hybrydowy Model Multi-Timeframe TIMDR (1d + 1w) z Integracją Sektorową GSF.

Wersja zintegrowana z analityką wielo-interwałową i sektorową osłoną makro.
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


def fetch_gsf_macro_data(period: str = "1y") -> pd.DataFrame:
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
# 3. SILNIK EVALUACJI MULTI-TIMEFRAME TIMDR (1D + 1W)
# ==============================================================================


def calculate_single_tf_timdr(df: pd.DataFrame) -> float:
  """Oblicza skalar TIMDR dla podanej ramki czasowej (df)."""
  if df is None or len(df) < 20:
    return 0.50

  close = df["Close"].squeeze()
  ret = close.pct_change().dropna()

  if ret.empty:
    return 0.50

  sharpe = (ret.mean() / ret.std() * np.sqrt(252)) if ret.std() != 0 else 0
  sharpe_n = 1 / (1 + np.exp(-sharpe))
  winrate_n = (ret > 0).mean()

  cummax = close.cummax()
  dd = (close - cummax) / cummax
  dd_n = 1 + dd.min()

  R_score = 0.40 * sharpe_n + 0.30 * winrate_n + 0.30 * max(0, dd_n)
  return float(R_score)


def timdr_multi_tf_gsf_analyze(
    ticker: str, macro_df: pd.DataFrame, base_gsf: dict
) -> dict | None:
  # 1. Pobieranie ramek 1d oraz 1w
  df_1d = yf.download(
      ticker, period="1y", interval="1d", auto_adjust=True, progress=False
  )
  df_1w = yf.download(
      ticker, period="2y", interval="1wk", auto_adjust=True, progress=False
  )

  if df_1d is None or len(df_1d) < 50 or df_1w is None or len(df_1w) < 15:
    return None

  # 2. Obliczanie pojedynczych skalarów TIMDR
  R_1d = calculate_single_tf_timdr(df_1d)
  R_1w = calculate_single_tf_timdr(df_1w)

  # Wielo-ramowa fuzja (50% Dzienny + 50% Tygodniowy)
  R_multi = 0.50 * R_1d + 0.50 * R_1w

  # 3. Integracja z Sektorowym GSF
  sec_gsf = compute_sectoral_gsf_score(ticker, macro_df, base_gsf)
  R_GSF_sector = sec_gsf["R_GSF_sector"]

  # Hybrydowy Skalar Rezonansu (70% Multi-Timeframe + 30% Sektorowy GSF)
  R_final = float(0.70 * R_multi + 0.30 * R_GSF_sector)

  # 4. Obliczanie ATR (14) z ramki dziennej dla wyznaczenia SL / TP
  close_1d = df_1d["Close"].squeeze()
  high_1d = df_1d["High"].squeeze()
  low_1d = df_1d["Low"].squeeze()

  tr = (
      pd.concat(
          [
              high_1d - low_1d,
              (high_1d - close_1d.shift()).abs(),
              (low_1d - close_1d.shift()).abs(),
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
  last_price = float(close_1d.iloc[-1])

  # 5. Sprawdzenie spójności trendów między interwałami (Alignment Check)
  # Jeśli rozbieżność między 1d a 1w jest większa niż 0.20, zgłaszamy niespójność
  tf_mismatch = abs(R_1d - R_1w) > 0.20

  # Silnik decyzyjny
  if tf_mismatch and R_final > 0.55:
    dec = "TRZYMAJ (DISCORD TF)"
    pos = "50%"
  elif R_final > 0.75:
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
      "R_1d": round(R_1d, 4),
      "R_1w": round(R_1w, 4),
      "R_multi": round(R_multi, 4),
      "R_GSF": round(R_GSF_sector, 4),
      "R_final": round(R_final, 4),
      "decyzja": dec,
      "alokacja": pos,
      "SL": round(last_price - 1.5 * atr, 2),
      "TP": round(last_price + 2.0 * atr, 2),
  }


# ==============================================================================
# 4. GŁÓWNA PĘTLA EXECUTORA SKANERA
# ==============================================================================


def main():
  print("=" * 95)
  print("   SKANER WIG20 (MULTI-TIMEFRAME 1D/1W TIMDR + SEKTOROWY GSF)")
  print("=" * 95)

  print(
      "\n1. Pobieranie danych dla makro-pola GSF (VIX, US10Y, EUR/USD, Ropa,"
      " Miedź)..."
  )
  macro_df = fetch_gsf_macro_data(period="1y")
  base_gsf = compute_base_gsf_score(macro_df)
  print(f" ✓ Bazowy Skalar Pole GSF (R_GSF_base): {base_gsf.get('R_GSF_base')}")

  print(
      "\n2. Rozpoczynam skanowanie wielo-interwałowe walorów indeksu"
      " WIG20...\n"
  )
  results = []

  for t in WIG20:
    try:
      r = timdr_multi_tf_gsf_analyze(t, macro_df, base_gsf)
      if r:
        results.append(r)
        print(
            f"  ✓ {t:<7} | R_1d: {r['R_1d']} | R_1w: {r['R_1w']} | R_final:"
            f" {r['R_final']} | {r['decyzja']} ({r['alokacja']})"
        )
      else:
        print(f"  ⚠️ Pominięcie: {t} (Niewystarczające dane)")
    except Exception as e:
      print(f"  ❌ Błąd przetwarzania dla {t}: {e}")

  if results:
    df_res = pd.DataFrame(results).sort_values("R_final", ascending=False)

    print("\n" + "=" * 105)
    print("=== PODSUMOWANIE SKANOWANIA MULTI-TIMEFRAME WIG20 (1D/1W TIMDR + GSF) ===")
    print("=" * 105)
    print(df_res.to_string(index=False))

    output_file = "wig20_gsf_timdr_scan.csv"
    df_res.to_csv(output_file, index=False)
    print(f"\n Zapisano pełny raport wielo-interwałowy w pliku: {output_file}")
  else:
    print("\n❌ Brak wyników do wyświetlenia.")


if __name__ == "__main__":
  main()
