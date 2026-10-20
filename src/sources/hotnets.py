"""Chinese hot-boards (Baidu / Weibo / Douyin / Toutiao best-effort) + (X via getdaytrends / trends24; GoogleTrends US)."""
import re
from src.util import fetch_json, fetch_text, fmt_num, escape_md, clamp

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


def _toutiao() -> list:
    # 头条接口防御性多候选；海外 IP 会 404，属于已知限制
    for url in ("https://www.toutiao.com/hot-json/hot/board/?origin=toutiao_pc",
                "https://www.toutiao.com/api/pc/hot_board?origin=toutiao_pc"):
        try:
            j = fetch_json(url, timeout=15)
            rows = []
            for item in (j.get("data") or [])[:6]:
                if not isinstance(item, dict):
                    continue
                title = item.get("Title") or item.get("title") or ""
                hot = item.get("HotValue") or item.get("hot_value") or 0
                readonly = item.get("Url") or item.get("url") or ""
                if title:
                    rows.append(f"{title}（热度 {fmt_num(hot)}）<{readonly}>")
            if rows:
                return rows
        except Exception:
            continue
    return []


def _baidu() -> list:
    j = fetch_json("https://top.baidu.com/api/board?platform=wise&tab=realtime", timeout=20)
    items = []
    for card in (j.get("data") or {}).get("cards") or []:
        stack = list(card.get("content") or [])
        while stack:
            n = stack.pop()
            if isinstance(n, dict):
                if n.get("word"):
                    items.append(n)
                stack += list(n.values())
            elif isinstance(n, list):
                stack += n
    rows = []
    for inner in items[:8]:
        w = inner.get("word") or ""
        if not w:
            continue
        hot = inner.get("hotScore") or inner.get("hot") or 0
        url = inner.get("url") or inner.get("rawUrl") or ""
        tag = inner.get("show") or ""
        desc = inner.get("desc") or ""
        sc = f"（热度 {fmt_num(hot)}）" if hot else ""
        hd = f" —— {clamp(desc, 90)}" if desc else ""
        line = f"**{tag}** {w}{sc}" if tag else f"{w}{sc}"
        if url:
            line += f" <{url}>"
        rows.append(line + hd)
    return rows


def _weibo() -> list:
    j = fetch_json(
        "https://weibo.com/ajax/side/hotSearch",
        headers={"Referer": "https://weibo.com/hot/search", "X-Requested-With": "XMLHttpRequest"},
        timeout=15,
    )
    rows = []
    for it in ((j.get("data") or {}).get("realtime") or [])[:8]:
        w = it.get("word") or ""
        if not w or it.get("is_ad"):
            continue
        num = it.get("num") or 0
        rows.append(f"{w}（热度 {fmt_num(num)}）")
    return rows[:6]


def _douyin() -> list:
    j = fetch_json("https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/", timeout=15)
    data = j.get("data") or []
    words = []
    if isinstance(data, dict):
        words = data.get("word_list") or []
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        words = data[0].get("word_list") or []
    rows = []
    for it in words[:6]:
        w = it.get("word") or ""
        if w:
            rows.append(f"{w}（热度 {fmt_num(it.get('hot_value'))}）")
    return rows


def _getdaytrends() -> list:
    html = fetch_text("https://getdaytrends.com/", timeout=25)
    rows = []
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for tr in soup.select("table tr"):
            a = tr.find("a", href=True)
            if a and ("hashtag" in a["href"] or "/search?q=" in a["href"] or a["href"].startswith("http")):
                text = a.get_text(strip=True)
                if text and len(text) > 1 and text not in [r for r in rows]:
                    rows.append(text)
    else:
        rows = re.findall(r"<a[^>]*>\s*([^<]{2,50})\s*</a>", html)
        rows = [r.strip() for r in rows if not r.strip().isdigit()][:8]
    return rows[:7]


def _trends24() -> list:
    for url in ("https://trends24.in/", "https://trends24.in/united-states/"):
        try:
            html = fetch_text(url, timeout=20)
            if not HAS_BS4:
                return re.findall(r"<a[^>]*>([^<]{2,60})</a>", html)[:7]
            soup = BeautifulSoup(html, "html.parser")
            ol = soup.find("ol", class_=re.compile("trend"))
            if ol:
                return [ (li.get_text() or "").strip() for li in ol.find_all("li")[:7] if li.get_text(strip=True) ]
        except Exception:
            continue
    return []


def _gtr_us() -> list:
    txt = fetch_text("https://trends.google.com/trending/rss?geo=US", timeout=20)
    if HAS_BS4:
        soup = BeautifulSoup(txt, "xml")
        titles = [(s.get_text() or "").strip() for s in soup.find_all("title")]
        return [t for t in titles[1:8] if t]
    import xml.etree.ElementTree as ET
    root = ET.fromstring(txt)
    return [(i.findtext("title") or "").strip() for i in root.findall("./channel/item")][:7]


def fetch(cfg: dict, prev: dict) -> dict:
    bullets, ok, missing = [], [], []

    # --- 中国区热榜（多平台互相备份，谁通谁上）
    cn_rows, cn_src = [], None
    for label, fn in (("百度", _baidu), ("微博", _weibo), ("抖音", _douyin), ("头条", _toutiao)):
        try:
            rows = fn()
            if rows:
                cn_rows, cn_src = rows, label
                break
        except Exception:
            continue
    if cn_rows:
        ok.append(cn_src)
        bullets.append(f"**🇨🇳 {cn_src}热榜：**")
        bullets += [f"· {escape_md(clamp(r, 150))}" for r in cn_rows[:5]]
    else:
        missing.append("中国热榜(百度/微博/抖音/头条)")

    # --- X / Twitter 热点（getdaytrends 先行，trends24 兜底）
    x_rows = None
    try:
        x_rows = _getdaytrends()
    except Exception:
        x_rows = None
    if not x_rows:
        try:
            x_rows = _trends24()
        except Exception:
            x_rows = None
    if x_rows:
        ok.append("X")
        bullets.append("**🌍 X/Twitter 热点：**")
        bullets += [f"· {escape_md(r)}" for r in x_rows[:5]]
    else:
        missing.append("X/Twitter")

    try:
        us = _gtr_us()
        if us:
            ok.append("GoogleTrends-US")
            bullets.append("**🇺🇸 美国搜索热点（Google Trends，可窥 TikTok/Reddit 舆情）：**")
            bullets += [f"· {escape_md(r)}" for r in us[:5]]
    except Exception:
        missing.append("GoogleTrends-US")

    if not ok:
        return {"ok": False, "bullets": ["_各热搜源本周全部不可达（网络封锁或改版）_"]}

    note = "本节来源：" + " · ".join(ok)
    if missing:
        note += " | 不可达：" + "、".join(missing)
    return {"ok": True, "bullets": bullets, "note": note}
