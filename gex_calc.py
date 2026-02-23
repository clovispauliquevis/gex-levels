print("RODANDO SCRIPT NOVO")

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import math
import json

RISK_FREE = 0.05

def gamma_bs(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    return (math.exp(-d1**2 / 2) / math.sqrt(2 * math.pi)) / (S * sigma * math.sqrt(T))

def calculate_qqq_gex():

    ticker = "QQQ"
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")["Close"].iloc[-1]

    expirations = stock.options
    today = datetime.today().date()

    rows = []

    for exp in expirations[:3]:
        exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
        T = (exp_date - today).days / 365

        is_0dte = (exp_date == today)

        chain = stock.option_chain(exp)

        for side, df in [("call", chain.calls), ("put", chain.puts)]:
            for _, row in df.iterrows():
                if row["openInterest"] == 0:
                    continue

                strike = row["strike"]
                iv = row["impliedVolatility"]
                oi = row["openInterest"]

                gamma = gamma_bs(price, strike, T, RISK_FREE, iv)
                gex = gamma * oi * 100 * price

                if side == "put":
                    gex = -gex

                rows.append({
                    "strike": strike,
                    "gex": gex,
                    "side": side,
                    "is_0dte": is_0dte
                })

    df = pd.DataFrame(rows)

    grouped = df.groupby("strike")["gex"].sum().reset_index()
    grouped = grouped.sort_values("strike")
    grouped["cum"] = grouped["gex"].cumsum()

    gamma_flip = grouped.iloc[(grouped["cum"]).abs().argsort()[:1]]["strike"].values[0]
    max_gamma = grouped.iloc[grouped["gex"].abs().idxmax()]["strike"]
    min_gamma = grouped.iloc[grouped["gex"].abs().idxmin()]["strike"]

    puts = df[df["side"] == "put"]
    calls = df[df["side"] == "call"]

    put_wall = puts.nsmallest(1, "gex")["strike"].values[0]
    call_wall = calls.nlargest(1, "gex")["strike"].values[0]

    put_high = puts.nsmallest(2, "gex")["strike"].tolist()
    call_high = calls.nlargest(2, "gex")["strike"].tolist()

    puts_0 = df[(df["side"]=="put") & (df["is_0dte"])]
    calls_0 = df[(df["side"]=="call") & (df["is_0dte"])]

    put_wall_0 = puts_0.nsmallest(1,"gex")["strike"].values[0] if not puts_0.empty else None
    call_wall_0 = calls_0.nlargest(1,"gex")["strike"].values[0] if not calls_0.empty else None

    result = {
        "QQQ Put Wall": round(float(put_wall),2),
        "QQQ Call Wall": round(float(call_wall),2),
        "QQQ Put High Gamma-1": round(float(put_high[0]),2),
        "QQQ Put High Gamma-2": round(float(put_high[1]),2),
        "QQQ Call High Gamma-1": round(float(call_high[0]),2),
        "QQQ Call High Gamma-2": round(float(call_high[1]),2),
        "QQQ Put Wall 0DTE": round(float(put_wall_0),2) if put_wall_0 else None,
        "QQQ Call Wall 0DTE": round(float(call_wall_0),2) if call_wall_0 else None,
        "QQQ Max Gamma": round(float(max_gamma),2),
        "QQQ Min Gamma": round(float(min_gamma),2),
        "QQQ Gamma Flip": round(float(gamma_flip),2),
    }

    return result, price

def convert_to_mnq(levels, qqq_price):

    mnq_price = yf.Ticker("MNQ=F").history(period="1d")["Close"].iloc[-1]

    ratio = mnq_price / qqq_price

    mnq_levels = {}

    for key, value in levels.items():
        if value is None:
            continue
        new_key = key.replace("QQQ", "MNQ")
        mnq_levels[new_key] = round(value * ratio,2)

    return mnq_levels

if __name__ == "__main__":

    qqq_levels, qqq_price = calculate_qqq_gex()
    mnq_levels = convert_to_mnq(qqq_levels, qqq_price)

    final = {}
    final.update(qqq_levels)
    final.update(mnq_levels)
    final["Atualizado"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    with open("levels.json","w") as f:
        json.dump(final,f,indent=2)
