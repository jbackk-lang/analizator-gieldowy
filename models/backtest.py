"""
core/backtest.py — wektorowy backtester · analizator-giełdowy

Poprawki v2:
  1. Walidacja signal_col i price_col — czytelny błąd gdy kolumna nie istnieje
  2. Guard look-ahead bias: shift(1) gwarantowany nawet gdy caller zapomni
  3. compute_metrics: obsługa edge case gdy equity ma tylko NaN
  4. compute_metrics: sharpe annualizowany poprawnie gdy r.std()==0 (flat equity)
  5. Dodana metryka: total_return (końcowy wynik equity − 1)
  6. Dodana metryka: n_days (liczba dni w backtescie)
  7. backtest_signals: opcjonalny parametr initial_capital
"""

import pandas as pd
import numpy as np


def backtest_signals(
    df:             pd.DataFrame,
    signal_col:     str   = "signal",
    price_col:      str   = "Close",
    commission:     float = 0.001,
    initial_capital: float = 10_000.0,
) -> pd.DataFrame:
    """
    Wektorowy backtest sygnałów +1/−1/0.

    Parametry:
        df              : DataFrame z kolumnami signal_col i price_col
        signal_col      : nazwa kolumny z sygnałami (+1/0/−1)
        price_col       : nazwa kolumny z cenami (domyślnie 'Close')
        commission      : prowizja od transakcji (domyślnie 0.1%)
        initial_capital : kapitał startowy (używany do equity w PLN/USD)

    Zwraca df z dodanymi kolumnami:
        returns          — dzienna stopa zwrotu instrumentu
        position         — pozycja (z opóźnieniem 1 dnia, guard look-ahead)
        strategy_returns — dzienna stopa zwrotu strategii po prowizji
        trade            — zmiana pozycji (0 = brak transakcji)
        equity           — krzywa kapitału (startuje od 1.0)
        equity_capital   — krzywa kapitału w jednostkach initial_capital
    """
    # ── Walidacja kolumn ──────────────────────────────────────────────────────
    if signal_col not in df.columns:
        raise ValueError(
            f"Kolumna sygnału '{signal_col}' nie istnieje w DataFrame.\n"
            f"Dostępne kolumny: {list(df.columns)}"
        )
    if price_col not in df.columns:
        raise ValueError(
            f"Kolumna cen '{price_col}' nie istnieje w DataFrame.\n"
            f"Dostępne kolumny: {list(df.columns)}"
        )

    df = df.copy()

    # ── Returns ───────────────────────────────────────────────────────────────
    df["returns"] = df[price_col].pct_change()

    # ── GUARD look-ahead bias: shift(1) ──────────────────────────────────────
    # Sygnał z dnia T → pozycja otwarta NA OTWARCIU dnia T+1
    # shift(1) gwarantuje że nie używamy informacji z przyszłości
    df["position"] = df[signal_col].shift(1).fillna(0)

    # ── Strategy returns z prowizją ───────────────────────────────────────────
    df["strategy_returns"] = df["position"] * df["returns"]
    df["trade"]            = df["position"].diff().abs()
    df["strategy_returns"] -= df["trade"] * commission

    # ── Equity ───────────────────────────────────────────────────────────────
    df["equity"]         = (1 + df["strategy_returns"]).cumprod()
    df["equity_capital"] = df["equity"] * initial_capital

    return df


def compute_metrics(bt: pd.DataFrame, rf: float = 0.0) -> dict:
    """
    Oblicza metryki backtestowe.

    Parametry:
        bt : wynik backtest_signals()
        rf : roczna stopa wolna od ryzyka (domyślnie 0.0)

    Zwraca dict z:
        sharpe, winrate, drawdown, cagr, total_return, trades, n_days
    """
    r = bt["strategy_returns"].dropna()

    # ── POPRAWKA: edge case — brak danych ────────────────────────────────────
    if len(r) == 0:
        return {
            "sharpe":       0.0,
            "winrate":      0.0,
            "drawdown":     0.0,
            "cagr":         0.0,
            "total_return": 0.0,
            "trades":       0,
            "n_days":       0,
        }

    ann = 252  # dni sesyjnych w roku

    # ── Sharpe ───────────────────────────────────────────────────────────────
    # POPRAWKA: gdy std==0 (flat equity) → sharpe=0, nie NaN/inf
    r_std = r.std()
    if r_std > 0:
        sharpe = float((r.mean() - rf / ann) / r_std * np.sqrt(ann))
    else:
        sharpe = 0.0

    # ── Win rate ──────────────────────────────────────────────────────────────
    active_days = (r != 0).sum()
    winrate = float((r > 0).sum() / active_days) if active_days > 0 else 0.0

    # ── Max drawdown ─────────────────────────────────────────────────────────
    equity   = bt["equity"].dropna()
    # POPRAWKA: gdy equity ma tylko NaN lub jest pusta
    if len(equity) == 0:
        drawdown = 0.0
    else:
        roll_max = equity.cummax()
        dd_series = (equity - roll_max) / roll_max.replace(0, np.nan)
        drawdown = float(dd_series.min()) * -1   # dodatnia liczba
        drawdown = max(0.0, drawdown)            # guard przed ujemnym

    # ── CAGR ─────────────────────────────────────────────────────────────────
    n_years    = len(r) / ann
    final_eq   = float(equity.iloc[-1]) if len(equity) > 0 else 1.0
    total_return = final_eq - 1.0
    if n_years > 0 and final_eq > 0:
        cagr = float(final_eq ** (1.0 / n_years) - 1.0)
    else:
        cagr = 0.0

    # ── Trades ───────────────────────────────────────────────────────────────
    trades = int(bt["trade"].sum()) if "trade" in bt.columns else 0

    return {
        "sharpe":       round(sharpe,       4),
        "winrate":      round(winrate,      4),
        "drawdown":     round(drawdown,     4),
        "cagr":         round(cagr,         4),
        "total_return": round(total_return, 4),
        "trades":       trades,
        "n_days":       len(r),
    }
