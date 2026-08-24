"""
generate_demo_csv.py — generuje JAWNIE SYNTETYCZNY zestaw danych OHLCV
do demonstracji (nie prawdziwe dane rynkowe - live pobieranie z Yahoo
Finance jest zablokowane w tym sandboksie, patrz README.md). Geometric
Brownian Motion z realistycznymi parametrami (dryf, zmiennosc), zeby
sygnaly MA/RSI mialy sens do przetestowania calego pipeline'u.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 260  # ok. rok sesji gieldowych
dates = pd.bdate_range("2025-08-18", periods=n)

mu, sigma = 0.0004, 0.017  # dzienny dryf/zmiennosc, rzedu duzej spolki
returns = rng.normal(mu, sigma, n)
# wstrzykujemy krotki trend spadkowy w srodku (zeby zobaczyc SPRZEDAJ tez)
returns[120:150] -= 0.006

close = 150 * np.cumprod(1 + returns)
open_ = np.empty(n)
open_[0] = close[0] * (1 - rng.normal(0, 0.003))
open_[1:] = close[:-1] * (1 + rng.normal(0, 0.003, n - 1))

daily_range = np.abs(rng.normal(0, 0.009, n)) + 0.003
high = np.maximum(open_, close) * (1 + daily_range)
low = np.minimum(open_, close) * (1 - daily_range)
volume = rng.integers(30_000_000, 90_000_000, n)

df = pd.DataFrame({
    "Date": dates.strftime("%Y-%m-%d"),
    "Open": open_.round(2),
    "High": high.round(2),
    "Low": low.round(2),
    "Close": close.round(2),
    "Volume": volume,
})
df.to_csv("demo_data.csv", index=False)
print(f"Zapisano demo_data.csv: {len(df)} wierszy, {dates[0].date()} .. {dates[-1].date()}")
print(f"Cena startowa: {close[0]:.2f}, koncowa: {close[-1]:.2f} ({(close[-1]/close[0]-1)*100:+.1f}%)")
