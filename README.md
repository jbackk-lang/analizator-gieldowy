# 📈 Analizator Giełdowy TIMDR / GSF + Multi-Timeframe Engine

> Adaptacyjny system wyceny rynkowej i oceny strategii inwestycyjnych oparty na filitrze topologiczno-informacyjnym (TIMDR), globalnym skalarze kontekstu (GSF), analizie wolumenu (VWAP/OBV) oraz skanerze zintegrowanym z systemem alertowym.

---

## 💡 Czym jest ten system?

Standardowy analizator lub backtest sprawdza jedynie historyczne wyniki. Ten system daje **decyzje handlowe w czasie rzeczywistym**, odpowiadając na kluczowe pytanie: **czy obecny ruch rynkowy to trwały trend, czy tylko szum?**

### Kluczowe Funkcjonalności:
- **Silnik Multi-Timeframe (1D / 1W):** Bada spójność sygnałów na różnych interwałach. W przypadku wykrycia dywergencji (np. silny dzienny pęd przy słabym interwale tygodniowym) system automatycznie redukuje wielkość pozycji (Discord TF).
- **Kontekst Makro & Sektorowy (GSF):** Uwzględnia globalne zmienne makroekonomiczne (VIX, US10Y, EUR/USD, ropa BRENT, miedź), korygując wycenę spółek z poszczególnych sektorów (Banki, Surowce, Technologia).
- **Weryfikacja Wolumenu (VWAP & OBV):** Odrzuca fałszywe wybicia. Rezonans akumulacyjny jest potwierdzany tylko wtedy, gdy wskaźnik OBV rośnie powyżej swojej średniej SMA20, a kurs znajduje się w okolicy punktu równowagi cenowej (VWAP 20d).
- **Zarządzanie Ryzykiem i Pozycją:** Wyznacza dynamiczne poziomy `Stop Loss (1.5x ATR)` oraz `Take Profit (2.5x–2.75x ATR)` dopasowane do aktualnej zmienności rynkowej.
- **System Alertowy:** Wysyła natychmiastowe powiadomienia na **Discorda** oraz **Telegram**, gdy kurs spółki wejdzie w wyznaczoną strefę rezonansu (złotą strefę wejścia).

---

## 🛠️ Instalacja i Wymagania

Sklonuj repozytorium i zainstaluj wymagane pakiety:

```bash
git clone [https://github.com/twoje-konto/analizator-timdr.git](https://github.com/twoje-konto/analizator-timdr.git)
cd analizator-timdr
pip install yfinance pandas numpy plotly matplotlib requests
