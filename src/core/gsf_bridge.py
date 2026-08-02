"""GSF Bridge Module - Integration between Global Financial System (GSF) field

and local TIMDR Analyzer.
"""

from typing import Dict
import numpy as np
import pandas as pd
import yfinance as yf

# Globalne aktywa bazowe określające fazę pola GSF
GSF_GLOBAL_ASSETS = {
    "VIX": "^VIX",  # Indeks strachu / zmienność
    "US10Y": "^TNX",  # Rentowność obligacji US 10-Year
    "EURUSD": "EURUSD=X",  # Dolarowy wskaźnik płynności
    "COPPER": "HG=F",  # Miedź (Barometr przemysłowy)
}


def compute_gsf_field_score(period: str = "6mo") -> Dict[str, float]:
  """Pobiera dane makro i oblicza spójność pola GSF (R_GSF).

  Returns:
      Dict zawierający R_GSF, poziom ryzyka oraz składowe pola.
  """
  try:
    data = yf.download(
        list(GSF_GLOBAL_ASSETS.values()),
        period=period,
        interval="1d",
        progress=False,
    )["Close"]

    if data.empty:
      return {"R_GSF": 0.5, "status": "NEUTRAL_FALLBACK"}

    # 1. Ocena VIX (Reżim strachu)
    vix_last = float(data["^VIX"].iloc[-1])
    vix_score = 1.0 / (1.0 + np.exp((vix_last - 20.0) / 4.0))

    # 2. Dynamika EUR/USD (Płynność dolara)
    eurusd_ret = data["EURUSD=X"].pct_change(20).iloc[-1]
    usd_score = 1.0 / (1.0 + np.exp(-eurusd_ret * 10.0))

    # 3. Miedź / Przemysł (Popyt globalny)
    copper_ret = data["HG=F"].pct_change(20).iloc[-1]
    copper_score = 1.0 / (1.0 + np.exp(-copper_ret * 8.0))

    # Aggregated GSF Field Score (Ważone pole makro)
    R_GSF = float(0.4 * vix_score + 0.3 * usd_score + 0.3 * copper_score)
    R_GSF = max(0.0, min(1.0, R_GSF))

    if R_GSF > 0.60:
      status = "GLOBAL_RISK_ON"
    elif R_GSF >= 0.40:
      status = "GLOBAL_NEUTRAL"
    else:
      status = "GLOBAL_RISK_OFF"

    return {
        "R_GSF": round(R_GSF, 4),
        "status": status,
        "vix_score": round(float(vix_score), 4),
        "usd_score": round(float(usd_score), 4),
        "copper_score": round(float(copper_score), 4),
    }

except Exception as e:
  return {"R_GSF": 0.50, "status": f"ERROR_{str(e)}"}
