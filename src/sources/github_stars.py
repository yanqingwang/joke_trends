"""GitHub star tracking: watchlist stars + weekly delta + new hot repos discovery."""
import datetime as dt
from src.util import fetch_json, fmt_num, escape_md

API = "https://api.github.com"


def fetch(cfg: dict, prev: dict) -> dict:
    watch = cfg.get("watchlist") or []
    headers = {"Accept": "application/vnd.github+json"}
    stars = {}
    for repo in watch:
        try:
            j = fetch_json(f"{API}/repos/{repo}", headers=headers)
            stars[repo] = int(j.get("stargazers_count", 0))
        except Exception:
            continue  # skip unreachable repo this week

    search_days = int(cfg.get("search_days", 30))
    since = (dt.datetime.utcnow() - dt.timedelta(days=search_days)).strftime("%Y-%m-%d")
    kw = cfg.get("search_keyword", "ai")
    new_hot = []
    try:
        q = f"{kw} created:>={since}"
        j = fetch_json(
            f"{API}/search/repositories?q={q.replace(' ', '+')}&sort=stars&order=desc&per_page={int(cfg.get('search_limit', 5))}",
            headers=headers,
        )
        for it in j.get("items", []):
            new_hot.append({
                "full_name": it["full_name"],
                "stars": it.get("stargazers_count", 0),
                "desc": (it.get("description") or "")[:120],
            })
    except Exception:
        pass

    prev_stars = (prev or {}).get("stars") or {}
    bullets = []
    for repo, cur in stars.items():
        old = prev_stars.get(repo)
        if old not in (None, 0) and cur != old:
            delta = cur - old
            sign = "▲" if delta > 0 else "▼"
            bullets.append(f"**{escape_md(repo)}** — ★ {fmt_num(cur)} 与上周比 {sign} {fmt_num(abs(delta))}")
        else:
            bullets.append(f"**{escape_md(repo)}** — ★ {fmt_num(cur)}")
    if not bullets:
        bullets.append("_GitHub API 本周不可用（限流或网络），下周再战_")

    new_lines = [f"💎 **{escape_md(x['full_name'])}** ★{fmt_num(x['stars'])} — {escape_md(x['desc'])}" for x in new_hot]
    return {
        "ok": bool(stars),
        "bullets": bullets[: int(cfg.get("max_bullets", 8))],
        "extra": ("**最近 30 天冒头的新 AI 仓库：**\n" + "\n".join(new_lines)) if new_lines else "",
        "state": {"stars": stars},
    }
