"""Manual-injected sections (e.g. HR bidding intel). Includes when the template has been filled in."""
from pathlib import Path

PLACEHOLDER = "（本周未录入"


def fetch(cfg: dict, prev: dict) -> dict:
    tpl = cfg.get("template") or ""
    p = Path(tpl)
    try:
        text = p.read_text(encoding="utf-8").strip()
    except Exception:
        return {"ok": False, "bullets": [f"_人工维护模板缺失（请创建 {tpl}）_"]}

    lines = [l for l in text.splitlines() if l.strip()]
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    if not body or PLACEHOLDER in body:
        return {"ok": False, "bullets": [f"_本周未人工录入，模板在 `{tpl}`，欢迎提交 PR 补充情报_"]}

    return {"ok": True, "bullets": [body], "note": "人工维护区"}
