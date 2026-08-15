# core/timdr.py — TIMDR evaluator · analizator-giełdowy
#
# POPRAWKA (bug krytyczny - program nie startował): `main.py` robi
#   from core.timdr import timdr_evaluate, filter_recommendation_by_timdr
# ale ten plik (jedyny faktycznie importowany - `core` to pakiet) w
# oryginale definiował TYLKO `timdr_evaluate`. `filter_recommendation_by_timdr`
# istniała wyłącznie w osobnym, nieużywanym pliku `timdr.py` w katalogu
# głównym repo, którego main.py nigdy nie importuje. Zweryfikowano:
# `python3 -c "from core.timdr import timdr_evaluate, filter_recommendation_by_timdr"`
# rzucał `ImportError: cannot import name 'filter_recommendation_by_timdr'`
# - program crashował na pierwszej linijce main.py, przed jakąkolwiek
# analizą.
#
# Drugi, powiązany problem: nawet po naprawie samego importu, oryginalny
# `timdr_evaluate()` w tym pliku zwracał tylko `R_total`, `E`, `details`
# - main.py odwołuje się też do `timdr_res['confidence']` i
# `timdr_res["warnings"]`, a `filter_recommendation_by_timdr` (poniżej)
# potrzebuje `timdr_result["suggested_position_size"]`. Żadnego z tych
# kluczy oryginał nie zwracał - dawałoby to kolejny crash (`KeyError`)
# zaraz po naprawie importu.
#
# Naprawiono: scalono pełniejszą wersję `timdr_evaluate` (z walidacją
# znaku drawdown, zakresu winrate, listą ostrzeżeń, confidence i
# suggested_position_size - z osieroconego pliku root `timdr.py`) z
# konfigurowalnymi wagami/progami z tej wersji (`config["weights"]`,
# `config["thresholds"]`), i dodano `filter_recommendation_by_timdr`.

import numpy as np


def timdr_evaluate(config: dict) -> dict:
    """
    Ocenia strategię na podstawie Sharpe, winrate i drawdown.

    config:
        R          — dict z metrykami: sharpe, winrate, drawdown
        weights    — opcjonalnie {"sharpe":0.5,"winrate":0.3,"dd":0.2}
        thresholds — opcjonalnie {"object":0.55,"semi":0.35}

    Zwraca:
        R_total, E, details, warnings, confidence, suggested_position_size
    """
    warnings_list = []

    R = config.get("R", {})
    if not isinstance(R, dict):
        R = {}
        warnings_list.append("config['R'] nie jest słownikiem — użyto wartości domyślnych")

    sharpe = float(R.get("sharpe", 0.0))
    winrate = float(R.get("winrate", 0.0))
    dd = float(R.get("drawdown", 1.0))

    if dd < 0:
        warnings_list.append(
            f"drawdown={dd:.4f} jest ujemny — przyjęto abs({dd:.4f})={abs(dd):.4f}. "
            "Oczekiwana konwencja: wartość dodatnia np. 0.18 = 18% drawdown."
        )
        dd = abs(dd)

    if not (0.0 <= winrate <= 1.0):
        warnings_list.append(f"winrate={winrate:.4f} poza [0,1] — przycięto do zakresu")
        winrate = max(0.0, min(1.0, winrate))

    if dd > 1.0:
        warnings_list.append(f"drawdown={dd:.4f} > 1.0 — przycięto do 1.0")
        dd = 1.0

    sharpe_n = float(np.tanh(max(0.0, sharpe)))
    winrate_n = float(winrate)
    dd_n = float(1.0 - min(dd, 1.0))

    weights = config.get("weights", {"sharpe": 0.5, "winrate": 0.3, "dd": 0.2})
    R_total_raw = weights["sharpe"] * sharpe_n + weights["winrate"] * winrate_n + weights["dd"] * dd_n

    R_total = float(max(0.0, min(1.0, R_total_raw)))
    if R_total != R_total_raw:
        warnings_list.append(f"R_total_raw={R_total_raw:.4f} przycięto do {R_total:.4f}")

    thresholds = config.get("thresholds", {"object": 0.55, "semi": 0.35})

    if R_total > thresholds["object"]:
        E = "obiekt (strategia stabilna)"
        confidence = round(R_total, 2)
        position_size = 1.0
    elif R_total > thresholds["semi"]:
        E = "pół-obiekt (niestabilna, ale rokująca)"
        confidence = round(R_total * 0.7, 2)
        position_size = 0.5
    else:
        E = "szum (brak emergencji)"
        confidence = round(R_total * 0.2, 2)
        position_size = 0.0

    return {
        "R_total": R_total,
        "E": E,
        "confidence": confidence,
        "suggested_position_size": position_size,
        "details": {
            "sharpe_n": round(sharpe_n, 6),
            "winrate_n": round(winrate_n, 6),
            "dd_n": round(dd_n, 6),
        },
        "warnings": warnings_list,
    }


def filter_recommendation_by_timdr(rec: dict, timdr_result: dict) -> dict:
    """
    Modyfikuje rekomendację inwestycyjną w zależności od emergencji TIMDR.
    Zapobiega kupowaniu/sprzedawaniu na sygnałach będących "szumem".
    """
    rec_copy = rec.copy()
    e_class = timdr_result["E"]
    pos_size = timdr_result["suggested_position_size"]

    if "szum" in e_class:
        rec_copy["action"] = "NEUTRALNIE / TRZYMAJ (SZUM RYNKOWY)"
        rec_copy["note"] = "Moduł TIMDR wykrył brak stabilnej emergencji (R_total zbyt niskie)."
    elif "pół-obiekt" in e_class and "SILNE" in rec_copy["action"]:
        rec_copy["action"] = rec_copy["action"].replace("SILNE ", "")
        rec_copy["note"] = "Sygnał obniżony z SILNE do standardowego ze względu na średnią emergencję."
    elif "obiekt" in e_class:
        rec_copy["note"] = "Sygnał wspierany stabilną emergencją TIMDR (R_total powyżej progu)."
    else:
        rec_copy["note"] = "Emergencja pół-obiekt — sygnał utrzymany, zalecana ostrożność."

    rec_copy["position_size"] = f"{int(pos_size * 100)}%"
    return rec_copy
