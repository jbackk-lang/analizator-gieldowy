# old/ — oryginalne, wadliwe wersje (przed naprawą)

Ten folder to archiwum "przed" — dokładne kopie plików z pierwszej
wersji repo `jbackk-lang/analizator-gieldowy` (commit
`1d0c3150b0df2bea826138a07303a1b31f961b09`, sprzed dzisiejszych
poprawek), zachowane wyłącznie do porównania/historii. **Nie używaj ich
do uruchomienia** — folder nadrzędny (`..`) zawiera już naprawioną,
przetestowaną wersję.

| Plik tutaj | Oryginalna ścieżka w repo | Błąd |
|---|---|---|
| `core_timdr_ORYGINAL_PRZED_NAPRAWA.py` | `core/timdr.py` | Brak `filter_recommendation_by_timdr` (Bug 1), brak kluczy `confidence`/`suggested_position_size`/`warnings` (Bug 2) |
| `timdr_root_ORYGINAL_OSIEROCONY.py` | `timdr.py` (katalog główny, nigdy nie importowany przez main.py) | Zła nazwa klucza `sugerowana_wielkosc_pozycji` zamiast `position_size` (Bug 3), brak `note` w gałęzi "obiekt" (Bug 4) |
| `loader_ORYGINAL_PRZED_NAPRAWA.py` | `data/loader.py` | `yf.download(..., show_errors=False)` — parametr usunięty w nowszych `yfinance`, `TypeError` przy każdej próbie pobrania danych (Bug 5) |

Pełny opis wszystkich 7 znalezionych i naprawionych błędów (z
weryfikacją i numerami przed/po) jest w głównym `README.md` w folderze
nadrzędnym.
