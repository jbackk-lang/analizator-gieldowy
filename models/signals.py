def adaptive_fused_signal(
    df: pd.DataFrame,
    window: int = 20,
    fee: float = 0.0005
) -> pd.DataFrame:
    """
    Adaptacyjna fuzja sygnałów (E2):
      - wagi MA i ATR zmieniają się w czasie
      - wagi zależą od lokalnej skuteczności (rolling performance)
      - fuzja = emergencja sygnału TIMDR

    window = ile dni patrzymy wstecz, żeby ocenić skuteczność
    """

    out = df.copy()

    # 1. Oba sygnały
    out = simple_signal(out)
    out = atr_breakout_signal(out)

    # 2. Zwroty
    out["ret"] = out["Close"].pct_change()

    # 3. Rolling performance MA
    out["pos_ma"] = out["signal_ma"].shift(1).fillna(0)
    out["ret_ma"] = out["pos_ma"] * out["ret"]
    out["perf_ma"] = out["ret_ma"].rolling(window).mean()

    # 4. Rolling performance ATR
    out["pos_atr"] = out["signal_atr"].shift(1).fillna(0)
    out["ret_atr"] = out["pos_atr"] * out["ret"]
    out["perf_atr"] = out["ret_atr"].rolling(window).mean()

    # 5. Normalizacja (softmax)
    perf_ma = out["perf_ma"].fillna(0)
    perf_atr = out["perf_atr"].fillna(0)

    exp_ma = np.exp(perf_ma)
    exp_atr = np.exp(perf_atr)
    denom = exp_ma + exp_atr + 1e-9

    out["w_ma"] = exp_ma / denom
    out["w_atr"] = exp_atr / denom

    # 6. Fuzja sygnałów
    # ATR jest w [-1, 1], MA w [0, 1] → normalizujemy ATR
    atr_norm = (out["signal_atr"] + 1) / 2

    fused = out["w_ma"] * out["signal_ma"] + out["w_atr"] * atr_norm

    # 7. Emergentny sygnał
    out["signal_adaptive"] = np.where(
        fused > 0.66, 1,
        np.where(fused < 0.33, -1, 0)
    )

    return out
