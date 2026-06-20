import pandas as pd
import numpy as np


def backtest_signals(df: pd.DataFrame, signal_col: str = "signal", fee: float = 0.0005):
    """
    Prosty backtest:
      - long gdy signal == 1
      - short gdy signal == -1
      - flat gdy signal == 0

    fee = prowizja (0.05%)
    """

    out = df.copy()

    # Zwroty procentowe
    out["ret"] = out["Close"].pct_change()

    # Pozycja wg sygnału
    out["pos"] = out[signal_col].shift(1).fillna(0)

    # Zwrot strategii
    out["strategy_ret"] = out["pos"] * out["ret"]

    # Koszt transakcyjny przy zmianie pozycji
    out["trade"] = out["pos"].diff().abs()
    out["strategy_ret"] -= out["trade"] * fee

    # Krzywa kapitału
    out["equity"] = (1 + out["strategy_ret"]).cumprod()

    return out


def compute_metrics(df: pd.DataFrame):
    """
    Metryki dla TIMDR:
      - sharpe
      - winrate
      - max drawdown
    """

    ret = df["strategy_ret"].dropna()

    # Sharpe (dzienny)
    sharpe = np.sqrt(252) * ret.mean() / (ret.std() + 1e-9)

    # Winrate
    wins = (ret > 0).sum()
    total = len(ret)
    winrate = wins / total if total > 0 else 0

    # Max drawdown
    equity = df["equity"]
    roll_max = equity.cummax()
    dd = ((equity - roll_max) / roll_max).min()
    drawdown = abs(dd)

    return {
        "sharpe": float(sharpe),
        "winrate": float(winrate),
        "drawdown": float(drawdown)
    }
