# Analizator Giełdowy + TIMDR — API i Dashboard

Fork/naprawiona wersja [jbackk-lang/analizator-gieldowy](https://github.com/jbackk-lang/analizator-gieldowy):
sygnał MA-crossover + RSI (pamięć adaptacyjna), backtest, ocena TIMDR
(Λ–τ–ρ → R_total/E/confidence) i moduł rekomendacji SL/TP, opakowane w
lokalne REST API (Flask) + dashboard w przeglądarce.

**Status: 25/25 testów przechodzi, 7 błędów znalezionych i naprawionych.**

## Uruchomienie

```
run.bat
```

Zainstaluje zależności i uruchomi `http://127.0.0.1:5000` w przeglądarce.
Dashboard startuje domyślnie na **danych demo** (przycisk "🎲 Dane demo").
Żeby pobrać prawdziwe dane, wpisz ticker i kliknij "▶ Analizuj (żywe dane)"
— wymaga to działającego dostępu do internetu na Twoim komputerze.

## Dlaczego dane demo, a nie żywe, w tym repo

To repozytorium zbudowano i zweryfikowano w środowisku (sandbox), w
którym dostęp do zewnętrznych API danych rynkowych (Yahoo Finance i
inne) jest zablokowany na poziomie sieci. Dlatego cała weryfikacja
poniżej używa **jawnie oznaczonych danych syntetycznych**
(`demo_data.csv`, wygenerowanych przez `generate_demo_csv.py` metodą
geometrycznego ruchu Browna, z wstrzykniętym trendem spadkowym dni
120–150) — nigdy nie są przedstawiane jako prawdziwe dane rynkowe.
`/api/analyze` bez `use_demo:true` normalnie próbuje pobrać żywe dane
przez `yfinance` — to zadziała na komputerze z dostępem do internetu
(patrz też Bug 5 niżej, który wcześniej to uniemożliwiał niezależnie od
sieci).

## Znalezione błędy

### Bug 1 (krytyczny) — brakujący import, program nie startował

`main.py` robi:
```python
from core.timdr import timdr_evaluate, filter_recommendation_by_timdr
```
ale oryginalny `core/timdr.py` (jedyny faktycznie importowany —
`core` to pakiet Pythona) definiował **tylko** `timdr_evaluate`.
`filter_recommendation_by_timdr` istniała wyłącznie w osobnym,
nieużywanym pliku `timdr.py` w katalogu głównym repo, którego main.py
nigdy nie importuje.

Zweryfikowano bezpośrednio:
```
$ python3 -c "from core.timdr import timdr_evaluate, filter_recommendation_by_timdr"
ImportError: cannot import name 'filter_recommendation_by_timdr' from 'core.timdr'
```
Program crashował na pierwszej linijce main.py, przed jakąkolwiek analizą.

### Bug 2 (łańcuchowy) — brakujące klucze w wyniku TIMDR

Nawet po naprawieniu importu, oryginalny `timdr_evaluate()` w
`core/timdr.py` zwracał tylko `R_total`, `E`, `details` — a main.py i
`filter_recommendation_by_timdr` odwołują się też do
`timdr_res['confidence']`, `timdr_res['warnings']` i
`timdr_result['suggested_position_size']`. Brak tych kluczy dałby
`KeyError` zaraz po naprawieniu Bugu 1.

### Bug 3 (łańcuchowy) — zła nazwa klucza `position_size`

Osierocona wersja `filter_recommendation_by_timdr` (z pliku root
`timdr.py`) ustawiała `rec_copy["sugerowana_wielkosc_pozycji"]`, ale
`main.py` czyta `final_rec["position_size"]` — inna nazwa klucza,
dałoby kolejny `KeyError`.

### Bug 4 (łańcuchowy) — brak `note` w najlepszym przypadku

Ta sama osierocona funkcja ustawiała `rec_copy["note"]` tylko w
gałęziach `"szum"` lub `"pół-obiekt"` + `"SILNE"` w akcji. Dla gałęzi
`"obiekt"` (najlepszy i statystycznie najczęstszy wynik) `note` **nigdy
nie było ustawiane**, a `main.py` bezwarunkowo drukuje
`final_rec["note"]` — `KeyError` właśnie w najbardziej pożądanym
scenariuszu.

**Naprawa (Bugi 1–4):** przepisano `core/timdr.py` scalając pełną
wersję `timdr_evaluate` (z walidacją znaku drawdown, przycinaniem
winrate do [0,1], listą ostrzeżeń, `confidence`,
`suggested_position_size`, konfigurowalnymi wagami/progami) z nową
`filter_recommendation_by_timdr`, która poprawnie ustawia
`position_size` i `note` we **wszystkich** gałęziach. Zweryfikowano
pełnym przebiegiem `python3 main.py DEMO --csv demo_data.csv --verbose`
— zero błędów, spójny wynik.

### Bug 5 (krytyczny, znaleziony przy budowie API) — `yfinance.download(show_errors=...)`

`data/loader.py` wołał:
```python
yf.download(ticker, period=period, auto_adjust=True, progress=False, show_errors=False)
```
Parametr `show_errors` **nie istnieje** w nowszych wersjach `yfinance`
(potwierdzone na zainstalowanej `yfinance==1.6.0`):
```
TypeError: download() got an unexpected keyword argument 'show_errors'
```
To crashowało **każdą** próbę pobrania żywych danych — niezależnie od
tego, czy komputer ma dostęp do internetu czy nie, ponieważ błąd
występował na etapie wywołania funkcji, przed jakimkolwiek zapytaniem
sieciowym. Innymi słowy: nawet na komputerze z pełnym dostępem do
Yahoo Finance, `run.bat` w oryginalnej wersji repo nie zadziałałby.

**Naprawa:** usunięto przestarzały parametr `show_errors` z wywołania
`yf.download(...)`, z dodatkowym `try/except TypeError` jako
zabezpieczeniem na wypadek bardzo starych wersji `yfinance` o innej
sygnaturze. Zweryfikowano: po naprawie `load_ohlc("AAPL")` w tym
sandboksie kończy się teraz oczekiwanym błędem sieciowym
(`curl: (7) CONNECT tunnel failed`), a nie `TypeError` — dokładnie
błąd sieci sandboksa, a nie błąd kodu.

### Bug 6 (zgłoszony przez użytkownika po uruchomieniu na własnym komputerze) — puste dane mimo naprawy Buga 5

Po naprawie Buga 5 `yf.download()` przestawał crashować, ale na
komputerze użytkownika dashboard i tak pokazywał czerwony błąd "Yahoo
Finance zwróciło puste dane... Brak danych dla wybranego okresu".

Przyczyna: Yahoo Finance wprowadził w 2025/2026 ochronę antybotową
(Cloudflare) na swoim API. Starsze wersje `yfinance` — czyli te, które
`pip install yfinance` instaluje, jeśli **jakakolwiek** wersja jest już
zainstalowana na komputerze (bo `pip install pakiet` bez `--upgrade`
uznaje istniejącą instalację za spełniającą wymaganie) — nie mają
biblioteki `curl_cffi` do podszywania się pod przeglądarkę i dostają w
odpowiedzi puste dane albo `JSONDecodeError`. To potwierdzony,
publiczny problem: [ranaroussi/yfinance#2393](https://github.com/ranaroussi/yfinance/issues/2393).
Aktualna wersja `yfinance` (2.x, z `curl_cffi`) sobie z tym radzi.

**Naprawa:** `run.bat` teraz wymusza `pip install --upgrade yfinance`
(nie tylko "zainstaluj jeśli brak") przy **każdym** uruchomieniu, więc
zawsze używana jest najnowsza, załatana wersja. Komunikat błędu w
`data/loader.py` i podpowiedź w `api.py` też zaktualizowano, żeby od
razu wskazywały tę komendę jako pierwszy krok diagnostyki.

Jeśli mimo aktualizacji `yfinance` nadal widzisz puste dane — to
najpewniej realny throttling/blokada IP po stronie Yahoo (nie błąd w
tym repo); poczekaj chwilę albo użyj przycisku "Dane demo" w
międzyczasie.

### Bug 7 (zgłoszony przez użytkownika, dashboard v2) — nieprawidłowy JSON: `Unexpected token 'N'... 'ma_fast':[NaN,NaN,Na'... is not valid JSON`

Po naprawieniu Bugów 5–6 żywe dane zaczęły się pobierać, ale dashboard w
przeglądarce od razu rzucał błąd parsowania JSON. Wskaźniki
`ma_fast`/`ma_slow`/`rsi` mają z natury `NaN` na początku serii (zanim
okno kroczące się wypełni) — dla dłuższych/świeższych tickerów
(np. `EURPLN=X`) to nawet 30 pierwszych wartości.

Kod próbował to obsłużyć: `df["ma_fast"].round(4).where(df["ma_fast"].notna(), None)`.
Problem: `pandas.Series.where(..., None)` na kolumnie o typie `float64`
**nie wstawia Pythonowego `None`** — pandas nie potrafi przechować
`None` w kolumnie zmiennoprzecinkowej i po cichu konwertuje z powrotem
na `NaN`. Zweryfikowano bezpośrednio:
```python
>>> pd.Series([1.0, float('nan')]).where(lambda s: s.notna(), None).tolist()
[1.0, nan]   # nie [1.0, None] !
```
`.tolist()` dawał więc listę Pythonowych `float('nan')`, a
`flask.jsonify` (przez `json.dumps(..., allow_nan=True)` — domyślne
ustawienie) serializował je jako **dosłowny token `NaN`** w JSON-ie.
To rozszerzenie Pythona jest niezgodne z RFC 8259 — przeglądarkowy
`JSON.parse()` je odrzuca, dając dokładnie zgłoszony błąd. Testy w tym
repo tego nie wyłapały wcześniej, bo używały `resp.get_json()`, które
pod spodem też używa (tolerancyjnego) `json.loads` Pythona.

**Naprawa:** dodano `_clean_json()` w `api.py` — rekurencyjnie
przechodzi cały wynik odpowiedzi i zamienia `NaN`/`Infinity`/`-Infinity`
na `None` na poziomie zwykłych list/dictów (nie pandas/numpy), tuż
przed `jsonify`. Usunięto niedziałającą próbę `.where(..., None)`.
Dodano `test_bug7_odpowiedz_demo_jest_scisle_poprawnym_jsonem` w
`test_api.py`, który parsuje surową odpowiedź TAK restrykcyjnie jak
przeglądarka (`json.loads(..., parse_constant=...)` odrzucający
`NaN`/`Infinity`) — złapałby ten błąd, gdyby wrócił.

## Struktura repo

```
analizator-gieldowy/
├── core/timdr.py              # ocena TIMDR (naprawiona, patrz Bug 1-4)
├── data/loader.py              # wczytywanie CSV / Yahoo Finance (naprawiony, Bug 5)
├── models/signals.py           # sygnały MA + RSI + pamięć adaptacyjna (bez zmian, poprawny)
├── models/backtest.py          # wektorowy backtester + metryki (bez zmian, poprawny)
├── main.py                     # CLI (dodano --csv)
├── api.py                      # Flask API
├── static/dashboard.html       # dashboard (Canvas 2D, bez CDN)
├── generate_demo_csv.py        # generator syntetycznych danych demo
├── demo_data.csv               # 260 dni OHLCV, syntetyczne (GBM + wstrzyknięty trend spadkowy)
├── test_core_timdr.py          # 12 testów, w tym regresje dla Bug 1-4
├── test_loader.py              # 6 testów, w tym regresja dla Bug 5
├── test_api.py                 # 7 testów end-to-end przez Flask test_client, w tym regresja dla Bug 7
├── run.bat
└── requirements.txt
```

## API

| Endpoint | Metoda | Opis |
|---|---|---|
| `/` | GET | dashboard |
| `/api/health` | GET | healthcheck |
| `/api/demo` | GET | pełna analiza na wbudowanych danych syntetycznych |
| `/api/analyze` | POST | `{"ticker":"AAPL","period":"1y","use_demo":false}` — żywe dane albo demo |

Odpowiedź `/api/demo` i `/api/analyze` zawiera: `dates`, `close`,
`ma_fast`, `ma_slow`, `rsi`, `signal`, `equity`, `recommendation`
(action/price/sl/tp/position_size/note), `metrics`
(sharpe/winrate/drawdown/cagr/trades), `timdr`
(R_total/E/confidence/details/warnings), `is_demo`.

## CLI (bez zmian funkcjonalnych poza `--csv`)

```
python main.py AAPL --period 1y
python main.py DEMO --csv demo_data.csv --verbose
python main.py AAPL TSLA BTC-USD --save
```

## Testy

```
pip install -r requirements.txt
pytest -q
```
Wynik: **25/25 passed** (12 w `test_core_timdr.py`, 6 w `test_loader.py`,
7 w `test_api.py`).

## Wynik przykładowej analizy (dane demo, do wglądu)

```
Decyzja:          SILNE SPRZEDAJ (STRONG SELL)
Sugerowana Pozycja: 100%
Aktualna Cena:    108.97$
Stop Loss (SL):   115.17$
Take Profit (TP): 96.56$
R_total:          0.6304
Ufność:           63%
Emergencja:       obiekt (strategia stabilna)
```
(dane syntetyczne — nie jest to rzeczywista prognoza rynkowa)
