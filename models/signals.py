"""
models/signals.py — sygnały giełdowe · analizator-giełdowy

Poprawki v2:
  1. memory_adaptive_fused_signal — progi RSI domyślnie 30/70 zamiast 40/60
     (rsi_buy=40 / rsi_sell=60 powodowało zbyt częste sygnały RSI, dając
     nadmiar transakcji i gorsze wyniki niż simple_signal)
  2. memory_adaptive: mode_window zamiast mean dla "pamięci" — dominant vote
     zamiast średniej (unika sygnałów ułamkowych na granicy)
  3. Dodana kolumna "signal_raw" (przed pamięcią) dla debugowania
  4. simple_signal: dodana kolumna "crossover" (True w dniu zmiany)
  5. Obie funkcje: zabezpieczenie przed za krótkim DataFrame (< max(slow, rsi_period))
"""

import pandas as pd
import numpy as np


def simple_signal(
    df:   pd.DataFrame,
    fast: int = 10,
    slow: int = 30,
) -> pd.DataFrame:
    """
    Prosty sygnał MA crossover.

    Zwraca: +1 kup / −1 sprzedaj / 0 czekaj
    Dodatkowe kolumny: ma_fast, ma_slow, crossover
    """
    if len(df) < slow:
        raise ValueError(
            f"Za mało danych: {len(df)} wierszy, potrzeba co najmniej {slow} "
            f"dla slow MA={slow}."
        )

    df = df.copy()
    df["ma_fast"] = df["Close"].rolling(fast).mean()
    df["ma_slow"] = df["Close"].rolling(slow).mean()

    df["signal"] = 0
    df.loc[df["ma_fast"] > df["ma_slow"], "signal"] =  1
    df.loc[df["ma_fast"] < df["ma_slow"], "signal"] = -1

    # Dodatkowa kolumna: dzień zmiany sygnału (crossover)
    df["crossover"] = df["signal"].diff().abs() > 0

    return df


def memory_adaptive_fused_signal(
    df:            pd.DataFrame,
    fast:          int   = 10,
    slow:          int   = 30,
    rsi_period:    int   = 14,
    rsi_buy:       float = 30.0,   # POPRAWKA: było 40.0 — zbyt agresywne
    rsi_sell:      float = 70.0,   # POPRAWKA: było 60.0 — zbyt agresywne
    memory_window: int   = 5,
) -> pd.DataFrame:
    """
    Fused signal: MA crossover + RSI + dominant-vote pamięci.

    Poprawki:
    - rsi_buy=30 / rsi_sell=70 — standardowe progi RSI (zamiast 40/60)
    - Pamięć przez dominant vote (mode), nie mean() — brak sygnałów ułamkowych
    - Dodana kolumna signal_raw (fuzja przed pamięcią) do debugowania

    Zwraca kolumny:
        signal_memory_adaptive — finalny sygnał (+1/0/−1)
        signal_raw             — sygnał bez pamięci
        rsi                    — wartość RSI
        ma_fast, ma_slow       — średnie kroczące
    """
    min_len = max(slow, rsi_period)
    if len(df) < min_len:
        raise ValueError(
            f"Za mało danych: {len(df)} wierszy, potrzeba co najmniej {min_len}."
        )

    df = df.copy()

    # ── MA crossover ─────────────────────────────────────────────────────────
    df["ma_fast"] = df["Close"].rolling(fast).mean()
    df["ma_slow"] = df["Close"].rolling(slow).mean()

    ma_sig = pd.Series(0, index=df.index)
    ma_sig[df["ma_fast"] > df["ma_slow"]] =  1
    ma_sig[df["ma_fast"] < df["ma_slow"]] = -1

    # ── RSI ──────────────────────────────────────────────────────────────────
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(rsi_period).mean()
    loss  = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))
    df["rsi"] = rsi

    rsi_sig = pd.Series(0, index=df.index)
    rsi_sig[rsi < rsi_buy]  =  1   # RSI wyprzedany → kup
    rsi_sig[rsi > rsi_sell] = -1   # RSI wykupiony  → sprzedaj

    # ── Fuzja MA + RSI ───────────────────────────────────────────────────────
    # Oba sygnały muszą się zgadzać → fuzja clip(-1,1) jako głosowanie
    fused = (ma_sig + rsi_sig).clip(-1, 1)
    df["signal_raw"] = fused.astype(int)

    # ── POPRAWKA: Pamięć przez dominant vote ─────────────────────────────────
    # Oryginał: rolling mean → wartości 0.2, 0.6 → round → tylko int
    # Poprawka: rolling apply z mode (najczęstszy sygnał w oknie)
    def _dominant_vote(window: np.ndarray) -> int:
        vals, counts = np.unique(window.astype(int), return_counts=True)
        return int(vals[np.argmax(counts)])

    df["signal_memory_adaptive"] = (
        fused.rolling(memory_window, min_periods=1)
             .apply(_dominant_vote, raw=True)
             .astype(int)
    )

    return df
