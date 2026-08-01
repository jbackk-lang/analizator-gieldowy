# src/main.py — ANALIZATOR GIELDOWY z REKOMENDACJAMI I TIMDR

import argparse
import sys
import numpy as np
import pandas as pd
from termcolor import colored

from core.timdr import timdr_evaluate, filter_recommendation_by_timdr
from data.loader import load_ohlc
from models.backtest import backtest_signals, compute_metrics
from models.signals import memory_adaptive_fused_signal


# ---------------------------------------------------------
# Formatting i Logika Rekomendacji
# ---------------------------------------------------------

def colorize_emergence(E: str) -> str:
    if "obiekt" in E and "pół" not in E:
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
    """Kalkulacja ATR na potrzeby dynamicznych poziomów SL/TP."""
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window).mean().iloc[-1]
    return float(atr) if not np.isnan(atr) else (float(df["Close"].iloc[-1]) * 0.02)


def generate_raw_recommendation(df: pd.DataFrame, signal_col: str = "signal_memory_adaptive") -> dict:
    """Tłumaczy surowy sygnał z modelu na rekomendację handlową oraz poziomy SL/TP."""
    last_row = df.iloc[-1]
    last_signal = float(last_row[signal_col])
    current_price = float(last_row["Close"])
    
    atr = calculate_atr(df)

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
        "signal_value": round(last_signal, 4),
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

    # 3. Surowa rekomendacja
    raw_rec = generate_raw_recommendation(df, signal_col="signal_memory_adaptive")

    # 4. Backtest & Metryki
    bt = backtest_signals(df, signal_col="signal_memory_adaptive")
    metrics = compute_metrics(bt)

    # 5. Ewaluacja TIMDR
    config = {
        "T": f"{ticker} / {interval}",
        "I": df,
        "M": "memory-adaptive-fusion",
        "It": period,
        "R": metrics
    }
    timdr_res = timdr_evaluate(config)

    # 6. Modyfikacja rekomendacji na podstawie TIMDR
    final_rec = filter_recommendation_by_timdr(raw_rec, timdr_res)

    # 7. Prezentacja wyników
    print(colored(">>> REKOMENDACJA INWESTYCYJNA <<<", "yellow", attrs=["bold"]))
    print("Decyzja:         ", colorize_recommendation(final_rec["action"]))
    print("Sugerowana Pozycja:", colored(final_rec["position_size"], "cyan"))
    print("Sygnał Modelu:   ", colored(f"{final_rec['signal_value']}", "white"))
    print("Aktualna Cena:   ", colored(f"{final_rec['price']}$", "white"))
    print("Stop Loss (SL):  ", colored(f"{final_rec['sl']}$", "red"))
    print("Take Profit (TP):", colored(f"{final_rec['tp']}$", "green"))
    print("Uwagi:           ", colored(final_rec["note"], "dark_grey"))
    print(colored("---------------------------------", "yellow"))

    print(colored("=== TIMDR RESULT ===", "magenta"))
    print("R_total:   ", colored(f"{timdr_res['R_total']:.4f}", "white"))
    print("Ufność:    ", colored(f"{timdr_res['confidence'] * 100:.0f}%", "white"))
    print("Emergencja:", colorize_emergence(timdr_res["E"]))
    print("Szczegóły: ", timdr_res["details"])
    if timdr_res["warnings"]:
        print("Ostrzeżenia:", colored(str(timdr_res["warnings"]), "yellow"))
    print(colored("====================\n", "magenta"))

    if verbose:
        print(colored("=== OSTATNIE SYGNAŁY ===", "blue"))
        print(df[["Close", "signal_memory_adaptive"]].tail(10))

    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "rekomendacja": final_rec["action"],
        "alokacja": final_rec["position_size"],
        "sygnal": final_rec["signal_value"],
        "cena": final_rec["price"],
        "stop_loss": final_rec["sl"],
        "take_profit": final_rec["tp"],
        "R_total": timdr_res["R_total"],
        "E": timdr_res["E"]
    }


# ---------------------------------------------------------
# Tryb Batch
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
    parser = argparse.ArgumentParser(description="Analizator giełdowy + TIMDR z modułem rekomendacyjnym")
    parser.add_argument("ticker", nargs="*", help="Ticker lub lista tickerów (np. AAPL BTC-USD TSLA)")
    parser.add_argument("--period", default="1y", help="Okres (np. 1y, 6mo, 5y)")
    parser.add_argument("--interval", default="1d", help="Interwał (np. 1d, 4h, 1wk)")
    parser.add_argument("--verbose", action="store_true", help="Pokaż więcej danych")
    parser.add_argument("--save", action="store_true", help="Zapisz wyniki do CSV")
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
        df_batch = analyze_batch(tickers, args.period, args.interval, args.verbose)
        summary_cols = ["ticker", "rekomendacja", "alokacja", "cena", "stop_loss", "take_profit", "R_total"]
        
        print(colored("\n=== PODSUMOWANIE BATCH ===", "cyan", attrs=["bold"]))
        print(df_batch[summary_cols].to_string(index=False))

        if args.save:
            df_batch.to_csv("batch_results.csv", index=False)
            print(colored("\nZapisano podsumowanie do: batch_results.csv", "green"))


if __name__ == "__main__":
    main()
