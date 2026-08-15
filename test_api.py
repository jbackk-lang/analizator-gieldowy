"""
test_api.py — testy end-to-end dla api.py (Flask), przez test_client
(bez realnie uruchomionego serwera / bez sieci).
"""

import json

import pytest

import api as api_module


def _strict_json_parse(raw: str):
    """Parsuje JSON DOKŁADNIE tak restrykcyjnie jak przeglądarkowy
    JSON.parse() - odrzuca dosłowne tokeny NaN/Infinity/-Infinity,
    które standardowy `json.loads` Pythona domyślnie akceptuje jako
    nieformalne rozszerzenie (stąd Bug 7 nie był widoczny w testach,
    które używały zwykłego resp.get_json())."""
    def _reject(token):
        raise ValueError(f"Niedozwolony w JSON token: {token!r}")

    return json.loads(raw, parse_constant=_reject)


@pytest.fixture()
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_index_serwuje_dashboard(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<!DOCTYPE html>" in resp.data
    assert b"Analizator" in resp.data


def test_bug7_odpowiedz_demo_jest_scisle_poprawnym_jsonem(client):
    """Regresja dla Bug 7: przeglądarka zgłaszała
    "Unexpected token 'N', ...'ma_fast':[NaN,NaN,Na'... is not valid JSON".
    Przyczyna: NaN z rolling-window w ma_fast/ma_slow/rsi trafiał do
    odpowiedzi jako dosłowny (nie-standardowy) token `NaN`, którego
    JSON.parse() w przeglądarce nie akceptuje. Ten test parsuje surową
    odpowiedź TAK SAMO restrykcyjnie jak przeglądarka i musi się udać."""
    resp = client.get("/api/demo")
    raw = resp.get_data(as_text=True)
    assert " NaN" not in raw and "[NaN" not in raw and ",NaN" not in raw, (
        "Odpowiedź zawiera dosłowny token NaN - nie jest to poprawny JSON"
    )
    assert "Infinity" not in raw
    data = _strict_json_parse(raw)  # rzuci ValueError, jeśli JSON jest niepoprawny
    assert data["ma_fast"][0] is None  # początek okna rolling -> null, nie NaN
    assert isinstance(data["ma_fast"][-1], float)


def test_demo_zwraca_pelna_analize(client):
    resp = client.get("/api/demo")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["is_demo"] is True
    assert len(data["dates"]) > 200
    assert len(data["dates"]) == len(data["close"])
    assert len(data["dates"]) == len(data["rsi"])
    assert len(data["dates"]) == len(data["equity"])

    rec = data["recommendation"]
    for key in ("action", "signal_value", "price", "sl", "tp", "position_size", "note"):
        assert key in rec, f"brak klucza '{key}' w recommendation (patrz Bug 3/4 w README)"

    timdr = data["timdr"]
    for key in ("R_total", "E", "confidence", "details", "warnings"):
        assert key in timdr, f"brak klucza '{key}' w timdr (patrz Bug 2 w README)"

    metrics = data["metrics"]
    for key in ("sharpe", "winrate", "drawdown", "cagr", "trades"):
        assert key in metrics


def test_analyze_use_demo_true(client):
    resp = client.post("/api/analyze", json={"use_demo": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_demo"] is True
    assert "action" in data["recommendation"]


def test_analyze_live_bez_sieci_daje_czytelny_blad_nie_typeerror(client):
    """W tym środowisku (sandbox bez dostępu do Yahoo Finance) żywe
    zapytanie MUSI zwrócić czytelny błąd JSON (400) z podpowiedzią
    use_demo, a NIE 500/TypeError - to byłby dokładnie Bug 5."""
    resp = client.post("/api/analyze", json={"ticker": "AAPL", "period": "1mo"})
    assert resp.status_code in (400, 200)  # 200 tylko jeśli akurat jest sieć
    data = resp.get_json()
    if resp.status_code == 400:
        assert "error" in data
        assert "show_errors" not in data["error"], "Bug 5 (show_errors) nie powinien już wystąpić"
        assert "hint" in data
        assert "use_demo" in data["hint"]


def test_analyze_bledny_json_nie_wywala_serwera(client):
    resp = client.post("/api/analyze", data="nie-jest-jsonem", content_type="application/json")
    # Flask z silent=True w request.get_json powinien potraktować to
    # jako pusty dict -> spadnie do domyślnego tickera/use_demo=False,
    # co bez sieci da 400, ale serwer nie może rzucić 500.
    assert resp.status_code != 500
