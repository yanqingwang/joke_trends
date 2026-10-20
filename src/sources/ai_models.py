"""AI model popularity & release velocity: HF trending models + optional Artificial Analysis scores."""
import os
from src.util import fetch_json, fmt_num, pct

API_HF = "https://huggingface.co/api/models"
AA_MODELS = "https://api.artificialanalysis.ai/v2/models"


def fetch(cfg: dict, prev: dict) -> dict:
    limit = int(cfg.get("hf_limit", 8))
    hf_rows = None
    for url in (
        f"{API_HF}?sort=downloads30d&direction=-1&limit={limit}",
        f"{API_HF}?sort=downloads&direction=-1&limit={limit}",
    ):
        try:
            j = fetch_json(url, timeout=20)
            if isinstance(j, list) and j:
                hf_rows = j
                break
        except Exception:
            continue

    bullets = []
    cur_dl = {}
    if hf_rows:
        prev_dl = (prev or {}).get("downloads") or {}
        for m in hf_rows:
            mid = m.get("modelId") or m.get("id") or ""
            dl = m.get("downloads30d") or m.get("downloads") or 0
            cur_dl[mid] = dl
        for m in hf_rows:
            mid = m.get("modelId") or m.get("id") or ""
            dl = m.get("downloads30d") or m.get("downloads") or 0
            arrow, d_txt = "", ""
            old = prev_dl.get(mid)
            if old is not None:
                v, s = pct(dl or 0, old)
                arrow = s
                d_txt = f"{v:+.1f}%"
            bullets.append(f"🧠 **{mid}** — 30 天下载 {fmt_num(dl)} {arrow} {d_txt}".strip())

    extra = ""
    key = os.environ.get("AA_API_KEY")
    if key:
        try:
            j = fetch_json(AA_MODELS, headers={"x-api-key": key}, timeout=20)
            models = (j.get("data") or j or [])[:5]
            lines = []
            for m in models:
                name = m.get("name") or m.get("model_name") or ""
                idx = m.get("artificial_analysis_intelligence_index") or m.get("intelligence_index")
                if name and idx is not None:
                    lines.append(f"📈 **{name}** — Artificial Analysis 智能指数 {idx}")
            if lines:
                extra = "**第三方综合评测（Artificial Analysis）：**\n" + "\n".join(lines)
        except Exception:
            pass

    if not bullets:
        bullets = ["_Hugging Face API 本周不可达，模型热度数据缺失（下周再战）_"]

    return {
        "ok": bool(hf_rows),
        "bullets": bullets,
        "extra": extra,
        "note": "排名按 30 天下载量（HF 官方榜）；需要 LMArena 级综合评测分数时，可配 AA_API_KEY 环境变量获取 Artificial Analysis 数据。",
        "state": {"downloads": cur_dl},
    }
