"""Tech hiring pulse: HN "Who is hiring" thread activity + greenhouse/lever job-board counts."""
import re
from src.util import fetch_json, fmt_num

GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
LEVER = "https://api.lever.co/v0/postings/{board}?mode=json"
HN_ALGOLIA = "https://hn.algolia.com/api/v1"


def _latest_hiring_thread() -> dict:
    j = fetch_json(
        f"{HN_ALGOLIA}/search_by_date?tags=story,author_whoishiring&query=hiring&hitsPerPage=1",
        timeout=20,
    )
    hits = j.get("hits") or []
    if not hits:
        raise ValueError("no thread")
    return hits[0]


def _thread_stats(story_id: str, fn_keywords: list) -> dict:
    j = fetch_json(
        f"{HN_ALGOLIA}/search?tags=comment,story_{story_id}&hitsPerPage=400",
        timeout=25,
    )
    n = int(j.get("nbHits", 0))
    counts = {}
    for kw in fn_keywords:
        low = kw.lower()
        c = 0
        for h in j.get("hits", []):
            t = ((h.get("comment_text") or "").lower())
            if low in t:
                c += 1
        counts[kw] = c
    return {"jobs": n, "fn_counts": counts}


def _greenhouse(board: str) -> int:
    j = fetch_json(GREENHOUSE.format(board=board), timeout=15)
    return int((j.get("meta") or {}).get("total", 0))


def _lever(board: str) -> int:
    j = fetch_json(LEVER.format(board=board), timeout=15)
    return len(j or [])


def fetch(cfg: dict, prev: dict) -> dict:
    bullets, ok_parts, state = [], [], {}
    fn_keywords = cfg.get("fn_keywords") or []

    try:
        th = _latest_hiring_thread()
        title = (th.get("title") or "").strip()
        stats = _thread_stats(th.get("objectID"), fn_keywords)
        ok_parts.append("hn")
        prev_jobs = (prev or {}).get("thread_jobs")
        if prev_jobs is not None and prev_jobs != stats["jobs"]:
            v = stats["jobs"] - prev_jobs
            arrows = "▲" if v > 0 else "▼"
            bullets.append(f"📋 本月“{title}” 线程 **{stats['jobs']}** 条岗位评论（{arrows} {abs(v)}）")
        else:
            bullets.append(f"📋 本月“{title}” 线程 **{stats['jobs']}** 条岗位评论")
        top_fn = sorted(stats["fn_counts"].items(), key=lambda x: -x[1])
        fn_line = " · ".join(f"{k}: {c}" for k, c in top_fn[:6] if c)
        if fn_line:
            bullets.append(f"🧩 按方向分布（粗略关键词命中）：{fn_line}")
        state["thread_jobs"] = stats["jobs"]
        state["fn_counts"] = stats["fn_counts"]
    except Exception:
        bullets.append("_HN Who-is-hiring 线程获取失败_")

    boards = cfg.get("boards") or {}
    prev_boards = (prev or {}).get("boards") or {}
    board_state = {}
    for board in boards.get("greenhouse", []) or []:
        try:
            n = _greenhouse(board)
            board_state[f"gh:{board}"] = n
            old = prev_boards.get(f"gh:{board}")
            suffix = f"（上周 {old}，{'▲' if n > old else '▼' if n < old else '—'} {abs(n - old) if old else ''}）" if old else ""
            bullets.append(f"🏢 greenhouse **{board}** 在招 {n} 岗{suffix}")
            ok_parts.append(f"gh:{board}")
        except Exception:
            bullets.append(f"🏢 greenhouse **{board}** 枚举失败")
    for board in boards.get("lever", []) or []:
        try:
            n = _lever(board)
            board_state[f"lv:{board}"] = n
            old = prev_boards.get(f"lv:{board}")
            suffix = f"（上周 {old}）" if old else ""
            bullets.append(f"🏢 lever **{board}** 在招 {n} 岗{suffix}")
            ok_parts.append(f"lv:{board}")
        except Exception:
            pass
    state["boards"] = board_state

    return {
        "ok": bool(ok_parts),
        "bullets": bullets[:10],
        "note": "绿色通道：greenhouse/lever 公共岗位 API；线程统计为关键词粗匹配，仅供参考。",
        "state": state,
    }
