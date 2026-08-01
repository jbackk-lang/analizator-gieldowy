## Dokumentacja online
https://jbackk-lang.github.io/

# Analizator Giełdowy oparty na TIMDR/GIA

> Adaptacyjny system wyceny rynkowej i oceny strategii inwestycyjnych z filtrem topologiczno-informacyjnym, automatycznym silnikiem rekomendacji oraz skanerem całych indeksów rynkowych (WIG20, S&P 500, Crypto).

---

## Czym to jest (dla inwestora / tradera)

Standardowy analizator lub backtest mówi Ci: **czy strategia zarabiała w przeszłości**.  
Ten analizator daje Ci gotowe **decyzje handlowe tu i teraz**, odpowiadając na kluczowe pytanie: **czy obecny ruch rynkowy to trwały trend, czy tylko szum?**

Zamiast samej prostej analizy wskaźnikowej (RSI, MACD), system:
- **Generuje jasną rekomendację:** `SILNE KUPUJ`, `KUPUJ`, `TRZYMAJ`, `SPRZEDAJ` lub `SILNE SPRZEDAJ`.
- **Wyznacza dynamiczne poziomy ryzyka:** Matematycznie wylicza `Stop Loss (SL)` oraz `Take Profit (TP)` w oparciu o aktualną zmienność rynkową ($1.5 \times \text{ATR}$ / $2.0 \times \text{ATR}$).
- **Zarządza wielkością pozycji (Position Sizing):** Określa, czy bezpiecznie jest wejść na 100% kapitału, 50%, czy całkowicie wstrzymać się od handlu (`0%`) z powodu wykrycia szumu rynkowego.
- **Ocenia strukturę kontekstu (TIMDR):** Bada spójność trendu, gęstość informacji i rezonans sygnałów ($R_{total}$), odrzucając fałszywe wybicia.
- **Skanuje całe indeksy:** Uruchamia automatyczny skaner całych giełd (np. GPW WIG20) i wypluwa ranking najlepiej rokujących walorów.

---

## Podgląd wyników w konsoli

### 1. Analiza pojedynczego waloru (`main.py`)

```text
=== ANALIZA: PKN.WA | 1y | 1d ===

>>> REKOMENDACJA INWESTYCYJNA <<<
Decyzja:           KUPUJ (BUY)
Sugerowana Pozycja: 100%
Sygnał Modelu:     0.6421
Aktualna Cena:     67.45 PLN
Stop Loss (SL):    64.15 PLN
Take Profit (TP):  74.05 PLN
Uwagi:             Sygnał potwierdzony przez stabilną emergencję TIMDR.
---------------------------------

=== TIMDR RESULT ===
R_total:    0.6184
Ufność:     62%
Emergencja: obiekt (strategia stabilna)
Szczegóły:  {'sharpe_n': 0.6812, 'winrate_n': 0.5833, 'dd_n': 0.8120}
====================
