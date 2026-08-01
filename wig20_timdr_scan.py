
import yfinance as yf
import pandas as pd
import numpy as np

WIG20 = [
    "ALE.WA","ALR.WA","BDX.WA","CDR.WA","DNP.WA","EBP.WA",
    "KGH.WA","KRU.WA","KTY.WA","LPP.WA","MBK.WA","PCO.WA",
    "PEO.WA","PGE.WA","PKN.WA","PKO.WA","PZU.WA","TPE.WA","ZAB.WA","207.WA"
]

# Dla MODIVO - ticker to MOD.WA
WIG20 = ["ALE.WA","ALR.WA","BDX.WA","CDR.WA","DNP.WA","KGH.WA","KRU.WA","KTY.WA","LPP.WA","MBK.WA","MOD.WA","PCO.WA","PEO.WA","PGE.WA","PKN.WA","PKO.WA","PZU.WA","TPE.WA","ZAB.WA"]

def timdr_analyze(ticker, period="1y"):
    df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False)
    if len(df) < 50:
        return None
    close = df['Close']
    ret = close.pct_change().dropna()
    sharpe = (ret.mean()/ret.std()*np.sqrt(252)) if ret.std()!=0 else 0
    sharpe_n = 1/(1+np.exp(-sharpe))
    winrate_n = (ret>0).mean()
    cummax = close.cummax()
    dd = (close-cummax)/cummax
    dd_n = 1+dd.min()
    R_total = 0.4*sharpe_n + 0.3*winrate_n + 0.3*max(0,dd_n)
    
    high_low = df['High']-df['Low']
    tr = pd.concat([high_low, (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    last = float(close.iloc[-1])
    
    if R_total>0.75: dec="SILNE KUPUJ"
    elif R_total>0.6: dec="KUPUJ"
    elif R_total>0.5: dec="TRZYMAJ"
    elif R_total>0.4: dec="SPRZEDAJ"
    else: dec="SILNE SPRZEDAJ"
    
    return {"ticker":ticker,"cena":last,"R_total":round(float(R_total),4),"decyzja":dec,"SL":round(last-1.5*float(atr),2),"TP":round(last+2*float(atr),2)}

results = []
for t in WIG20:
    try:
        r = timdr_analyze(t)
        if r: results.append(r)
    except: pass

df_res = pd.DataFrame(results).sort_values("R_total", ascending=False)
print(df_res)
df_res.to_csv("wig20_timdr_scan.csv", index=False)
