"""Generic RSS + HN-Algolia news filter used for SaaS deals / AI funding / AI cases / Linux / hardware / HR news."""
from src.util import feed_items, clamp, escape_md

HN_ALGOLIA = "https://hn.algolia.com/api/v1"


def _hn(q: str, days: int = 12, limit: int = 8) -> list:
    import urllib.parse, time
    qq = urllib.parse.quote(q)
    url = f"{HN_ALGOLIA}/search?query={qq}&tags=story&numericFilters=created_at_i>{int(time.time()) - days*86400}&hitsPerPage={limit}"
    from src.util import fetch_json
    j = fetch_json(url, timeout=20)
    out = []
    for h in j.get("hits", []):
        out.append({
            "title": h.get("title", ""),
            "link": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
            "summary": (h.get("story_text") or "")[:180],
            "date": h.get("created_at", ""),
        })
    return out


def fetch(cfg: dict, prev: dict) -> dict:
    feeds = cfg.get("feeds") or []
    kws = [k.lower() for k in (cfg.get("keywords") or [])]
    limit = int(cfg.get("limit", 5))
    use_filter = bool(cfg.get("filter", True)) and bool(kws)
    items = []
    for url in feeds:
        try:
            for it in feed_items(url, limit=40):
                hay = ((it.get("title") or "") + " " + (it.get("summary") or "")).lower()
                score = sum(1 for k in kws if k in hay)
                if (not use_filter or score > 0):
                    it["_score"] = score
                    items.append(it)
        except Exception:
            continue

    hn_it = []
    hn_q = cfg.get("hn_query")
    if hn_q:
        try:
            hn_it = _hn(hn_q, days=int(cfg.get("hn_days", 12)), limit=8)
        except Exception:
            hn_it = []
    if hn_it and use_filter:
        hn_it = [i for i in hn_it if sum(1 for k in kws if k in ((i.get("title") or "") + " " + (i.get("summary") or "")).lower()) > 0] or hn_it[:3]

    if not items and not hn_it:
        return {"ok": False, "bullets": [f"_信源全部不可达：{', '.join(feeds) or '—'}_"]}

    # sort RSS by keyword score desc then keep newest among top
    items.sort(key=lambda x: (x.get("_score", 0)), reverse=True)
    picked = items[: max(1, limit - min(2, len(hn_it)))]
    picked = picked[: int(cfg.get("rss_cap", 4))]
    bullets = []
    for i in picked:
        bullets.append(f"· [{escape_md(clamp(i['title'], 120))}]({i['link']})")
    if hn_it:
        bullets.append("**Hacker News 讨论热点：**")
        for i in hn_it[: 2 if picked else 4]:
            bullets.append(f"· [{escape_md(clamp(i['title'], 120))}]({i['link']})")
    if not bullets:
        bullets = ["_本类目本周没有命中关键词的新闻，可能是风平浪静_"]

    return {"ok": bool(bullets), "bullets": bullets[: limit + 1], "note": "按关键词相关度排序"}
