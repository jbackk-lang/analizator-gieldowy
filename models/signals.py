import pandas as pd

def simple_signal(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> pd.DataFrame:
    out = df.copy()
    out["ma_fast"] = out["Close"].rolling(fast).mean()
    out["ma_slow"] = out["Close"].rolling(slow).mean()
    out["signal"] = (out["ma_fast"] > out["ma_slow"]).astype(int)
    return out


def atr_breakout_signal(df: pd.DataFrame, atr_period: int = 14, k: float = 2.0) -> pd.DataFrame:
    out = df.copy()

    # True Range
    out["H-L"] = out["High"] - out["Low"]
    out["H-PC"] = (out["High"] - out["Close"].shift(1)).abs()
    out["L-PC"] = (out["Low"] - out["Close"].shift(1)).abs()
    out["TR"] = out[["H-L", "H-PC", "L-PC"]].max(axis=1)

    # ATR
    out["ATR"] = out["TR"].rolling(atr_period).mean()

    # Poziomy wybicia
    out["upper"] = out["Close"].shift(1) + k * out["ATR"]
    out["lower"] = out["Close"].shift(1) - k * out["ATR"]

    # Sygnał
    out["signal_atr"] = 0
    out.loc[out["Close"] > out["upper"], "signal_atr"] = 1
    out.loc[out["Close"] < out["lower"], "signal_atr"] = -1

    return out
