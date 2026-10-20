"""Polymarket prediction-market movers (best effort; gamma API is geo-filtered in some regions)."""
import json
from src.util import fetch_json, pct

GAMMA = "https://gamma-api.polymarket.com"


def fetch(cfg: dict, prev: dict) -> dict:
    try:
        j = fetch_json(
            f"{GAMMA}/markets?closed=false&order=volume24hr&ascending=false&limit=50",
            timeout=20,
        )
    except Exception:
        return {"ok": False, "bullets": ["_Polymarket gamma API 本周不可达（可能区域屏蔽），建议手动补充几个热门盘_"]}
    rows = []
    for m in j:
        prices = m.get("outcomePrices")
        try:
            prices = json.loads(prices) if isinstance(prices, str) else prices
            p = float(prices[0]) if prices else None
        except Exception:
            p = None
        if p is not None:
            rows.append({"q": (m.get("question") or "")[:150], "p_yes": p})

    kws = [k.lower() for k in (cfg.get("keywords") or [])]
    picked = rows if not kws else [r for r in rows if any(k in r["q"].lower() for k in kws)]
    picked = picked[: int(cfg.get("max_bullets", 6))] if picked else rows[:5]

    prev_q = (prev or {}).get("quotes") or {}
    bullets = []
    for r in picked:
        arrow, txt = "", ""
        old = prev_q.get(r["q"])
        if old is not None:
            d, s = pct(r["p_yes"], old)
            arrow = s
            txt = f"（上周 {old*100:.0f}%，Δ {d:+.1f}pp）"
        bullets.append(f"{arrow} {r['q']} — **P(Yes) {r['p_yes']*100:.0f}%**{txt}")

    return {
        "ok": True,
        "bullets": bullets,
        "note": "数据源：polymarket.com Gamma API · 24h 成交量前几名",
        "state": {"quotes": {r["q"]: r["p_yes"] for r in rows}},
    }
