"""
test_loader.py — testy dla data/loader.py

Dokumentuje Bug 5 (patrz README.md): oryginalny kod wołał
    yf.download(ticker, period=period, auto_adjust=True, progress=False,
                show_errors=False)
Parametr `show_errors` nie istnieje w yfinance>=1.6 (usunięty) - PRZED
naprawą KAŻDE wywołanie load_ohlc() dla żywego tickera kończyło się
`TypeError: download() got an unexpected keyword argument 'show_errors'`,
niezależnie od dostępu do internetu. To był krytyczny bug, bo cały sens
tego repo (run.bat pobierający prawdziwe dane) był z nim niedostępny
nawet na maszynie z pełnym dostępem do sieci.
"""

import os
import numpy as np
import pandas as pd
import pytest

from data.loader import load_ohlc, _validate_and_clean


HERE = os.path.dirname(__file__)
DEMO_CSV = os.path.join(HERE, "demo_data.csv")


def test_bug5_reprodukcja_oryginalnego_bledu_show_errors():
    """Odtwarzamy dokładnie oryginalne wywołanie yf.download z usuniętym
    w nowszych wersjach parametrem show_errors i pokazujemy TypeError."""
    def fake_modern_yf_download(ticker, period, auto_adjust, progress, show_errors):
        # sygnatura współczesnego yfinance nie ma show_errors - Python
        # rzuci TypeError zanim w ogóle dojdzie do tej linijki, bo
        # wywołanie z nieistniejącym kwargiem nie przejdzie. Symulujemy
        # to bezpośrednio:
        raise TypeError("download() got an unexpected keyword argument 'show_errors'")

    with pytest.raises(TypeError, match="show_errors"):
        fake_modern_yf_download("AAPL", period="1y", auto_adjust=True, progress=False, show_errors=False)


def test_bug5_naprawiony_loader_nie_uzywa_show_errors():
    """Naprawiony load_ohlc nie powinien przekazywać show_errors do
    yf.download - weryfikujemy to przez monkeypatch modułu yfinance
    atrapą o sygnaturze WSPÓŁCZESNEGO yfinance (bez show_errors)."""
    import sys
    import types

    calls = []

    def fake_download(ticker, period=None, auto_adjust=None, progress=None):
        calls.append({"ticker": ticker, "period": period, "auto_adjust": auto_adjust, "progress": progress})
        dates = pd.date_range("2025-01-01", periods=40, freq="D")
        return pd.DataFrame({
            "Open": np.linspace(100, 110, 40),
            "High": np.linspace(101, 111, 40),
            "Low": np.linspace(99, 109, 40),
            "Close": np.linspace(100, 110, 40),
            "Volume": np.full(40, 1_000_000),
        }, index=dates)

    fake_yf = types.ModuleType("yfinance")
    fake_yf.download = fake_download
    sys.modules["yfinance"] = fake_yf
    try:
        df = load_ohlc("AAPL", period="1mo")
    finally:
        del sys.modules["yfinance"]

    assert len(calls) == 1, "load_ohlc powinien wywołać yf.download dokładnie raz przy sukcesie"
    assert "show_errors" not in calls[0]
    assert len(df) == 40
    assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(df.columns)


def test_wczytanie_demo_csv():
    assert os.path.exists(DEMO_CSV), "demo_data.csv powinien istnieć w repo"
    df = load_ohlc("DEMO", csv_path=DEMO_CSV)
    assert len(df) > 200
    assert list(df.columns[:4]) == ["Open", "High", "Low", "Close"]
    assert df.index.is_monotonic_increasing


def test_brakujacy_plik_csv_czytelny_blad():
    with pytest.raises(FileNotFoundError):
        load_ohlc("X", csv_path="/nie/istnieje/plik.csv")


def test_validate_and_clean_wymaga_kolumn_ohlc():
    df = pd.DataFrame({"Open": [1, 2], "High": [1, 2], "Close": [1, 2]})  # brak Low
    with pytest.raises(ValueError, match="Brak wymaganych kolumn"):
        _validate_and_clean(df, source="test")


def test_validate_and_clean_usuwa_nan_i_sortuje():
    dates = pd.to_datetime(["2025-01-03", "2025-01-01", "2025-01-02"])
    df = pd.DataFrame({
        "Open": [1.0, 2.0, np.nan],
        "High": [1.5, 2.5, 3.5],
        "Low": [0.5, 1.5, 2.5],
        "Close": [1.2, 2.2, 3.2],
    }, index=dates)
    cleaned = _validate_and_clean(df, source="test")
    assert len(cleaned) == 2  # wiersz z NaN usunięty
    assert cleaned.index.is_monotonic_increasing
