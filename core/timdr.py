# src/core/timdr.py
# ------------------------------------------------------------
#  KOT SCHRÖDINGERA W TIMDR
#
#  Strategia przed oceną (przed backtestem i TIMDR) istnieje
#  w stanie superpozycji:
#      - jest dobra i zła,
#      - działa i nie działa,
#      - ma rezonans i nie ma rezonansu.
#
#  To jest dokładnie kot Schrödingera:
#      konfiguracja sygnału = funkcja falowa,
#      modalności M = superpozycja stanów,
#      pomiar = backtest + metryki,
#      kolaps = E (emergencja obiektu).
#
#  TIMDR pełni rolę mechanizmu kolapsu:
#      R_total > próg  → strategia staje się OBIEKTEM,
#      R_total < próg  → strategia pozostaje SZUMEM.
#
#  Dopiero ocena TIMDR "otwiera pudełko".
# ------------------------------------------------------------

# core/timdr.py — poprawiona wersja TIMDR dla analizator-gieldowy

import numpy as np

def timdr_evaluate(config: dict) -> dict:
    """
    Ocena strategii na podstawie Sharpe, winrate i drawdown.
    Zwraca R_total, klasę emergencji E oraz szczegóły normalizacji.
    """

    metrics = config.get("R") or {}

    sharpe  = float(metrics.get("sharpe",   0.0))
    winrate = float(metrics.get("winrate",  0.0))
    dd_raw  = float(metrics.get("drawdown", 1.0))
    dd      = abs(dd_raw)  # normalizacja znaku

    sharpe_n  = float(np.tanh(sharpe))
    winrate_n = max(0.0, min(1.0, winrate))
    dd_n      = 1.0 - min(dd, 1.0)

    weights = config.get("weights", {"sharpe": 0.5, "winrate": 0.3, "dd": 0.2})
    R_total = (
        weights["sharpe"]  * sharpe_n +
        weights["winrate"] * winrate_n +
        weights["dd"]      * dd_n
    )

    thresholds = config.get("thresholds", {"object": 0.55, "semi": 0.35})

    if R_total > thresholds["object"]:
        E = "obiekt (strategia stabilna)"
    elif R_total > thresholds["semi"]:
        E = "pół-obiekt (niestabilna, ale rokująca)"
    else:
        E = "szum (brak emergencji)"

    return {
        "R_total": R_total,
        "E": E,
        "details": {
            "sharpe_n":  sharpe_n,
            "winrate_n": winrate_n,
            "dd_n":      dd_n,
        },
    }

