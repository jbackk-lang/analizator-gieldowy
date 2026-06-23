## 🔗 Wszystkie modele i repozytoria
Pełna lista projektów znajduje się na stronie:
https://jbackk-lang.github.io
---

# Analizator Giełdowy TIMDR

Analizator giełdowy oparty na modelu **TIMDR**.  
To nie jest zwykły backtest z RSI/MACD — to **framework decyzyjny**, który ocenia strategię przez filtr struktury:  
**T → I → M → I(t) → R**.

---

## 1. O co tu chodzi?

Zamiast patrzeć tylko na:

- pojedyncze wskaźniki (RSI, MACD, SMA),
- pojedyncze transakcje,
- pojedyncze wyniki backtestu,

TIMDR patrzy na **strukturę całego obiegu**:

- jak strategia zachowuje się w czasie,
- jak wygląda sekwencja zysk/strata,
- jak zmienia się ryzyko,
- czy wynik jest stabilny, czy przypadkowy.

To jest **analiza topologiczna**, nie tylko statystyczna.

---

## 2. Struktura TIMDR w analizatorze

Konfiguracja ma postać:

```python
config = {
    "T": ...,
    "I": ...,
    "M": ...,
    "It": ...,
    "R": ...
}
