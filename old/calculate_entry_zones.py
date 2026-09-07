from typing import List, Dict, Any
import numpy as np
import pandas as pd
import yfinance as yf

BANKING_TICKERS = ["PKO.WA", "PEO.WA", "SPL.WA", "MBK.WA", "ALR.WA"]


def calculate_entry_zones(tickers: List[str]) -> pd.DataFrame:
  results = []

  for t in tickers:
    # Pobieranie danych 6-miesięcznych (1d) z uwzględnieniem wolumenu
    df = yf.download(t, period="6mo", interval="1d", progress=False)
    if df.empty or len(df) < 30:
      continue

    # Spłaszczanie kolumn w przypadku obiektów MultiIndex z yfinance
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    volume = df["Volume"].squeeze()

    # 1. OBOWIĄZKOWE WSKAŹNIKI ZMIENNOŚCI I TRENDU (ATR + EMA20)
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

    atr = float(tr.iloc[-1])
    ema20 = float(close.ewm(span=20).mean().iloc[-1])
    last_close = float(close.iloc[-1])

    # 2. WSKAŹNIK OBV (ON-BALANCE VOLUME)
    obv_change = np.where(
        close > close.shift(1), volume, np.where(close < close.shift(1), -volume, 0)
    )
    obv = pd.Series(obv_change, index=df.index).cumsum()
    obv_sma20 = obv.rolling(20).mean()

    is_obv_accumulating = float(obv.iloc[-1]) > float(obv_sma20.iloc[-1])
    obv_slope_positive = float(obv.iloc[-1]) > float(obv.iloc[-5])

    # 3. WSKAŹNIK VWAP (ROLLING VWAP - 20 DNI)
    # Wyznaczenie średniej ceny ważonej wolumenem z ostatnich 20 sesji
    typical_price = (high + low + close) / 3.0
    vwap_20 = (typical_price * volume).rolling(20).sum() / volume.rolling(
        20
    ).sum()
    current_vwap = float(vwap_20.iloc[-1])

    price_above_vwap = last_close >= current_vwap

    # 4. OCENA KONSENSUSI AKUMULACJI (VOLUME VERIFICATION)
    # Akumulacja zachodzi, gdy OBV rosnie oraz cena trzyma sie blisko/powyzej VWAP
    volume_confirmed = is_obv_accumulating and obv_slope_positive

    if volume_confirmed and price_above_vwap:
      volume_status = "AKUMULACJA (STRONG)"
      score_bonus = 1.10
    elif volume_confirmed:
      volume_status = "AKUMULACJA (MODERATE)"
      score_bonus = 1.00
    else:
      volume_status = "DYSTRYBUCJA / BRAK PĘDU"
      score_bonus = 0.85

    # 5. WYCENA STREFY WEJŚCIA, SL ORAZ TP
    # Optymalne wejście w punkcie przeciażenia (Pullback do EMA20 lub VWAP)
    entry_target = min(
        last_close, max(ema20, current_vwap - 0.2 * atr)
    )  # Kupujemy na korekcie
    sl = entry_target - (1.5 * atr)
    tp = entry_target + (2.5 * atr * score_bonus)  # Zwiększamy TP przy akumulacji

    rr_ratio = (tp - entry_target) / (entry_target - sl)

    results.append({
        "Ticker": t,
        "Cena": round(last_close, 2),
        "VWAP (20d)": round(current_vwap, 2),
        "Optym. Wejście": round(entry_target, 2),
        "SL (Stop Loss)": round(sl, 2),
        "TP (Take Profit)": round(tp, 2),
        "R/R Ratio": round(rr_ratio, 2),
        "Status Wolumenu": volume_status,
        "OBV vs SMA20": "POWYŻEJ" if is_obv_accumulating else "PONIŻEJ",
    })

  return pd.DataFrame(results)


# Przykład użycia:
if __name__ == "__main__":
  df_zones = calculate_entry_zones(BANKING_TICKERS)
  print(df_zones.to_string(index=False))
