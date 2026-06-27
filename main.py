# src/main.py

from data.loader import load_ohlc
from models.signals import memory_adaptive_fused_signal
from models.backtest import backtest_signals, compute_metrics
from core.timdr import timdr_evaluate


def main():
    # 1. Pobranie danych
    df = load_ohlc("AAPL", period="1y", interval="1d")

    # 2. Generacja sygnału
    df = memory_adaptive_fused_signal(df)

    # 3. Backtest
    bt = backtest_signals(df, signal_col="signal_memory_adaptive")

    # 4. Metryki
    metrics = compute_metrics(bt)

    # 5. Ocena TIMDR
    config = {
        "T": "AAPL / 1D",
        "I": df,
        "M": "memory-adaptive-fusion",
        "It": "1y",
        "R": metrics
    }

    result = timdr_evaluate(config)

    # 6. Wynik
    print("\n=== TIMDR RESULT ===")
    print("R_total:", result["R_total"])
    print("Emergencja:", result["E"])
    print("Szczegóły:", result["details"])
    print("====================\n")


if __name__ == "__main__":
    main()
