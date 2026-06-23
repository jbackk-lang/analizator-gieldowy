## 🔗 Wszystkie modele i repozytoria
Pełna lista projektów znajduje się na stronie:
https://jbackk-lang.github.io
---

# analizator-giełdowy

df = load_ohlc("AAPL")
df = memory_adaptive_fused_signal(df)

bt = backtest_signals(df, signal_col="signal_memory_adaptive")
metrics = compute_metrics(bt)

config = {
    "T": "AAPL / 1D",
    
    "I": df,
    
    "M": "memory-adaptive-fusion",

       "It": "1y",
    "R": metrics
    
}

print(timdr_evaluate(config))
 Możesz też podać własny plik CSV z danymi OHLC — wystarczy zmienić loader, np.:

python
df = pd.read_csv("moje_dane.csv")
Wtedy cały analizator działa na Twoich danych zamiast Yahoo Finance.
