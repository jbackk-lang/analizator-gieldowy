# src/data/loader.py
import yfinance as yf
import pandas as pd

def load_ohlc(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    data = yf.download(ticker, period=period, interval=interval)
    data = data.dropna()
    return data
