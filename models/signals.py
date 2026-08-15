"""
models/signals.py — sygnały giełdowe · analizator-giełdowy

(kopia bez zmian z jbackk-lang/analizator-gieldowy)
"""

import pandas as pd
import numpy as np


def simple_signal(
    df: pd.DataFrame,
    fast: int = 10,
    slow: int = 30,
) -> pd.DataFrame:
    if len(df) < slow:
        raise ValueError(
            f"Za mało danych: {len(df)} wierszy, potrzeba co najmniej {slow} "
            f"dla slow MA={slow}."
        )

    df = df.copy()
    df["ma_fast"] = df["Close"].rolling(fast).mean()
    df["ma_slow"] = df["Close"].rolling(slow).mean()

    df["signal"] = 0
    df.loc[df["ma_fast"] > df["ma_slow"], "signal"] = 1
    df.loc[df["ma_fast"] < df["ma_slow"], "signal"] = -1

    df["crossover"] = df["signal"].diff().abs() > 0

    return df


def memory_adaptive_fused_signal(
    df: pd.DataFrame,
    fast: int = 10,
    slow: int = 30,
    rsi_period: int = 14,
    rsi_buy: float = 30.0,
    rsi_sell: float = 70.0,
    memory_window: int = 5,
) -> pd.DataFrame:
    min_len = max(slow, rsi_period)
    if len(df) < min_len:
        raise ValueError(
            f"Za mało danych: {len(df)} wierszy, potrzeba co najmniej {min_len}."
        )

    df = df.copy()

    df["ma_fast"] = df["Close"].rolling(fast).mean()
    df["ma_slow"] = df["Close"].rolling(slow).mean()

    ma_sig = pd.Series(0, index=df.index)
    ma_sig[df["ma_fast"] > df["ma_slow"]] = 1
    ma_sig[df["ma_fast"] < df["ma_slow"]] = -1

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    df["rsi"] = rsi

    rsi_sig = pd.Series(0, index=df.index)
    rsi_sig[rsi < rsi_buy] = 1
    rsi_sig[rsi > rsi_sell] = -1

    fused = (ma_sig + rsi_sig).clip(-1, 1)
    df["signal_raw"] = fused.astype(int)

    def _dominant_vote(window: np.ndarray) -> int:
        vals, counts = np.unique(window.astype(int), return_counts=True)
        return int(vals[np.argmax(counts)])

    df["signal_memory_adaptive"] = (
        fused.rolling(memory_window, min_periods=1)
        .apply(_dominant_vote, raw=True)
        .astype(int)
    )

    return df
