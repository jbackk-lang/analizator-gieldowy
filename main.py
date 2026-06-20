# src/main.py
from data.loader import load_ohlc
from models.signals import simple_signal

def main():
    df = load_ohlc("AAPL", period="1y")
    sig = simple_signal(df)
    print(sig.tail())

if __name__ == "__main__":
    main()
