## Dokumentacja online
https://jbackk-lang.github.io/
# Analizator Giełdowy oparty na TIMDR/GIA

> Adaptacyjny system oceny strategii inwestycyjnych z filtrem topologiczno-informacyjnym.

---

## Czym to jest (dla inwestora / tradera)

Standardowy backtest mówi Ci: **czy strategia zarabiała w przeszłości**.  
Ten analizator mówi Ci coś innego: **w jakiej fazie był rynek, gdy strategia działała — i czy ta faza wraca**.

Zamiast oceniać tylko wynik (zysk/strata), TIMDR ocenia **strukturę kontekstu**:
- Czy rynek był w fazie wysokiej spójności (trend)? → wynik w takiej fazie ma inną wagę niż wynik w chaosie
- Czy sygnał pojawił się w momencie rezonansu (zbieżność wolumenu, zmienności, kierunku)? → sygnały rezonansowe są trwalsze
- Czy warunki, w których strategia działała, wciąż istnieją? → to pytanie, którego RSI nie zadaje

**Nie jest to** zamiennik RSI, MACD ani analizy technicznej. To **filtr oceny** nakładany na wynik backtestingu.

---

## Czym to jest (dla developera / quanta)

System składa się z trzech warstw:

### 1. Silnik TIMDR
Konfiguracyjny obiekt oceny oparty na pięciu wymiarach:

```python
config = {
    "T": 0.3,   # Topologia — spójność struktury cenowej (trend vs chaos)
    "I": 0.25,  # Informacja — gęstość sygnału (wolumen, zmienność, ATR)
    "M": 0.2,   # Modal — dominujący tryb rynku (trend / range / reversal)
    "It": 0.15, # Dynamika czasowa — tempo zmiany struktury
    "R": 0.1    # Rezonans — zbieżność wielu sygnałów w jednym punkcie
}
```

Wagi są konfigurowane per strategia i per ticker. Funkcja `timdr_evaluate()` zwraca skalar [0, 1] — im wyższy, tym bardziej kontekst backtestingu odpowiada warunkom "rezonansowym".

### 2. Moduł danych OHLC
Pobiera dane historyczne (domyślnie: `yfinance`), normalizuje, oblicza wskaźniki pomocnicze (ATR, wolumen względny, kierunkowość).

### 3. Backtest + ocena TIMDR
Standardowy backtest (sygnały wejścia/wyjścia) jest uruchamiany niezależnie od TIMDR. Wyniki są następnie filtrowane przez `timdr_evaluate()` — transakcje przeprowadzone w warunkach niskiego rezonansu są oznaczane jako strukturalnie słabsze, nawet jeśli były zyskowne.

```python
results = run_backtest(ticker="AAPL", strategy=my_strategy)
timdr_score = timdr_evaluate(results, config)
print(f"Wynik backtestingu: {results['return']:.1%}")
print(f"Ocena TIMDR: {timdr_score:.2f} / 1.0")
```

---

## Szybki start

```bash
git clone https://github.com/jbackk-lang/analizator-gieldowy
cd analizator-gieldowy
pip install -r requirements.txt
python main.py --ticker AAPL --period 2y
```

---

## Przykład: to samo co RSI, ale inne pytanie

| Metryka | Klasyczny backtest | Backtest + TIMDR |
|---|---|---|
| Zwrot całkowity | +34% | +34% |
| Win rate | 58% | 58% |
| Transakcje w fazie rezonansu | — | 71% |
| Wynik transakcji rezonansowych | — | +51% |
| Wynik transakcji nierezonansowych | — | +8% |

> Strategia zarabiała — ale prawie cały zysk pochodził z warunków, które TIMDR identyfikuje jako "spójne topologicznie". W warunkach chaosu ta sama strategia prawie nie zarabiała.  
> To jest informacja, której klasyczny backtest nie daje.

*(Dane przykładowe — uruchom `python example.py` żeby zobaczyć wyniki na rzeczywistych danych)*

---

## Kiedy to ma sens, a kiedy nie

**Ma sens gdy:**
- Strategia działa dobrze w trendach, słabo w konsolidacjach (lub odwrotnie) — TIMDR to wyizoluje
- Chcesz wiedzieć, czy aktualne warunki rynkowe odpowiadają tym, w których strategia działała
- Budujesz system adaptacyjny, który zmienia parametry w zależności od fazy rynku

**Nie ma sensu gdy:**
- Szukasz prostego potwierdzenia że strategia jest dobra — użyj wtedy klasycznego backtestingu z Sharpe ratio
- Twoja strategia jest HFT lub oparta na arbitrażu (TIMDR operuje na strukturze dziennej/tygodniowej)

---

## Podstawy teoretyczne

TIMDR (Topological Information Modal Dynamic Resonance) to framework opisujący przepływ informacji przez układy dynamiczne w sześciu warstwach. W kontekście rynków finansowych: rynek jest układem dynamicznym, a transakcja jest sygnałem — jej jakość zależy od tego, w jakiej fazie układu się pojawia.

Pełna dokumentacja modelu: [GIA-and-TIMDR](https://github.com/jbackk-lang/GIA-and-TIMDR)

---

## Status projektu

🔧 Aktywny rozwój — konto założone: czerwiec 2026  
📊 Zaimplementowane: silnik TIMDR, backtest OHLC, ocena rezonansu  
🔜 W planach: interfejs webowy, integracja z Binance API, tryb live

---

*Jacek Kielich · Wieliczka · 2026*
