"""
data/loader.py — ładuje dane OHLCV z pliku CSV lub Yahoo Finance.

POPRAWKA (bug #5, znaleziony przy budowie api.py): oryginalny kod wołał
    yf.download(ticker, period=period, auto_adjust=True, progress=False,
                show_errors=False)
Parametr `show_errors` został usunięty z `yfinance.download()` w
nowszych wersjach biblioteki (potwierdzone: `yfinance==1.6.0` -> `TypeError:
download() got an unexpected keyword argument 'show_errors'`). Efekt: KAŻDA
próba pobrania żywych danych (czyli główny cel tego repo/run.bat) kończyła
się crashem, niezależnie od dostępu do internetu - błąd występował od razu,
zanim doszło do jakiegokolwiek zapytania sieciowego. Naprawiono usuwając
przestarzały parametr; patrz README.md.

POPRAWKA (bug #6, zgłoszony przez użytkownika po uruchomieniu run.bat na
własnym komputerze): po naprawie buga #5 `yf.download()` przestawał
rzucać TypeError, ale nadal zwracał PUSTY DataFrame ("brak danych") dla
poprawnych tickerów. Przyczyna: Yahoo Finance wprowadził w 2025/2026
ochronę antybotową (Cloudflare) - starsze wersje `yfinance` (bez
biblioteki `curl_cffi` do podszywania się pod przeglądarkę) dostają w
odpowiedzi puste dane albo `JSONDecodeError`
(https://github.com/ranaroussi/yfinance/issues/2393). To NIE jest błąd
w tym repo, tylko efekt zainstalowanej, przestarzałej wersji yfinance
na komputerze użytkownika (samo `pip install yfinance`, bez
`--upgrade`, nic nie zmienia, jeśli jakakolwiek wersja jest już
zainstalowana). Naprawiono w run.bat, które teraz wymusza
`pip install --upgrade yfinance` przy każdym uruchomieniu.
"""

import os
import time
import pandas as pd


_REQUIRED_COLS = {"Open", "High", "Low", "Close"}

_CSV_HELP = (
    "Podaj własny plik CSV z parametrem csv_path=...\n"
    "Format: Date,Open,High,Low,Close[,Volume]\n"
    "Przykład: load_ohlc('AAPL', csv_path='dane/aapl.csv')"
)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().title() for c in df.columns]
    return df


def _flatten_multiindex(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(ticker.upper(), axis=1, level=1)
        except KeyError:
            df.columns = df.columns.get_level_values(0)
    return df


def load_ohlc(
    ticker: str,
    period: str = "1y",
    csv_path: str = None,
    retries: int = 2,
) -> pd.DataFrame:
    if csv_path is not None:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Plik CSV nie istnieje: {csv_path!r}\n{_CSV_HELP}"
            )
        try:
            df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
        except KeyError:
            df = pd.read_csv(csv_path, parse_dates=[0], index_col=0)

        df = _normalize_columns(df)
        return _validate_and_clean(df, source=f"CSV:{csv_path}")

    try:
        import yfinance as yf
    except ImportError:
        raise ImportError(
            "Biblioteka yfinance nie jest zainstalowana.\n"
            "Instalacja: pip install yfinance\n"
            f"Alternatywnie: {_CSV_HELP}"
        )

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            try:
                df = yf.download(
                    ticker,
                    period=period,
                    auto_adjust=True,
                    progress=False,
                )
            except TypeError:
                # bardzo stare wersje yfinance mogą wymagać innych
                # argumentów - awaryjnie wołamy z minimalnym zestawem
                df = yf.download(ticker, period=period, progress=False)
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(1.0)
            continue

        df = _flatten_multiindex(df, ticker)
        df = _normalize_columns(df)

        if df.empty:
            last_error = ValueError(
                f"Yahoo Finance zwróciło puste dane dla '{ticker}' "
                f"(period='{period}'). Możliwe przyczyny:\n"
                f"  • NAJCZĘSTSZA: masz przestarzałą wersję yfinance bez ochrony\n"
                f"    przed blokadą antybotową Yahoo — uruchom:\n"
                f"    python -m pip install --upgrade yfinance\n"
                f"    (run.bat robi to automatycznie przy każdym starcie)\n"
                f"  • Throttling Yahoo — odczekaj chwilę i spróbuj ponownie\n"
                f"  • Nieprawidłowy symbol tickera\n"
                f"  • Brak danych dla wybranego okresu\n"
                f"{_CSV_HELP}"
            )
            if attempt < retries:
                time.sleep(2.0)
            continue

        return _validate_and_clean(df, source=f"Yahoo:{ticker}")

    if isinstance(last_error, Exception):
        raise last_error
    raise RuntimeError(f"Nie udało się pobrać danych dla '{ticker}'.")


def _validate_and_clean(df: pd.DataFrame, source: str = "") -> pd.DataFrame:
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"Brak wymaganych kolumn {sorted(missing)} w danych ({source}).\n"
            f"Dostępne kolumny: {sorted(df.columns.tolist())}\n"
            f"Wymagane: {sorted(_REQUIRED_COLS)}"
        )

    cols = ["Open", "High", "Low", "Close"]
    if "Volume" in df.columns:
        cols.append("Volume")

    df = df[cols].copy()
    df.dropna(inplace=True)

    if df.empty:
        raise ValueError(
            f"Po usunięciu NaN DataFrame jest pusty ({source}). "
            "Sprawdź jakość danych wejściowych."
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df.sort_index(inplace=True)
    return df
