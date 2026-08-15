import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf


def generate_interactive_bank_charts(tickers=["PKO.WA", "PEO.WA"]):
  for ticker in tickers:
    # 1. Pobieranie danych
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    if df.empty:
      print(f"Brak danych dla {ticker}")
      continue

    # Obsługa MultiIndex yfinance
    if isinstance(df.columns, pd.MultiIndex):
      close = df["Close"][ticker].squeeze()
      high = df["High"][ticker].squeeze()
      low = df["Low"][ticker].squeeze()
      volume = df["Volume"][ticker].squeeze()
    else:
      close = df["Close"].squeeze()
      high = df["High"].squeeze()
      low = df["Low"].squeeze()
      volume = df["Volume"].squeeze()

    # 2. Obliczenia wskaźników (ATR, EMA, VWAP, OBV)
    tr = (
        pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        )
        .max(axis=1)
        .rolling(14)
        .mean()
    )

    atr = float(tr.dropna().iloc[-1])
    ema20 = close.ewm(span=20).mean()

    # Rolling VWAP (20 dni)
    tp_price = (high + low + close) / 3.0
    vwap20 = (tp_price * volume).rolling(20).sum() / volume.rolling(20).sum()

    last_close = float(close.iloc[-1])
    current_vwap = float(vwap20.dropna().iloc[-1])
    current_ema = float(ema20.iloc[-1])

    # OBV
    obv_change = np.where(
        close > close.shift(1), volume, np.where(close < close.shift(1), -volume, 0)
    )
    obv = pd.Series(obv_change, index=df.index).cumsum()
    obv_sma20 = obv.rolling(20).mean()

    # 3. Parametry Handlowe (Strefa Wejścia, SL, TP)
    entry_target = min(last_close, max(current_ema, current_vwap - 0.2 * atr))
    entry_zone_upper = entry_target + 0.3 * atr
    entry_zone_lower = entry_target - 0.3 * atr

    sl = entry_target - (1.5 * atr)
    tp = entry_target + (2.75 * atr)  # Bonus za silną akumulację

    # 4. Budowanie Wykresu Plotly (2 podwykresy: Świece + Wolumen/OBV)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            f"{ticker} - Analiza Techniczna & Strefa Akumulacji",
            "Wolumen & OBV (On-Balance Volume)",
        ),
        row_heights=[0.75, 0.25],
    )

    # --- Wykres Świecowy ---
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"].squeeze(),
            high=high,
            low=low,
            close=close,
            name="Cena (OHLC)",
        ),
        row=1,
        col=1,
    )

    # Średnie i VWAP
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=vwap20,
            line=dict(color="orange", width=2),
            name="VWAP (20d)",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=ema20,
            line=dict(color="blue", width=1.5, dash="dot"),
            name="EMA (20)",
        ),
        row=1,
        col=1,
    )

    # Strefa Wejścia (Zacieniowany prostokąt)
    fig.add_hrect(
        y0=entry_zone_lower,
        y1=entry_zone_upper,
        fillcolor="rgba(255, 215, 0, 0.25)",
        line_width=1,
        line_color="gold",
        row=1,
        col=1,
        annotation_text="Strefa Wejścia (Pullback)",
        annotation_position="top left",
    )

    # Linie Poziomów SL i TP
    fig.add_hline(
        y=sl,
        line_color="crimson",
        line_dash="dash",
        line_width=2,
        annotation_text=f"SL: {sl:.2f} zł",
        annotation_position="bottom right",
        row=1,
        col=1,
    )

    fig.add_hline(
        y=tp,
        line_color="forestgreen",
        line_dash="dash",
        line_width=2,
        annotation_text=f"TP: {tp:.2f} zł",
        annotation_position="top right",
        row=1,
        col=1,
    )

    # --- Podwykres Wolumenu / OBV ---
    colors = [
        "green" if c >= o else "red"
        for c, o in zip(close, df["Open"].squeeze())
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=volume,
            marker_color=colors,
            opacity=0.4,
            name="Wolumen",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=obv,
            line=dict(color="purple", width=2),
            name="OBV",
            yaxis="y3",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=obv_sma20,
            line=dict(color="gray", width=1, dash="dot"),
            name="OBV SMA20",
            yaxis="y3",
        ),
        row=2,
        col=1,
    )

    # Layout i Stylizacja
    fig.update_layout(
        title=f"Wykres Taktyczny: {ticker} | R/R Ratio: {((tp-entry_target)/(entry_target-sl)):.2f}",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=750,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )

    fig.update_yaxes(title_text="Cena (PLN)", row=1, col=1)
    fig.update_yaxes(title_text="Wolumen", row=2, col=1)

    # Wyświetlenie interaktywnego wykresu
    fig.show()


# Uruchomienie generowania wykresów
if __name__ == "__main__":
  generate_interactive_bank_charts(["PKO.WA", "PEO.WA"])
