# src/main.py

import sys
from data.loader import load_ohlc
from models.signals import memory_adaptive_fused_signal
from models.backtest import backtest_signals, compute_metrics
from core.timdr import timdr_evaluate


def main():
    # -----------------------------
    # 1. Argumenty CLI
    # -----------------------------
    if len(sys.argv) >= 2:
        ticker = sys.argv[1]
    else:
        ticker = "AAPL"

    if len(sys.argv) >= 3:
        period = sys.argv[2]
    else:
        period = "1y"

    if len(sys.argv) >= 4:
        interval = sys.argv[3]
    else:
        interval = "1d"

    print(f"\n=== ANALIZA: {ticker} | {period} | {interval} ===\n")

    # -----------------------------
    # 2. Pobranie danych
    # -----------------------------
    df = load_ohlc(ticker, period=period, interval=interval)

    # -----------------------------
    # 3. Generacja sygnału
    # -----------------------------
    df = memory_adaptive_fused_signal(df)

    # -----------------------------
    # 4. Backtest
    # -----------------------------
    bt = backtest_signals(df, signal_col="signal_memory_adaptive")

    # -----------------------------
    # 5. Metryki
    # -----------------------------
    metrics = compute_metrics(bt)

    # -----------------------------
    # 6. TIMDR
    # -----------------------------
    config = {
        "T": f"{ticker} / {interval}",
        "I": df,
        "M": "memory-adaptive-fusion",
        "It": period,
        "R": metrics
    }

    result = timdr_evaluate(config)

    # -----------------------------
    # 7. Wynik
    # -----------------------------
    print("=== TIMDR RESULT ===")
    print("R_total:", result["R_total"])
    print("Emergencja:", result["E"])
    print("Szczegóły:", result["details"])
    print("====================\n")


if __name__ == "__main__":
    main()
