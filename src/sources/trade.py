"""Global trade pulse: FX basket via ECB + trade/tariff news via CNBC & Google News."""
from src.util import fetch_json, fetch_text, feed_items, pct
import re
import xml.etree.ElementTree as ET

ECB = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
NEWS = [
    ("google-news", "https://news.google.com/rss/search?q=global+trade+OR+tariffs&hl=en-US&gl=US&ceid=US:en"),
    ("cnbc-world", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
]
KW = re.compile(r"trade|tariff|export|import|shipment|container|freight|wto|export ban|supply chain", re.I)


def _ecb():
    txt = fetch_text(ECB, timeout=20)
    root = ET.fromstring(txt)
    cube = root.find(".//{*}Cube[@time]")
    return {e.get("currency"): float(e.get("rate")) for e in cube}


def _news():
    for label, url in NEWS:
        try:
            items = feed_items(url, limit=50)
            hits = [i for i in items if KW.search((i.get("title") or "") + " " + (i.get("summary") or ""))]
            if hits:
                return label, hits[:4]
        except Exception:
            continue
    return None, []


def fetch(cfg: dict, prev: dict) -> dict:
    bullets, state, ok_parts = [], {}, []

    prev_fx = (prev or {}).get("fx") or {}
    try:
        eur = _ecb()
        usd, cny, jpy, hkd = eur.get("USD"), eur.get("CNY"), eur.get("JPY"), eur.get("HKD")
        fx = {}
        if usd and cny:
            fx["USD/CNY"] = cny / usd
        if usd and jpy:
            fx["USD/JPY"] = jpy / usd
        if usd and hkd:
            fx["USD/HKD"] = hkd / usd
        if usd:
            fx["EUR/USD"] = usd
        bullets.append(f"💱 **EUR/USD** {usd:.4f}")
        for pair in ("USD/CNY", "USD/JPY", "USD/HKD"):
            if pair in fx:
                old = prev_fx.get(pair)
                suffix = f"（上周 {old:.2f}）" if old else ""
                bullets.append(f"💱 **{pair}** {fx[pair]:.2f} {suffix}")
        state["fx"] = fx
        ok_parts.append("ecb")
    except Exception:
        bullets.append("_ECB 汇率 baskets 不可达_")

    label, hits = _news()
    if hits:
        ok_parts.append(f"news:{label}")
        bullets.append("**贸易 / 关税要闻：**")
        for i in hits:
            bullets.append(f"· [{i['title']}]({i['link']})")

    return {
        "ok": bool(ok_parts),
        "bullets": bullets[:10],
        "note": "汇率反映贸易货币篮子对比欧元的走势；新闻来自公开 RSS。航运/集装箱指数暂无免 key API，欢迎手动补充。",
        "state": state,
    }
