# src/main.py — FULL WYPAS + REKOMENDACJE INWESTYCYJNE

import argparse
import sys
import numpy as np
import pandas as pd
from termcolor import colored

from core.timdr import timdr_evaluate
from data.loader import load_ohlc
from models.backtest import backtest_signals, compute_metrics
from models.signals import memory_adaptive_fused_signal


# ---------------------------------------------------------
# Pomocnicze kalkulacje i kolorowanie
# ---------------------------------------------------------

def colorize_emergence(E: str) -> str:
    if "obiekt" in E:
        return colored(E, "green")
    if "pół-obiekt" in E:
        return colored(E, "yellow")
    return colored(E, "red")


def colorize_recommendation(rec: str) -> str:
    if "KUP" in rec:
        return colored(rec, "green", attrs=["bold"])
    elif "SPRZEDAJ" in rec:
        return colored(rec, "red", attrs=["bold"])
    return colored(rec, "yellow", attrs=["bold"])


def calculate_atr(df: pd.DataFrame, window: int = 14) -> float:
    """Oblicza Ostatnią wartość ATR dla wyznaczenia dynamicznego SL/TP."""
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window).mean().iloc[-1]
    return float(atr) if not np.isnan(atr) else (df["Close"].iloc[-1] * 0.02)


def generate_recommendation(df: pd.DataFrame, signal_col: str = "signal_memory_adaptive"):
    """
    Tłumaczy OSTATNI sygnał z modelu na bezpośrednią rekomendację rynkową
    oraz kalkuluje poziomy zarządzania ryzykiem (SL/TP).
    """
    last_row = df.iloc[-1]
    last_signal = last_row[signal_col]
    current_price = float(last_row["Close"])
    
    # Przeliczanie ATR do ustawienia SL i TP
    atr = calculate_atr(df)
    
    # Interpretacja wartości sygnału (dostosuj progi, jeśli Twój model zwraca inne zakresem wartości!)
    if last_signal >= 0.75:
        action = "SILNE KUPUJ (STRONG BUY)"
        sl = current_price - (1.5 * atr)
        tp = current_price + (3.0 * atr)
    elif 0.2 < last_signal < 0.75:
        action = "KUPUJ (BUY)"
        sl = current_price - (1.5 * atr)
        tp = current_price + (2.5 * atr)
    elif -0.2 <= last_signal <= 0.2:
        action = "NEUTRALNIE / TRZYMAJ (HOLD)"
        sl = current_price - (2.0 * atr)
        tp = current_price + (2.0 * atr)
    elif -0.75 < last_signal < -0.2:
        action = "SPRZEDAJ (SELL)"
        sl = current_price + (1.5 * atr)
        tp = current_price - (2.5 * atr)
    else:
        action = "SILNE SPRZEDAJ (STRONG SELL)"
        sl = current_price + (1.5 * atr)
        tp = current_price - (3.0 * atr)

    return {
        "action": action,
        "signal_value": round(float(last_signal), 4),
        "price": round(current_price, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "atr": round(atr, 2)
    }


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

    # 3. Wygenerowanie rekomendacji dla OSTATNIEGO punktu
    rec = generate_recommendation(df, signal_col="signal_memory_adaptive")

    # 4. Backtest
    bt = backtest_signals(df, signal_col="signal_memory_adaptive")

    # 5. Metryki
    metrics = compute_metrics(bt)

    # 6. TIMDR
    config = {
        "T": f"{ticker} / {interval}",
        "I": df,
        "M": "memory-adaptive-fusion",
        "It": period,
        "R": metrics
    }

    result = timdr_evaluate(config)

    # 7. Output — SEKCJA REKOMENDACJI
    print(colored(">>> REKOMENDACJA INWESTYCYJNA <<<", "yellow", attrs=["bold"]))
    print("Decyzja:         ", colorize_recommendation(rec["action"]))
    print("Sygnał modelu:   ", colored(f"{rec['signal_value']}", "white"))
    print("Aktualna cena:   ", colored(f"{rec['price']}$", "white"))
    print("Stop Loss (SL):  ", colored(f"{rec['sl']}$", "red"))
    print("Take Profit (TP):", colored(f"{rec['tp']}$", "green"))
    print(colored("---------------------------------", "yellow"))

    print(colored("=== TIMDR RESULT ===", "magenta"))
    print("R_total:", colored(f"{result['R_total']:.4f}", "white"))
    print("Emergencja:", colorize_emergence(result["E"]))
    print("Szczegóły:", result["details"])
    print(colored("====================\n", "magenta"))

    if verbose:
        print(colored("=== OSTATNIE SYGNAŁY I REKOMENDACJE ===", "blue"))
        print(df[["Close", "signal_memory_adaptive"]].tail(10))

    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "rekomendacja": rec["action"],
        "sygnal": rec["signal_value"],
        "cena": rec["price"],
        "stop_loss": rec["sl"],
        "take_profit": rec["tp"],
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
    parser = argparse.ArgumentParser(description="Analizator giełdowy + TIMDR (wersja z rekomendacjami)")

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
        
        # Ładne wyświetlenie najważniejszych kolumn rekomendacji w konsoli dla wielu spółek
        summary_cols = ["ticker", "rekomendacja", "cena", "stop_loss", "take_profit", "R_total"]
        print(colored("\n=== PODSUMOWANIE BATCH ===", "cyan", attrs=["bold"]))
        print(df[summary_cols].to_string(index=False))

        if args.save:
            df.to_csv("batch_results.csv", index=False)
            print(colored("\nZapisano podsumowanie do: batch_results.csv", "green"))


if __name__ == "__main__":
    main()
