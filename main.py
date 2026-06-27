# src/main.py — FULL WYPAS

import sys
import argparse
import pandas as pd
from termcolor import colored

from data.loader import load_ohlc
from models.signals import memory_adaptive_fused_signal
from models.backtest import backtest_signals, compute_metrics
from core.timdr import timdr_evaluate


# ---------------------------------------------------------
# Kolorowanie wyników TIMDR
# ---------------------------------------------------------

def colorize_emergence(E: str) -> str:
    if "obiekt" in E:
        return colored(E, "green")
    if "pół-obiekt" in E:
        return colored(E, "yellow")
    return colored(E, "red")


# ---------------------------------------------------------
# Analiza pojedynczego tickera
# ---------------------------------------------------------

def analyze_single(ticker: str, period: str, interval: str, verbose: bool):
    print(colored(f"\n=== ANALIZA: {ticker} | {period} | {interval} ===", "cyan"))

    # 1. Dane
    df = load_ohlc(ticker, period=period, interval=interval)
    if df is None or len(df) < 10:
        print(colored("Brak danych lub za mało świec.", "red"))
        return None

    # 2. Sygnał
    df = memory_adaptive_fused_signal(df)

    # 3. Backtest
    bt = backtest_signals(df, signal_col="signal_memory_adaptive")

    # 4. Metryki
    metrics = compute_metrics(bt)

    # 5. TIMDR
    config = {
        "T": f"{ticker} / {interval}",
        "I": df,
        "M": "memory-adaptive-fusion",
        "It": period,
        "R": metrics
    }

    result = timdr_evaluate(config)

    # 6. Output
    print(colored("=== TIMDR RESULT ===", "magenta"))
    print("R_total:", colored(f"{result['R_total']:.4f}", "white"))
    print("Emergencja:", colorize_emergence(result["E"]))
    print("Szczegóły:", result["details"])
    print(colored("====================\n", "magenta"))

    if verbose:
        print(colored("=== OSTATNIE SYGNAŁY ===", "blue"))
        print(df.tail(10))

    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "R_total": result["R_total"],
        "E": result["E"],
        "details": result["details"]
    }


# ---------------------------------------------------------
# Tryb batch — wiele tickerów naraz
# ---------------------------------------------------------

def analyze_batch(tickers, period, interval, verbose):
    results = []

    for t in tickers:
        r = analyze_single(t, period, interval, verbose)
        if r:
            results.append(r)

    return pd.DataFrame(results)


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

def build_cli():
    parser = argparse.ArgumentParser(description="Analizator giełdowy + TIMDR (full wypas)")

    parser.add_argument("ticker", nargs="*", help="Ticker lub tickery (np. AAPL BTC-USD TSLA)")
    parser.add_argument("--period", default="1y", help="Okres (np. 1y, 6mo, 5y)")
    parser.add_argument("--interval", default="1d", help="Interwał (np. 1d, 4h, 1wk)")
    parser.add_argument("--verbose", action="store_true", help="Pokaż więcej danych")
    parser.add_argument("--save", action="store_true", help="Zapisz wyniki do CSV")
    parser.add_argument("--silent", action="store_true", help="Bez kolorów i opisów")

    return parser


def main():
    parser = build_cli()
    args = parser.parse_args()

    tickers = args.ticker if args.ticker else ["AAPL"]

    if len(tickers) == 1:
        result = analyze_single(tickers[0], args.period, args.interval, args.verbose)
        if args.save and result:
            pd.DataFrame([result]).to_csv("result.csv", index=False)
            print(colored("Zapisano: result.csv", "green"))
    else:
        df = analyze_batch(tickers, args.period, args.interval, args.verbose)
        print(df)

        if args.save:
            df.to_csv("batch_results.csv", index=False)
            print(colored("Zapisano: batch_results.csv", "green"))


if __name__ == "__main__":
    main()
