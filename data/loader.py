"""
data/loader.py — ładuje dane OHLCV z pliku CSV lub Yahoo Finance.

Poprawki v2:
  1. Graceful fallback gdy yfinance zwraca pusty DataFrame (throttling Yahoo)
     → czytelny komunikat z sugestią csv_path i przykładem formatu
  2. Retry (max 2 próby) z krótką pauzą przy pustym wyniku
  3. Walidacja kolumn OHLC z czytelnym komunikatem błędu
  4. Obsługa MultiIndex w yfinance ≥ 0.2.x (zwraca MultiIndex columns)
  5. Normalizacja nazw kolumn (case-insensitive: 'close' → 'Close')
  6. Komunikat gdy yfinance nie zainstalowane — z instrukcją instalacji

Użycie:
    # Z Yahoo Finance (wymaga yfinance + internetu):
    df = load_ohlc("AAPL", period="1y")

    # Z własnego pliku CSV:
    df = load_ohlc("AAPL", csv_path="moje_dane.csv")

Format CSV:
    Date,Open,High,Low,Close,Volume
    2024-01-02,185.0,186.5,184.2,185.9,55000000
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
    """Normalizuje nazwy kolumn do Title Case (close → Close)."""
    df.columns = [c.strip().title() for c in df.columns]
    return df


def _flatten_multiindex(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    yfinance ≥ 0.2.x zwraca MultiIndex columns: (Price, Ticker).
    Spłaszcza do pojedynczego poziomu biorąc tylko kolumny dla danego tickera.
    """
    if isinstance(df.columns, pd.MultiIndex):
        # Poziom 0 = nazwa kolumny, poziom 1 = ticker
        try:
            df = df.xs(ticker.upper(), axis=1, level=1)
        except KeyError:
            # Fallback: weź pierwszy poziom
            df.columns = df.columns.get_level_values(0)
    return df


def load_ohlc(
    ticker:   str,
    period:   str = "1y",
    csv_path: str | None = None,
    retries:  int = 2,
) -> pd.DataFrame:
    """
    Ładuje dane OHLCV dla tickera.

    Parametry:
        ticker   : symbol giełdowy (np. 'AAPL', 'PKN.WA')
        period   : okres dla yfinance ('1y', '2y', '6mo', 'max', ...)
        csv_path : ścieżka do pliku CSV (jeśli podana, omija Yahoo Finance)
        retries  : liczba prób przy pustym wyniku z Yahoo (domyślnie 2)

    Zwraca:
        pd.DataFrame z kolumnami: Open, High, Low, Close [, Volume]
        Indeks: DatetimeIndex (tylko dni sesyjne)
    """
    # ── ŚCIEŻKA 1: CSV ────────────────────────────────────────────────────────
    if csv_path is not None:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Plik CSV nie istnieje: {csv_path!r}\n{_CSV_HELP}"
            )
        try:
            df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
        except KeyError:
            # Spróbuj bez index_col jeśli brak kolumny Date
            df = pd.read_csv(csv_path, parse_dates=[0], index_col=0)

        df = _normalize_columns(df)
        return _validate_and_clean(df, source=f"CSV:{csv_path}")

    # ── ŚCIEŻKA 2: Yahoo Finance ──────────────────────────────────────────────
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
            df = yf.download(
                ticker,
                period=period,
                auto_adjust=True,
                progress=False,
                show_errors=False,
            )
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(1.0)
            continue

        # POPRAWKA: obsługa MultiIndex (yfinance ≥ 0.2.x)
        df = _flatten_multiindex(df, ticker)
        df = _normalize_columns(df)

        if df.empty:
            last_error = ValueError(
                f"Yahoo Finance zwróciło puste dane dla '{ticker}' "
                f"(period='{period}'). Możliwe przyczyny:\n"
                f"  • Throttling Yahoo — odczekaj chwilę i spróbuj ponownie\n"
                f"  • Nieprawidłowy symbol tickera\n"
                f"  • Brak danych dla wybranego okresu\n"
                f"{_CSV_HELP}"
            )
            if attempt < retries:
                time.sleep(2.0)
            continue

        return _validate_and_clean(df, source=f"Yahoo:{ticker}")

    # Wszystkie próby nieudane
    if isinstance(last_error, Exception):
        raise last_error
    raise RuntimeError(f"Nie udało się pobrać danych dla '{ticker}'.")


def _validate_and_clean(df: pd.DataFrame, source: str = "") -> pd.DataFrame:
    """Waliduje kolumny i czyści dane."""
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

    # Upewnij się że indeks to DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df.sort_index(inplace=True)
    return df
