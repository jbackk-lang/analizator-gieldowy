"""
api.py — Analizator giełdowy + TIMDR, lokalne REST API + dashboard
======================================================================
Serwer Flask udostępniający:
  GET  /                 -> dashboard (static/dashboard.html)
  GET  /api/health       -> healthcheck API
  GET  /api/demo         -> wbudowany syntetyczny zestaw OHLCV (demo_data.csv)
  POST /api/analyze      -> pełna analiza (ticker+period przez yfinance,
                             albo csv_path, albo dane OHLCV wysłane wprost)

Uruchomienie: `python api.py` (albo `run.bat`), potem
http://127.0.0.1:5000

WAŻNE: pobieranie żywych danych przez yfinance wymaga działającego
dostępu do internetu na komputerze, na którym uruchamiasz to API - w
sandboksie, w którym budowano to repo, Yahoo Finance był zablokowany na
poziomie sieci, więc do weryfikacji użyto dołączonego demo_data.csv
(syntetyczne dane, jawnie oznaczone - patrz README.md). Na Twoim
komputerze /api/analyze z samym tickerem powinno pociągnąć prawdziwe
dane, jeśli masz dostęp do internetu.
"""

import math
import os
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from core.timdr import timdr_evaluate, filter_recommendation_by_timdr
from data.loader import load_ohlc
from models.backtest import backtest_signals, compute_metrics
from models.signals import memory_adaptive_fused_signal

app = Flask(__name__, static_folder="static", static_url_path="")

DEMO_CSV = os.path.join(os.path.dirname(__file__), "demo_data.csv")


def _clean_json(obj):
    """
    POPRAWKA (bug #7, zgłoszony przez użytkownika: "Unexpected token 'N',
    ...'ma_fast':[NaN,NaN,Na'... is not valid JSON").

    Oryginalna próba naprawy w run_full_analysis() używała
    `series.where(series.notna(), None)` żeby zamienić NaN na None przed
    wysłaniem do przeglądarki. To NIE działa: pandas Series o dtype
    float64 nie może przechowywać Pythonowego None - `.where(..., None)`
    ciągle zwraca float64 z powrotem skonwertowanym na NaN (potwierdzone
    empirycznie). `.tolist()` daje więc listę Pythonowych `float('nan')`,
    a `json.dumps` (używany przez Flask `jsonify`, `allow_nan=True`
    domyślnie) serializuje to jako DOSŁOWNY token `NaN` w JSON-ie - co
    jest zgodne z rozszerzeniem Pythona, ale NIEZGODNE z RFC 8259 i
    JSON.parse() w przeglądarce, które rzuca dokładnie zaobserwowany
    błąd. Występowało to dla realnych tickerów (np. EURPLN=X), bo
    wskaźniki ma_fast/ma_slow/rsi mają NaN na początku okna (rolling).

    Naprawiono: ta funkcja rekurencyjnie przechodzi cały wynik i zamienia
    float('nan')/float('inf')/float('-inf') na Pythonowy None PO
    konwersji do zwykłych list/dictów, tuż przed jsonify - to działa
    niezależnie od dtype źródłowego obiektu pandas/numpy.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_json(v) for v in obj]
    return obj


def calculate_atr(df: pd.DataFrame, window: int = 14) -> float:
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window).mean().iloc[-1]
    return float(atr) if not np.isnan(atr) else (float(df["Close"].iloc[-1]) * 0.02)


def generate_raw_recommendation(df: pd.DataFrame, signal_col: str = "signal_memory_adaptive") -> dict:
    last_row = df.iloc[-1]
    last_signal = float(last_row[signal_col])
    current_price = float(last_row["Close"])
    atr = calculate_atr(df)

    if last_signal >= 0.75:
        action, sl, tp = "SILNE KUPUJ (STRONG BUY)", current_price - 1.5 * atr, current_price + 3.0 * atr
    elif 0.2 < last_signal < 0.75:
        action, sl, tp = "KUPUJ (BUY)", current_price - 1.5 * atr, current_price + 2.5 * atr
    elif -0.2 <= last_signal <= 0.2:
        action, sl, tp = "NEUTRALNIE / TRZYMAJ (HOLD)", current_price - 2.0 * atr, current_price + 2.0 * atr
    elif -0.75 < last_signal < -0.2:
        action, sl, tp = "SPRZEDAJ (SELL)", current_price + 1.5 * atr, current_price - 2.5 * atr
    else:
        action, sl, tp = "SILNE SPRZEDAJ (STRONG SELL)", current_price + 1.5 * atr, current_price - 3.0 * atr

    return {
        "action": action,
        "signal_value": round(last_signal, 4),
        "price": round(current_price, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "atr": round(atr, 2),
    }


def run_full_analysis(ticker: str, df: pd.DataFrame, period: str, interval: str) -> dict:
    df = memory_adaptive_fused_signal(df)
    raw_rec = generate_raw_recommendation(df)
    bt = backtest_signals(df, signal_col="signal_memory_adaptive")
    metrics = compute_metrics(bt)

    config = {"T": f"{ticker} / {interval}", "I": df, "M": "memory-adaptive-fusion", "It": period, "R": metrics}
    timdr_res = timdr_evaluate(config)
    final_rec = filter_recommendation_by_timdr(raw_rec, timdr_res)

    equity = bt["equity"].fillna(1.0)

    result = {
        "ticker": ticker,
        "dates": df.index.strftime("%Y-%m-%d").tolist(),
        "close": df["Close"].round(4).tolist(),
        "ma_fast": df["ma_fast"].round(4).tolist(),
        "ma_slow": df["ma_slow"].round(4).tolist(),
        "rsi": df["rsi"].round(2).tolist(),
        "signal": df["signal_memory_adaptive"].tolist(),
        "equity": equity.round(4).tolist(),
        "recommendation": final_rec,
        "metrics": metrics,
        "timdr": timdr_res,
    }
    # patrz _clean_json() - zamienia NaN/Infinity na None (Bug 7)
    return _clean_json(result)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "dashboard.html")


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"})


@app.route("/api/demo")
def api_demo():
    try:
        df = load_ohlc("DEMO", csv_path=DEMO_CSV)
    except Exception as exc:
        return jsonify({"error": f"nie udalo sie wczytac danych demo: {exc}"}), 500
    result = run_full_analysis("DEMO (dane syntetyczne)", df, period="1y", interval="1d")
    result["is_demo"] = True
    return jsonify(result)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """
    Body (JSON):
      ticker: str          - symbol (np. "AAPL"), wymagany o ile nie ma "csv"/"ohlcv"
      period: str = "1y"   - okres dla yfinance
      interval: str = "1d" - interwal (informacyjnie, yfinance-side)
      use_demo: bool        - jesli true, ignoruje ticker i uzywa demo_data.csv
    """
    body = request.get_json(force=True, silent=True) or {}
    ticker = body.get("ticker", "EURPLN=X")
    period = body.get("period", "1y")
    interval = body.get("interval", "1d")
    use_demo = bool(body.get("use_demo", False))

    try:
        if use_demo:
            df = load_ohlc("DEMO", csv_path=DEMO_CSV)
            label = "DEMO (dane syntetyczne)"
        else:
            df = load_ohlc(ticker, period=period)
            label = ticker
    except Exception as exc:
        return jsonify({
            "error": f"nie udalo sie pobrac danych dla '{ticker}': {exc}",
            "hint": (
                "1) Sprobuj: python -m pip install --upgrade yfinance "
                "(stare wersje dostaja puste dane od Yahoo - ochrona antybotowa). "
                "2) Jesli nadal nie dziala / brak internetu, wyslij {\"use_demo\": true} "
                "zeby zobaczyc dzialanie na danych syntetycznych."
            ),
        }), 400

    if df is None or len(df) < 30:
        return jsonify({"error": f"za malo danych ({0 if df is None else len(df)} wierszy, min. 30)"}), 400

    try:
        result = run_full_analysis(label, df, period=period, interval=interval)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"blad analizy: {exc}"}), 400

    result["is_demo"] = use_demo
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
