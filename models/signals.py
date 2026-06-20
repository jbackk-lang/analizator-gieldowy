# src/models/signals.py
import pandas as pd

def simple_signal(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> pd.DataFrame:
    out = df.copy()
    out["ma_fast"] = out["Close"].rolling(fast).mean()
    out["ma_slow"] = out["Close"].rolling(slow).mean()
    out["signal"] = (out["ma_fast"] > out["ma_slow"]).astype(int)
    return out
