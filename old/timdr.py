"""
timdr.py — TIMDR evaluator · analizator-giełdowy
Ocenia strategię przez pryzmat metrykowy Λ–τ–ρ, wyznacza emergencję E
oraz generuje dynamiczne wskaźniki ufności i rekomendacji inwestycyjnej.
"""

from typing import Any, Dict
import numpy as np


def timdr_evaluate(config: dict) -> dict:
    """
    Ocenia strategię na podstawie słownika config.

    config:
        T  — opis pola (np. 'AAPL / 1D')
        I  — dane (DataFrame z sygnałami, może być None)
        M  — modalność (np. 'memory-adaptive-fusion')
        It — horyzont czasu (np. '1y')
        R  — dict z metrykami: sharpe, winrate, drawdown

    Zwraca:
        R_total   — wynik łączny ∈ [0, 1]
        E         — klasa emergencji: obiekt / pół-obiekt / szum
        details   — składowe znormalizowane
        warnings  — lista ostrzeżeń walidacyjnych
        confidence— wskaźnik ufności systemu dla rekomendacji [0.0 - 1.0]
        suggested_position_size — sugerowana wielkość pozycji (0.0 do 1.0)
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
    sharpe_n  = float(np.tanh(max(0.0, sharpe)))  # Uporządkowane do [0, 1)
    winrate_n = float(winrate)                    # już ∈ [0, 1]
    dd_n      = float(1.0 - min(dd, 1.0))        # ∈ [0, 1]

    # ── Rezonans R_total ─────────────────────────────────────────────────────
    R_total_raw = 0.5 * sharpe_n + 0.3 * winrate_n + 0.2 * dd_n

    R_total = float(max(0.0, min(1.0, R_total_raw)))
    if R_total != R_total_raw:
        warnings_list.append(
            f"R_total_raw={R_total_raw:.4f} przycięto do {R_total:.4f}"
        )

    # ── Próg emergencji & Poziom ryzyka / Wielkość pozycji ────────────────────
    if R_total > 0.55:
        E = "obiekt (strategia stabilna)"
        confidence = round(R_total, 2)
        position_size = 1.0  # Full position / 100% kapitału alokowanego
    elif R_total > 0.35:
        E = "pół-obiekt (niestabilna, ale rokująca)"
        confidence = round(R_total * 0.7, 2)
        position_size = 0.5  # 50% pozycji (ostrożnie)
    else:
        E = "szum (brak emergencji)"
        confidence = round(R_total * 0.2, 2)
        position_size = 0.0  # NO TRADE — brak handlu na szumie

    return {
        "R_total":  R_total,
        "E":        E,
        "confidence": confidence,
        "suggested_position_size": position_size,
        "details": {
            "sharpe_n":  round(sharpe_n,  6),
            "winrate_n": round(winrate_n, 6),
            "dd_n":      round(dd_n,      6),
        },
        "warnings": warnings_list,
    }


def filter_recommendation_by_timdr(rec: dict, timdr_result: dict) -> dict:
    """
    Modyfikuje rekomendację inwestycyjną w zależności od emergencji TIMDR.
    Zapobiega kupowaniu/sprzedawaniu na sygnałach będących 'szumem'.
    """
    rec_copy = rec.copy()
    e_class = timdr_result["E"]
    pos_size = timdr_result["suggested_position_size"]

    if "szum" in e_class:
        rec_copy["action"] = "NEUTRALNIE / TRZYMAJ (SZUM RYNKOWY)"
        rec_copy["note"] = "Moduł TIMDR wykrył brak stabilnej emergencji (R_total zbyt niskie)."
    elif "pół-obiekt" in e_class and "SILNE" in rec_copy["action"]:
        # Obniżamy agresywność ze względu na pół-obiekt
        rec_copy["action"] = rec_copy["action"].replace("SILNE ", "")
        rec_copy["note"] = "Sygnał obniżony z SILNE do standardowego ze względu na średnią emergencję."
    
    rec_copy["sugerowana_wielkosc_pozycji"] = f"{int(pos_size * 100)}%"
    return rec_copy
