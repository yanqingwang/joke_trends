"""Shared helpers: HTTP fetching (with UA + timeout), JSON, RSS, markdown escaping, dates."""
import datetime as dt
import json
import re
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
DEFAULT_TIMEOUT = 15


def fetch_bytes(url: str, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(2_000_000)


def fetch_json(url: str, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None):
    return json.loads(fetch_bytes(url, timeout, headers))


def fetch_text(url: str, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None) -> str:
    return fetch_bytes(url, timeout, headers).decode("utf-8", "ignore")


def today_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def iso_week() -> tuple[str, str]:
    """Returns (year, 'Www') like 2026, 'W43'."""
    d = dt.date.today().isocalendar()
    return str(d[0]), f"W{d[1]}"


def week_label() -> str:
    d = dt.date.today().isocalendar()
    return f"{d[0]} 年第 {d[1]} 周"


def clamp(text: str, n: int = 200) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def escape_md(text: str) -> str:
    return re.sub(r"([\\`*_\[\]])", r"\\\1", text or "")


def pct(cur: float, prev: float) -> tuple[float, str]:
    """(percent change, sign string) with safe None fallback."""
    if cur is None or prev in (None, 0):
        return 0.0, "?"
    v = (cur - prev) / prev * 100
    arrow = "▲" if v > 0 else ("▼" if v < 0 else "—")
    return v, arrow


def fmt_num(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "?"
    if abs(n) >= 1_000_000_000:
        return f"{n/1e9:.2f}B"
    if abs(n) >= 1_000_000:
        return f"{n/1e6:.2f}M"
    if abs(n) >= 1_000:
        return f"{n/1e3:.1f}k"
    return f"{n:g}"


def try_chain(candidates: list, labels: list = None):
    """Try a list of (label, callable) pairs; return first success or (None, all_errors)."""
    errors = []
    for i, (label, fn) in enumerate(candidates):
        try:
            return fn(), None
        except Exception as e:  # noqa: BLE001 — deliberate broad catch for graceful degradation
            errors.append(f"{label}: {type(e).__name__}")
    return None, errors


# ---------------- RSS / Atom (stdlib only) ----------------

def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s or "")


def feed_items(url: str, limit: int = 40, timeout: int = DEFAULT_TIMEOUT) -> list:
    """Parse RSS2/Atom into [{'title','link','summary','date'}], newest first."""
    import xml.etree.ElementTree as ET
    txt = fetch_text(url, timeout)
    root = ET.fromstring(txt.encode() if isinstance(txt, str) else txt)
    items = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for node in root.findall("./channel/item") or root.findall("./item"):
        title = (node.findtext("title") or "").strip()
        link = ((node.findtext("link") or "").strip()
                or ((node.find("atom:link", ns) is not None and node.find("atom:link", ns).get("href")) or "").strip())
        summ = clamp(_strip_html(node.findtext("description") or node.findtext("summary") or ""), 220)
        items.append({"title": title, "link": link, "summary": summ,
                      "date": (node.findtext("pubDate") or node.findtext("updated") or "").strip()})
    for node in root.findall("./atom:entry", ns):
        title = (node.findtext("atom:title", default="", namespaces=ns) or "").strip()
        ln = ""
        le = node.find("atom:link", ns)
        if le is not None:
            ln = (le.get("href") or "").strip()
        summ = clamp(_strip_html(node.findtext("atom:summary", default="", namespaces=ns)
                                 or node.findtext("atom:content", default="", namespaces=ns)), 220)
        items.append({"title": title, "link": ln, "summary": summ,
                      "date": (node.findtext("atom:updated", default="", namespaces=ns)
                               or node.findtext("atom:published", default="", namespaces=ns) or "").strip()})
    return items[:limit]
