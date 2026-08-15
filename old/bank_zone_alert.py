import json
import urllib.request
import numpy as np
import pandas as pd
import yfinance as yf

# ==========================================
# KONFIGURACJA POWIADOMIEŃ (Uzupełnij własne dane)
# ==========================================
DISCORD_WEBHOOK_URL = ""  # Wklej tutaj URL Webhooka Discord
TELEGRAM_BOT_TOKEN = ""  # Wklej Token Bota Telegram
TELEGRAM_CHAT_ID = ""  # Wklej Chat ID


def send_discord_alert(message: str, webhook_url: str):
  """Wysyła sformatowane powiadomienie na serwer Discord."""
  if not webhook_url:
    return
  payload = {"content": message}
  headers = {"Content-Type": "application/json"}
  req = urllib.request.Request(
      webhook_url,
      data=json.dumps(payload).encode("utf-8"),
      headers=headers,
      method="POST",
  )
  try:
    with urllib.request.urlopen(req) as response:
      print("[DISCORD] Powiadomienie wysłane pomyślnie.")
  except Exception as e:
    print(f"[DISCORD BŁĄD] {e}")


def send_telegram_alert(message: str, bot_token: str, chat_id: str):
  """Wysyła powiadomienie tekstowe na Telegram."""
  if not bot_token or not chat_id:
    return
  url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
  payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
  headers = {"Content-Type": "application/json"}
  req = urllib.request.Request(
      url,
      data=json.dumps(payload).encode("utf-8"),
      headers=headers,
      method="POST",
  )
  try:
    with urllib.request.urlopen(req) as response:
      print("[TELEGRAM] Powiadomienie wysłane pomyślnie.")
  except Exception as e:
    print(f"[TELEGRAM BŁĄD] {e}")


def check_entry_zones_and_notify(tickers=["PKO.WA", "PEO.WA"]):
  """Analizuje kursy banków i wysyła alert przy trafieniu w strefę wejścia."""
  for ticker in tickers:
    try:
      df = yf.download(ticker, period="6mo", interval="1d", progress=False)
      if df.empty or len(df) < 30:
        continue

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

      # 1. Obliczenie ATR(14), EMA(20) oraz VWAP(20)
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
      ema20 = float(close.ewm(span=20).mean().iloc[-1])
      last_close = float(close.dropna().iloc[-1])

      tp_price = (high + low + close) / 3.0
      vwap20 = (tp_price * volume).rolling(20).sum() / volume.rolling(20).sum()
      current_vwap = float(vwap20.dropna().iloc[-1])

      # 2. Obliczenie wskaźnika OBV
      obv_change = np.where(
          close > close.shift(1), volume, np.where(close < close.shift(1), -volume, 0)
      )
      obv = pd.Series(obv_change, index=df.index).cumsum()
      obv_sma20 = obv.rolling(20).mean()

      is_accumulating = float(obv.iloc[-1]) > float(obv_sma20.dropna().iloc[-1])
      score_bonus = 1.10 if (is_accumulating and last_close >= current_vwap) else 1.00

      # 3. Wyznaczenie Strefy Wejścia (Pullback Zone)
      entry_target = min(last_close, max(ema20, current_vwap - 0.2 * atr))
      zone_upper = round(entry_target + 0.3 * atr, 2)
      zone_lower = round(entry_target - 0.3 * atr, 2)

      sl = round(entry_target - (1.5 * atr), 2)
      tp = round(entry_target + (2.5 * atr * score_bonus), 2)
      rr_ratio = round((tp - entry_target) / (entry_target - sl), 2)

      # 4. Warunek aktywacji alertu: Aktualny kurs w strefie [zone_lower, zone_upper]
      in_zone = zone_lower <= last_close <= zone_upper

      print(
          f"[{ticker}] Cena: {last_close:.2f} PLN | Strefa:"
          f" [{zone_lower} - {zone_upper}] PLN | W strefie: {in_zone}"
      )

      if in_zone:
        alert_msg = (
            f"🚨 **SYGNAŁ WEJŚCIA: {ticker}** 🚨\n\n"
            f"📈 **Cena rynkowa:** `{last_close:.2f} PLN`\n"
            f"🎯 **Strefa Akumulacji:** `{zone_lower:.2f} - {zone_upper:.2f} PLN`\n"
            f"⛔ **Stop Loss (SL):** `{sl:.2f} PLN`\n"
            f"🎯 **Take Profit (TP):** `{tp:.2f} PLN`\n"
            f"⚖️ **R/R Ratio:** `{rr_ratio}`\n"
            f"📊 **Status OBV:** {'AKUMULACJA (STRONG)' if is_accumulating else 'NEUTRALNY'}\n"
            f"📍 **VWAP (20d):** `{current_vwap:.2f} PLN`"
        )

        # Wysyłanie alertów (jeśli skonsolidowane URL są podane)
        if DISCORD_WEBHOOK_URL:
          send_discord_alert(alert_msg, DISCORD_WEBHOOK_URL)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
          send_telegram_alert(
              alert_msg, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
          )

    except Exception as e:
        print(f"Błąd analizy dla {ticker}: {e}")


# Uruchomienie skanera alertów
if __name__ == "__main__":
  check_entry_zones_and_notify(["PKO.WA", "PEO.WA"])
