"""
models/backtest.py — wektorowy backtester · analizator-giełdowy

(kopia bez zmian z jbackk-lang/analizator-gieldowy)
"""

import pandas as pd
import numpy as np


def backtest_signals(
    df: pd.DataFrame,
    signal_col: str = "signal",
    price_col: str = "Close",
    commission: float = 0.001,
    initial_capital: float = 10_000.0,
) -> pd.DataFrame:
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

    df["returns"] = df[price_col].pct_change()
    df["position"] = df[signal_col].shift(1).fillna(0)
    df["strategy_returns"] = df["position"] * df["returns"]
    df["trade"] = df["position"].diff().abs()
    df["strategy_returns"] -= df["trade"] * commission

    df["equity"] = (1 + df["strategy_returns"]).cumprod()
    df["equity_capital"] = df["equity"] * initial_capital

    return df


def compute_metrics(bt: pd.DataFrame, rf: float = 0.0) -> dict:
    r = bt["strategy_returns"].dropna()

    if len(r) == 0:
        return {
            "sharpe": 0.0,
            "winrate": 0.0,
            "drawdown": 0.0,
            "cagr": 0.0,
            "total_return": 0.0,
            "trades": 0,
            "n_days": 0,
        }

    ann = 252

    r_std = r.std()
    if r_std > 0:
        sharpe = float((r.mean() - rf / ann) / r_std * np.sqrt(ann))
    else:
        sharpe = 0.0

    active_days = (r != 0).sum()
    winrate = float((r > 0).sum() / active_days) if active_days > 0 else 0.0

    equity = bt["equity"].dropna()
    if len(equity) == 0:
        drawdown = 0.0
    else:
        roll_max = equity.cummax()
        dd_series = (equity - roll_max) / roll_max.replace(0, np.nan)
        drawdown = float(dd_series.min()) * -1
        drawdown = max(0.0, drawdown)

    n_years = len(r) / ann
    final_eq = float(equity.iloc[-1]) if len(equity) > 0 else 1.0
    total_return = final_eq - 1.0
    if n_years > 0 and final_eq > 0:
        cagr = float(final_eq ** (1.0 / n_years) - 1.0)
    else:
        cagr = 0.0

    trades = int(bt["trade"].sum()) if "trade" in bt.columns else 0

    return {
        "sharpe": round(sharpe, 4),
        "winrate": round(winrate, 4),
        "drawdown": round(drawdown, 4),
        "cagr": round(cagr, 4),
        "total_return": round(total_return, 4),
        "trades": trades,
        "n_days": len(r),
    }
