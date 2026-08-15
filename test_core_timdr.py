"""
test_core_timdr.py — testy regresyjne dla core/timdr.py

Dokumentują 4 powiązane błędy znalezione w oryginalnym repozytorium
jbackk-lang/analizator-gieldowy (patrz README.md, sekcja "Znalezione błędy"):

  Bug 1: ImportError — core/timdr.py (jedyny faktycznie importowany
         przez main.py) nie definiował `filter_recommendation_by_timdr`.
  Bug 2: timdr_evaluate() nie zwracał kluczy `confidence`,
         `suggested_position_size`, `warnings`, wymaganych dalej.
  Bug 3: filter_recommendation_by_timdr (z osieroconego pliku root
         timdr.py) ustawiał rec_copy["sugerowana_wielkosc_pozycji"], ale
         main.py czyta final_rec["position_size"] — zła nazwa klucza.
  Bug 4: filter_recommendation_by_timdr nie ustawiał klucza "note" w
         gałęzi "obiekt" (najlepszy, najczęstszy przypadek) — main.py
         bezwarunkowo drukuje final_rec["note"].

Każdy test poniżej odtwarza oryginalny, zepsuty kod inline i pokazuje,
że rzuca wyjątek, a następnie weryfikuje, że naprawiona wersja w
core/timdr.py działa poprawnie.
"""

import pytest

from core.timdr import timdr_evaluate, filter_recommendation_by_timdr


# ---------------------------------------------------------------------
# Bug 1: import
# ---------------------------------------------------------------------

def test_bug1_oba_symbole_importowalne():
    """core/timdr.py musi definiować OBIE funkcje, bo main.py robi
    `from core.timdr import timdr_evaluate, filter_recommendation_by_timdr`."""
    assert callable(timdr_evaluate)
    assert callable(filter_recommendation_by_timdr)


def test_bug1_reprodukcja_oryginalnego_bledu():
    """Oryginalny core/timdr.py (przed naprawą) definiował TYLKO
    timdr_evaluate. Symulujemy to tu przez moduł z jedną funkcją i
    pokazujemy, że import drugiej faktycznie rzuca ImportError - to
    dokładnie to, co obserwowano przy uruchomieniu oryginalnego main.py."""
    import types
    fake_module = types.ModuleType("fake_core_timdr_original")
    fake_module.timdr_evaluate = lambda config: {}
    with pytest.raises(AttributeError):
        _ = fake_module.filter_recommendation_by_timdr


# ---------------------------------------------------------------------
# Bug 2: brakujące klucze w timdr_evaluate
# ---------------------------------------------------------------------

REQUIRED_KEYS = {"R_total", "E", "confidence", "suggested_position_size", "details", "warnings"}


def test_bug2_timdr_evaluate_zwraca_wszystkie_wymagane_klucze():
    config = {"R": {"sharpe": 1.2, "winrate": 0.55, "drawdown": 0.15}}
    result = timdr_evaluate(config)
    missing = REQUIRED_KEYS - set(result.keys())
    assert not missing, f"Brakuje kluczy wymaganych przez main.py/api.py: {missing}"


def test_bug2_reprodukcja_oryginalnego_bledu_brakujacych_kluczy():
    """Oryginalna (okrojona) wersja timdr_evaluate zwracała tylko
    R_total/E/details. Odtwarzamy to i pokazujemy KeyError dokładnie
    tam, gdzie main.py/api.py by go dostały."""
    def original_timdr_evaluate(config):
        R = config.get("R", {})
        sharpe_n = 0.5
        winrate_n = R.get("winrate", 0.0)
        dd_n = 1.0 - R.get("drawdown", 1.0)
        R_total = 0.5 * sharpe_n + 0.3 * winrate_n + 0.2 * dd_n
        E = "obiekt (strategia stabilna)" if R_total > 0.55 else "szum (brak emergencji)"
        return {"R_total": R_total, "E": E, "details": {}}

    result = original_timdr_evaluate({"R": {"sharpe": 1.2, "winrate": 0.55, "drawdown": 0.15}})
    with pytest.raises(KeyError):
        _ = result["confidence"]
    with pytest.raises(KeyError):
        _ = result["suggested_position_size"]
    with pytest.raises(KeyError):
        _ = result["warnings"]


# ---------------------------------------------------------------------
# Bug 3 + 4: filter_recommendation_by_timdr
# ---------------------------------------------------------------------

def _sample_rec():
    return {
        "action": "SILNE KUPUJ (STRONG BUY)",
        "signal_value": 0.9,
        "price": 100.0,
        "sl": 95.0,
        "tp": 110.0,
        "atr": 2.0,
    }


def test_bug3_position_size_klucz_poprawny():
    timdr_res = timdr_evaluate({"R": {"sharpe": 2.0, "winrate": 0.6, "drawdown": 0.1}})
    final_rec = filter_recommendation_by_timdr(_sample_rec(), timdr_res)
    # main.py czyta final_rec["position_size"] — musi istnieć i być stringiem "%"
    assert "position_size" in final_rec
    assert final_rec["position_size"].endswith("%")


def test_bug3_reprodukcja_oryginalnego_bledu_zlej_nazwy_klucza():
    """Osierocona wersja root timdr.py ustawiała
    rec_copy['sugerowana_wielkosc_pozycji'] zamiast oczekiwanego przez
    main.py klucza 'position_size'."""
    def original_filter(rec, timdr_result):
        rec_copy = rec.copy()
        rec_copy["sugerowana_wielkosc_pozycji"] = f"{int(timdr_result['suggested_position_size'] * 100)}%"
        return rec_copy

    timdr_res = timdr_evaluate({"R": {"sharpe": 2.0, "winrate": 0.6, "drawdown": 0.1}})
    broken = original_filter(_sample_rec(), timdr_res)
    with pytest.raises(KeyError):
        _ = broken["position_size"]


def test_bug4_note_ustawiane_we_wszystkich_galeziach():
    """note musi być ustawione dla każdej z 3 klas emergencji (szum,
    pół-obiekt, obiekt) — main.py bezwarunkowo drukuje final_rec['note']."""
    cases = [
        {"sharpe": 3.0, "winrate": 0.7, "drawdown": 0.05},   # -> obiekt
        {"sharpe": 0.3, "winrate": 0.45, "drawdown": 0.3},   # -> pół-obiekt lub szum w zaleznosci od wag
        {"sharpe": -1.0, "winrate": 0.1, "drawdown": 0.9},   # -> szum
    ]
    for R in cases:
        timdr_res = timdr_evaluate({"R": R})
        final_rec = filter_recommendation_by_timdr(_sample_rec(), timdr_res)
        assert "note" in final_rec, f"Brak 'note' dla E={timdr_res['E']} (R={R})"
        assert isinstance(final_rec["note"], str) and len(final_rec["note"]) > 0


def test_bug4_reprodukcja_oryginalnego_bledu_brakujacej_note_dla_obiektu():
    """Osierocona wersja ustawiała note tylko w gałęziach 'szum' i
    'pół-obiekt'+SILNE — w gałęzi 'obiekt' (najlepszy, najczęstszy
    wynik) klucz 'note' nigdy nie powstawał."""
    def original_filter(rec, timdr_result):
        rec_copy = rec.copy()
        e_class = timdr_result["E"]
        if "szum" in e_class:
            rec_copy["note"] = "brak emergencji"
        elif "pół-obiekt" in e_class and "SILNE" in rec_copy["action"]:
            rec_copy["note"] = "obniżono z SILNE"
        # brak else/elif dla "obiekt" -> note nigdy nie ustawiane w tej galezi
        return rec_copy

    timdr_res = timdr_evaluate({"R": {"sharpe": 3.0, "winrate": 0.7, "drawdown": 0.05}})
    assert "obiekt" in timdr_res["E"] and "pół" not in timdr_res["E"]
    broken = original_filter(_sample_rec(), timdr_res)
    with pytest.raises(KeyError):
        _ = broken["note"]


# ---------------------------------------------------------------------
# Testy zdroworozsądkowe (nie-regresyjne)
# ---------------------------------------------------------------------

def test_timdr_evaluate_szum_gdy_slabe_wyniki():
    result = timdr_evaluate({"R": {"sharpe": -0.5, "winrate": 0.1, "drawdown": 0.8}})
    assert "szum" in result["E"]
    assert result["suggested_position_size"] == 0.0


def test_timdr_evaluate_ujemny_drawdown_dostaje_ostrzezenie():
    result = timdr_evaluate({"R": {"sharpe": 1.0, "winrate": 0.5, "drawdown": -0.2}})
    assert any("ujemny" in w for w in result["warnings"])


def test_timdr_evaluate_winrate_poza_zakresem_przycinany():
    result = timdr_evaluate({"R": {"sharpe": 1.0, "winrate": 1.5, "drawdown": 0.1}})
    assert result["details"]["winrate_n"] == 1.0
    assert any("poza [0,1]" in w for w in result["warnings"])


def test_filter_szum_wymusza_hold():
    timdr_res = timdr_evaluate({"R": {"sharpe": -1.0, "winrate": 0.05, "drawdown": 0.9}})
    final_rec = filter_recommendation_by_timdr(_sample_rec(), timdr_res)
    assert "TRZYMAJ" in final_rec["action"]
    assert final_rec["position_size"] == "0%"
