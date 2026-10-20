"""Crypto market mood: Fear&Greed index, BTC/ETH 7d, liquidation/crash news."""
from src.util import fetch_json, feed_items, fmt_num, pct
import re

FNG = "https://api.alternative.me/fng/?limit=8"
CG_MARKETS = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum&per_page=2&sparkline=false&price_change_percentage=7d"
NEWS_RSS = [
    ("google-news", "https://news.google.com/rss/search?q=crypto+liquidation+OR+crypto+crash&hl=en-US&gl=US&ceid=US:en"),
    ("cointelegraph", "https://cointelegraph.com/rss"),
]
NEWS_KW = re.compile(r"liquidat|crash|wiped out|爆仓|清算|暴跌", re.I)


def _fng():
    j = fetch_json(FNG, timeout=20)
    data = j.get("data") or []
    return [(int(d["value"]), d.get("value_classification", "")) for d in data]


def _coins():
    j = fetch_json(CG_MARKETS, timeout=25)
    return {c["id"]: {"price": c.get("current_price"),
                      "chg7d": c.get("price_change_percentage_7d_in_currency")} for c in j}


def _ychart(sym: str):
    j = fetch_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=8d",
        timeout=20,
    )
    res = (j.get("chart") or {}).get("result") or []
    if not res:
        raise ValueError("no result")
    quote = ((res[0].get("indicators") or {}).get("quote") or [{}])[0]
    closes = [c for c in (quote.get("close") or []) if c]
    if len(closes) < 2:
        raise ValueError("no closes")
    return closes


def _news():
    for label, url in NEWS_RSS:
        try:
            items = feed_items(url, limit=40)
            hits = [i for i in items if NEWS_KW.search((i.get("title") or "") + " " + (i.get("summary") or ""))] or items[:3]
            return label, hits[:3]
        except Exception:
            continue
    return None, []


def fetch(cfg: dict, prev: dict) -> dict:
    bullets, ok_parts, state, chart = [], [], {}, ""
    try:
        from src.svgchart import sparkline
        vals = _fng()
        if vals:
            v, s = pct(vals[-1][0], vals[-2][0])
            suffix = f" {'▲' if v > 0 else '▼'} {v:+.0f}%" if v else ""
            chart = sparkline([x[0] for x in vals])
            ok_parts.append("fng")
            state["fng"] = vals[-1][0]
            bullets.append(f"😱 **恐惧贪婪指数 {vals[-1][0]}（{vals[-1][1]}）**{suffix} — 7 天走势见下图")
    except Exception:
        bullets.append("_情绪指数获取失败_")

    coins = None
    for label, fn in (("coingecko", _coins),):
        try:
            coins = fn()
            ok_parts.append(label)
        except Exception:
            pass
    if not coins:
        try:
            closes = _ychart("BTC-USD")
            coins = {"bitcoin": {"price": closes[-1], "chg7d": pct(closes[-1], closes[0])[0]}}
            ok_parts.append("yahoo")
        except Exception:
            pass
    if coins:
        for sym, gid in (("BTC", "bitcoin"), ("ETH", "ethereum")):
            dta = coins.get(gid) or {}
            if not dta.get("price"):
                continue
            chg = dta.get("chg7d")
            chg_txt = f"，7 天 {chg:+.1f}%" if isinstance(chg, (int, float)) else ""
            state[f"p_{gid}"] = dta["price"]
            bullets.append(f"🪙 **{sym} ${fmt_num(dta['price'])}**{chg_txt}")
    else:
        bullets.append("_行情快照获取失败（CoinGecko / Yahoo 均不可达）_")

    label, hits = _news()
    if hits:
        ok_parts.append(f"news:{label}")
        bullets.append("**爆仓 / 暴跌相关头条：**")
        for i in hits:
            bullets.append(f"· [{i['title']}]({i['link']})")
    else:
        bullets.append("_爆仓/暴跌新闻暂缺，请看文末 Manual Notes 手动补充_")

    return {
        "ok": bool(ok_parts),
        "bullets": bullets,
        "chart": chart,
        "note": "来源：alternative.me 恐惧贪婪指数 · CoinGecko · 公开新闻 RSS（爆仓精确金额建议参考 coinglass.com 手动补充）",
        "state": state,
    }
