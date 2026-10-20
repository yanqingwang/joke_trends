"""Frontier research: latest arXiv submissions across configured categories."""
import urllib.parse
from src.util import fetch_text, escape_md, clamp
import xml.etree.ElementTree as ET

ARXIV = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch(cfg: dict, prev: dict) -> dict:
    cats = cfg.get("arxiv_categories") or ["cs.AI", "cs.LG"]
    limit = int(cfg.get("arxiv_limit", 4))
    if limit <= 0:
        limit = 1
    q = " OR ".join(f"cat:{c}" for c in cats)
    url = (f"{ARXIV}?search_query={urllib.parse.quote(q)}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={limit * 3}")
    bullets = []
    try:
        root = ET.fromstring(fetch_text(url, timeout=30))
        entries = root.findall("a:entry", NS)
        picked = 0
        for e in entries:
            if picked >= min(limit, 3):
                break
            title = " ".join((e.findtext("a:title", default="", namespaces=NS) or "").split())
            link = (e.find("a:id", NS).text or "") if e.find("a:id", NS) is not None else ""
            summ = clamp(" ".join(((e.findtext("a:summary", default="", namespaces=NS) or "").split())), 160)
            if not title:
                continue
            bullets.append(f"🔬 **[{title}]({link})**\n  ### {summ}")
            picked += 1
        if not bullets:
            bullets = ["_arXiv 没有返回新论文（可能接口暂时抽风）_"]
    except Exception:
        bullets = ["_arXiv API 不可达，前沿论文雷达失灵_"]

    return {
        "ok": bool(bullets and "不可达" not in bullets[0] and "没有返回" not in bullets[0]),
        "bullets": bullets,
        "note": "来源：arXiv 最新提交（类目 " + ", ".join(cats) + "）；评测基准分数类快讯请看 AI 模型动态一节。",
    }
