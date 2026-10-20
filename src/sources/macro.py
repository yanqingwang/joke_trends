"""Macro dashboard: gold / DXY / 10Y yield / oil / S&P500 / CNY & JPY vs USD."""
from datetime import datetime
from src.util import fetch_json, fetch_text, fmt_num, pct
import xml.etree.ElementTree as ET

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart"
ECB = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def _y(sym: str) -> dict:
    """Yahoo 7d daily closes. Tolerant to occasionally missing candelier data."""
    j = fetch_json(f"{YAHOO}/{sym}?interval=1d&range=8d", timeout=20)
    res = (j.get("chart") or {}).get("result") or []
    if not res:
        raise ValueError(f"no data for {sym}")
    meta = res[0].get("meta") or {}
    quote = ((res[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    closes = [c for c in quote if c]
    return {"symbol": meta.get("symbol", sym), "price": meta.get("regularMarketPrice"),
            "closes": closes, "currency": meta.get("currency", "")}


def _gold_api() -> float:
    j = fetch_json("https://api.gold-api.com/price/XAU", timeout=15)
    return float(j["price"])


def _ecb() -> dict:
    txt = fetch_text(ECB, timeout=20)
    root = ET.fromstring(txt)
    cube = root.find(".//{*}Cube[@time]")
    rates = {e.get("currency"): float(e.get("rate")) for e in cube}
    return rates  # EUR=1


def fetch(cfg: dict, prev: dict) -> dict:
    bullets, ok_parts, state = [], [], {}

    # ---- gold: gold-api first, Yahoo GC=F fallback
    gold = None
    try:
        gold = _gold_api()
        ok_parts.append("gold-api")
    except Exception:
        try:
            g = _y("GC%3DF")
            gold = g["price"]
            ok_parts.append("yahoo-GC")
        except Exception:
            pass
    prev_gold = (prev or {}).get("gold")
    if gold:
        chg = ""
        if prev_gold:
            v, s = pct(gold, prev_gold)
            chg = f" {'▲' if v > 0 else '▼'} {v:+.1f}%"
        state["gold"] = gold
        bullets.append(f"🥇 **金 ${gold:,.0f}/oz**{chg}")
    else:
        bullets.append("_金价获取失败_")

    # ---- yahoo instruments
    ymap = [
        ("💵 美元指数 DXY", "DX-Y.NYB"),
        ("🛢️ WTI 原油", "CL%3DF"),
        ("📈 10Y 美债收益率", "%5ETNX"),
        ("📊 标普500", "%5EGSPC"),
    ]
    closes_cache = {}
    for label, sym in ymap:
        try:
            r = _y(sym)
            closes_cache[sym] = r
            p = r["price"] or (r["closes"][-1] if r["closes"] else None)
            chg = ""
            if p and len(r["closes"]) >= 2:
                v, s = pct(p, r["closes"][0])
                chg = f"（周 {v:+.1f}%）"
            if p is not None:
                state[sym] = p
                unit = "%" if "TNX" in sym else ""
                p_txt = f"{p:,.2f}" if abs(p) < 100000 else fmt_num(p)
                bullets.append(f"{label}: **{p_txt}{unit}** {chg}".strip())
                ok_parts.append(sym)
        except Exception:
            pass

    if not any(s in ok_parts for s in [y[1] for y in ymap]) and ok_parts == []:
        bullets.append("_Yahoo 宏观行情不可达（可能限流）_")

    # ---- FX via ECB
    prev_fx = (prev or {}).get("fx") or {}
    try:
        eur = _ecb()
        usd_rate = eur.get("USD")
        cny_rate = eur.get("CNY")
        jpy_rate = eur.get("JPY")
        fx_state = {}
        if usd_rate:
            fx_state["EUR/USD"] = usd_rate
            if cny_rate:
                ucn = cny_rate / usd_rate
                fx_state["USD/CNY"] = ucn
                bullets.append(f"💱 USD/CNY **{ucn:.4f}**")
            if jpy_rate:
                uj = jpy_rate / usd_rate
                fx_state["USD/JPY"] = uj
                bullets.append(f"💱 USD/JPY **{uj:.2f}**")
        state["fx"] = fx_state
        ok_parts.append("ecb-fx")
    except Exception:
        bullets.append("_ECB 汇率不可达_")

    return {
        "ok": bool(ok_parts),
        "bullets": bullets[:10],
        "note": "来源：gold-api.com · Yahoo Finance · 欧央行参考汇率（ECB）。DXY 为 ICE 指数走势，个别资产可能临时缺数。",
        "state": state,
    }
