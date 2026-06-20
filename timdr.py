# core/timdr.py

import numpy as np

def timdr_evaluate(config):
    """
    config: słownik zawierający:
      - T: opis pola (np. 'AAPL / 1D / OHLC')
      - I: dane (np. DataFrame z sygnałami)
      - M: modalność (np. 'trend-following')
      - It: horyzont czasu (np. '1y')
      - R: metryki spójności (np. sharpe, winrate, dd)
    Zwraca:
      - ocenę R_total
      - emergencję E (czy strategia jest obiektem czy szumem)
    """

    # 1. Ekstrakcja metryk
    sharpe = config["R"].get("sharpe", 0)
    winrate = config["R"].get("winrate", 0)
    dd = config["R"].get("drawdown", 1)

    # 2. Normalizacja (0–1)
    sharpe_n = np.tanh(sharpe)
    winrate_n = winrate
    dd_n = 1 - min(dd, 1)

    # 3. Rezonans R_total
    R_total = 0.5 * sharpe_n + 0.3 * winrate_n + 0.2 * dd_n

    # 4. Próg emergencji
    if R_total > 0.55:
        E = "obiekt (strategia stabilna)"
    elif R_total > 0.35:
        E = "pół-obiekt (niestabilna, ale rokująca)"
    else:
        E = "szum (brak emergencji)"

    return {
        "R_total": float(R_total),
        "E": E,
        "details": {
            "sharpe_n": float(sharpe_n),
            "winrate_n": float(winrate_n),
            "dd_n": float(dd_n)
        }
    }
