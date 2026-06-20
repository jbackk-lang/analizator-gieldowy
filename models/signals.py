def memory_adaptive_fused_signal(
    df: pd.DataFrame,
    window: int = 20,
    memory_decay: float = 0.9,
    fee: float = 0.0005
) -> pd.DataFrame:
    """
    Adaptacyjna fuzja z pamięcią (F2):
      - system pamięta skuteczność sygnałów
      - pamięć zanika wykładniczo (memory_decay)
      - wagi sygnałów zależą od:
          * bieżącej skuteczności (perf)
          * pamięci skuteczności (mem)
          * pamięci rezonansu (stab)
      - wynik = emergentny sygnał TIMDR

    memory_decay = 0.9 → pamięć 90% poprzedniego stanu
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
    out["perf_ma"] = out["ret_ma"].rolling(window).mean().fillna(0)

    # 4. Rolling performance ATR
    out["pos_atr"] = out["signal_atr"].shift(1).fillna(0)
    out["ret_atr"] = out["pos_atr"] * out["ret"]
    out["perf_atr"] = out["ret_atr"].rolling(window).mean().fillna(0)

    # 5. PAMIĘĆ — inicjalizacja
    mem_ma = 0.0
    mem_atr = 0.0

    mem_ma_list = []
    mem_atr_list = []

    # 6. Aktualizacja pamięci w czasie
    for i in range(len(out)):
        mem_ma = memory_decay * mem_ma + (1 - memory_decay) * out["perf_ma"].iloc[i]
        mem_atr = memory_decay * mem_atr + (1 - memory_decay) * out["perf_atr"].iloc[i]

        mem_ma_list.append(mem_ma)
        mem_atr_list.append(mem_atr)

    out["mem_ma"] = mem_ma_list
    out["mem_atr"] = mem_atr_list

    # 7. Rezonans (stabilność sygnałów)
    out["stab_ma"] = 1 - out["ret_ma"].rolling(window).std().fillna(0)
    out["stab_atr"] = 1 - out["ret_atr"].rolling(window).std().fillna(0)

    # 8. Łączymy: performance + memory + stability
    score_ma = out["perf_ma"] + out["mem_ma"] + out["stab_ma"]
    score_atr = out["perf_atr"] + out["mem_atr"] + out["stab_atr"]

    # 9. Softmax wag
    exp_ma = np.exp(score_ma)
    exp_atr = np.exp(score_atr)
    denom = exp_ma + exp_atr + 1e-9

    out["w_ma"] = exp_ma / denom
    out["w_atr"] = exp_atr / denom

    # 10. Fuzja sygnałów
    atr_norm = (out["signal_atr"] + 1) / 2
    fused = out["w_ma"] * out["signal_ma"] + out["w_atr"] * atr_norm

    # 11. Emergentny sygnał
    out["signal_memory_adaptive"] = np.where(
        fused > 0.66, 1,
        np.where(fused < 0.33, -1, 0)
    )

    return out
