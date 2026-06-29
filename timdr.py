"""
timdr.py — TIMDR evaluator · analizator-giełdowy
Ocenia strategię przez pryzmat metrykowy Λ–τ–ρ i wyznacza emergencję E.

Poprawki v2:
  1. Walidacja znaku drawdown — jeśli ujemne (inna konwencja) → abs()
     (oryginał: dd_n = 1 - min(-0.18, 1) = 1.18 → powyżej 1.0)
  2. Walidacja zakresu wszystkich metryk wejściowych
  3. dd_n gwarantowane ∈ [0, 1]
  4. R_total gwarantowane ∈ [0, 1]
  5. Obsługa brakujących kluczy w config["R"] z bezpiecznymi wartościami domyślnymi
"""

import numpy as np
from typing import Any


def timdr_evaluate(config: dict) -> dict:
    """
    Ocenia strategię na podstawie słownika config.

    config:
        T  — opis pola (np. 'AAPL / 1D')
        I  — dane (DataFrame z sygnałami, może być None)
        M  — modalność (np. 'trend-following')
        It — horyzont czasu (np. '1y')
        R  — dict z metrykami: sharpe, winrate, drawdown

    Zwraca:
        R_total   — wynik łączny ∈ [0, 1]
        E         — klasa emergencji: obiekt / pół-obiekt / szum
        details   — składowe znormalizowane
        warnings  — lista ostrzeżeń walidacyjnych
    """
    warnings_list = []

    R = config.get("R", {})
    if not isinstance(R, dict):
        R = {}
        warnings_list.append("config['R'] nie jest słownikiem — użyto wartości domyślnych")

    # ── Ekstrakcja z wartościami domyślnymi ──────────────────────────────────
    sharpe  = float(R.get("sharpe",   0.0))
    winrate = float(R.get("winrate",  0.0))
    dd      = float(R.get("drawdown", 1.0))

    # ── POPRAWKA 1: walidacja znaku drawdown ─────────────────────────────────
    # compute_metrics() zwraca drawdown jako wartość DODATNIĄ (0.18 = 18% dd)
    # Jeśli ktoś poda ujemne (inna konwencja), bierzemy abs()
    if dd < 0:
        warnings_list.append(
            f"drawdown={dd:.4f} jest ujemny — przyjęto abs({dd:.4f})={abs(dd):.4f}. "
            "Oczekiwana konwencja: wartość dodatnia np. 0.18 = 18% drawdown."
        )
        dd = abs(dd)

    # ── POPRAWKA 2: walidacja zakresów ───────────────────────────────────────
    if not (0.0 <= winrate <= 1.0):
        warnings_list.append(f"winrate={winrate:.4f} poza [0,1] — przycięto do zakresu")
        winrate = max(0.0, min(1.0, winrate))

    if dd > 1.0:
        warnings_list.append(f"drawdown={dd:.4f} > 1.0 — przycięto do 1.0")
        dd = 1.0

    # ── Normalizacja (0–1) ───────────────────────────────────────────────────
    sharpe_n  = float(np.tanh(sharpe))          # ∈ (−1, 1)
    winrate_n = float(winrate)                   # już ∈ [0, 1]
    dd_n      = float(1.0 - min(dd, 1.0))       # ∈ [0, 1] — POPRAWKA 3: min() gwarantuje brak przekroczenia

    # ── Rezonans R_total ─────────────────────────────────────────────────────
    R_total_raw = 0.5 * sharpe_n + 0.3 * winrate_n + 0.2 * dd_n

    # POPRAWKA 4: gwarantuj ∈ [0, 1] — przy bardzo ujemnym sharpe może być < 0
    R_total = float(max(0.0, min(1.0, R_total_raw)))
    if R_total != R_total_raw:
        warnings_list.append(
            f"R_total_raw={R_total_raw:.4f} przycięto do {R_total:.4f}"
        )

    # ── Próg emergencji ──────────────────────────────────────────────────────
    if R_total > 0.55:
        E = "obiekt (strategia stabilna)"
    elif R_total > 0.35:
        E = "pół-obiekt (niestabilna, ale rokująca)"
    else:
        E = "szum (brak emergencji)"

    return {
        "R_total":  R_total,
        "E":        E,
        "details": {
            "sharpe_n":  round(sharpe_n,  6),
            "winrate_n": round(winrate_n, 6),
            "dd_n":      round(dd_n,      6),
        },
        "warnings": warnings_list,
    }
