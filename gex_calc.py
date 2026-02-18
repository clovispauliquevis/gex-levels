import json
from datetime import datetime, date
import math

import yfinance as yf
import pandas as pd
import numpy as np

SYMBOL = "QQQ"
MNQ_MULT = 4.0  # aproximação operacional: MNQ ~ QQQ * 4


def _safe_float(x):
    try:
        if x is None:
            return None
        x = float(x)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def _top4_high_gamma(strike_gex_series: pd.Series):
    # pega top 4 por |GEX|
    s = strike_gex_series.copy()
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return [None, None, None, None]
    top = s.abs().sort_values(ascending=False).head(4).index.tolist()
    # garantir 4
    while len(top) < 4:
        top.append(None)
    return top[:4]


def main():
    t = yf.Ticker(SYMBOL)
    expirations = t.options
    if not expirations:
        raise RuntimeError("Yahoo/yfinance não retornou expirations para QQQ.")

    today = date.today()

    all_calls = []
    all_puts = []

    for exp in expirations:
        chain = t.option_chain(exp)
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        calls["expiration"] = exp
        puts["expiration"] = exp

        all_calls.append(calls)
        all_puts.append(puts)

    calls = pd.concat(all_calls, ignore_index=True)
    puts = pd.concat(all_puts, ignore_index=True)

    calls["is_0dte"] = pd.to_datetime(calls["expiration"]).dt.date == today
    puts["is_0dte"] = pd.to_datetime(puts["expiration"]).dt.date == today

    # GEX proxy simples (igual você já vinha usando): OI * IV, puts negativo
    calls["GEX"] = calls["openInterest"].fillna(0) * calls["impliedVolatility"].fillna(0)
    puts["GEX"] = -1 * puts["openInterest"].fillna(0) * puts["impliedVolatility"].fillna(0)

    full = pd.concat([calls, puts], ignore_index=True)

    gex_by_strike = full.groupby("strike")["GEX"].sum().sort_index()
    gex_cum = gex_by_strike.cumsum()

    # Walls por OI total
    call_wall = _safe_float(calls.groupby("strike")["openInterest"].sum().idxmax())
    put_wall = _safe_float(puts.groupby("strike")["openInterest"].sum().idxmax())

    # 0DTE walls (se existir 0DTE no dia)
    calls_0 = calls[calls["is_0dte"]]
    puts_0 = puts[puts["is_0dte"]]
    call_wall_0 = _safe_float(calls_0.groupby("strike")["openInterest"].sum().idxmax()) if len(calls_0) else None
    put_wall_0 = _safe_float(puts_0.groupby("strike")["openInterest"].sum().idxmax()) if len(puts_0) else None

    # max/min gamma proxy (na prática: max/min GEX agregado)
    max_gamma = _safe_float(gex_by_strike.idxmax()) if not gex_by_strike.empty else None
    min_gamma = _safe_float(gex_by_strike.idxmin()) if not gex_by_strike.empty else None

    # gamma flip = strike onde |cumsum| é mínimo
    gamma_flip = _safe_float(gex_cum.abs().idxmin()) if not gex_cum.empty else None

    # IV extremos por strike (média)
    iv_by_strike = full.groupby("strike")["impliedVolatility"].mean().replace([np.inf, -np.inf], np.nan).dropna()
    max_iv = _safe_float(iv_by_strike.idxmax()) if not iv_by_strike.empty else None
    min_iv = _safe_float(iv_by_strike.idxmin()) if not iv_by_strike.empty else None

    # High gamma top4 (por |GEX|)
    hg = _top4_high_gamma(gex_by_strike)

    out = {
        "QQQ Put Wall": put_wall,
        "QQQ Call Wall": call_wall,
        "QQQ Put Wall 0DTE": put_wall_0,
        "QQQ Call Wall 0DTE": call_wall_0,
        "QQQ Max Gamma": max_gamma,
        "QQQ Min Gamma": min_gamma,
        "QQQ Gamma Flip": gamma_flip,
        "QQQ Max IV": max_iv,
        "QQQ Min IV": min_iv,
        "QQQ High Gamma-1": _safe_float(hg[0]),
        "QQQ High Gamma-2": _safe_float(hg[1]),
        "QQQ High Gamma-3": _safe_float(hg[2]),
        "QQQ High Gamma-4": _safe_float(hg[3]),
    }

    # conversão para MNQ
    def conv(v):
        v = _safe_float(v)
        return None if v is None else round(v * MNQ_MULT, 2)

    out.update({
        "MNQ Put Wall": conv(put_wall),
        "MNQ Call Wall": conv(call_wall),
        "MNQ Put Wall 0DTE": conv(put_wall_0),
        "MNQ Call Wall 0DTE": conv(call_wall_0),
        "MNQ Max Gamma": conv(max_gamma),
        "MNQ Min Gamma": conv(min_gamma),
        "MNQ Gamma Flip": conv(gamma_flip),
        "MNQ Max IV": conv(max_iv),
        "MNQ Min IV": conv(min_iv),
        "MNQ High Gamma-1": conv(hg[0]),
        "MNQ High Gamma-2": conv(hg[1]),
        "MNQ High Gamma-3": conv(hg[2]),
        "MNQ High Gamma-4": conv(hg[3]),
    })

    out["Atualizado"] = str(datetime.now())

    # remove chaves None (evita NaN/undefined no indicador)
    out = {k: v for k, v in out.items() if v is not None}

    with open("levels.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("OK: levels.json gerado.")


if __name__ == "__main__":
    main()
