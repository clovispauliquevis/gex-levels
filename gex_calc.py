import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import math

ticker = "QQQ"
risk_free_rate = 0.05

def calculate_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    return (math.exp(-d1**2 / 2) / math.sqrt(2 * math.pi)) / (S * sigma * math.sqrt(T))

def calculate_gex():
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")["Close"].iloc[-1]

    expirations = stock.options
    today = datetime.today().date()

    exposure_by_strike = {}

    for exp in expirations[:2]:
        exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
        T = (exp_date - today).days / 365

        chain = stock.option_chain(exp)

        for side, df in [("call", chain.calls), ("put", chain.puts)]:
            for _, row in df.iterrows():
                strike = row["strike"]
                iv = row["impliedVolatility"]
                oi = row["openInterest"]

                gamma = calculate_gamma(price, strike, T, risk_free_rate, iv)

                gex = gamma * oi * 100 * price

                if side == "put":
                    gex = -gex

                exposure_by_strike[strike] = exposure_by_strike.get(strike, 0) + gex

    df = pd.DataFrame(list(exposure_by_strike.items()), columns=["strike", "gex"])
    df = df.sort_values("strike")
    df["cum"] = df["gex"].cumsum()

    gamma_flip = df.iloc[(df["cum"]).abs().argsort()[:1]]["strike"].values[0]

    put_wall = df[df["gex"] < 0].nsmallest(1, "gex")["strike"].values[0]
    call_wall = df[df["gex"] > 0].nlargest(1, "gex")["strike"].values[0]

    return {
        "QQQ Put Wall": round(float(put_wall), 2),
        "QQQ Call Wall": round(float(call_wall), 2),
        "QQQ Gamma Flip": round(float(gamma_flip), 2),
        "Atualizado": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }
