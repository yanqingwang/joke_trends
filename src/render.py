"""Markdown report assembly."""
from src.util import week_label, today_iso


def _section(title: str, res: dict, max_items: int) -> str:
    bullets = res.get("bullets") or []
    if not isinstance(bullets, list):
        bullets = [str(bullets)]
    parts = [f"## {title}", ""]
    if res.get("chart"):
        parts.append('<div style="max-width:640px;margin:6px 0">' + res["chart"] + "</div>")
        parts.append("")
    has_sub_headers = any(b.strip().startswith("**") for b in bullets)
    shown = bullets[: (max_items * 6 if has_sub_headers else max_items)]
    parts.extend(shown)
    parts.append("")
    if res.get("extra"):
        parts.append(res["extra"])
        parts.append("")
    if res.get("note"):
        parts.append(f"> 💡 {res['note']}")
        parts.append("")
    return "\n".join(parts)


def render(profile: dict, results: list, manual_notes: str | None) -> str:
    title = profile.get("title", "Weekly Trends")
    tagline = profile.get("tagline", "")
    max_items = int(profile.get("max_items", 5))
    out = [f"# {title}", ""]
    out.append(f"**{week_label()}** · 生成于 {today_iso()}（UTC）")
    if tagline:
        out.append(f"> {tagline}")
    out.append("")

    ok = [r for r in results if r["res"].get("ok")]
    if ok:
        out += ["## 📌 一句话速览", ""]
        seen = 0
        for r in ok:
            bl = (r["res"].get("bullets") or [])
            # pick first real bullet: not a plain subheader and not a placeholder line
            cand = None
            for b in bl:
                clean = b.strip()
                if not clean or clean.startswith("_"):
                    continue
                stripped = clean.removeprefix("*").removesuffix("*").strip()
                if stripped.endswith("：") or stripped.endswith(":"):
                    continue
                cand = clean
                break
            if cand is None and bl:
                cand = bl[0].strip()
            if cand:
                body = cand.replace("\n  ### ", "：")
                out.append(f"- **{r['cfg'].get('title')}**：{body}")
                seen += 1
                if seen >= 6:
                    break
        out.append("")
        out.append("---")
        out.append("")

    for r in results:
        sec = r["cfg"].get("title", r["cfg"].get("key", "?"))
        res = r["res"]
        if not res.get("ok"):
            body = ""
            if res.get("bullets"):
                body = "\n".join(res.get("bullets")[:max_items])
            if not body:
                body = f"_{res.get('error') or '本周数据源全体失联，欢迎人工补充'}_"
            out += [f"## {sec}", "", body, ""]
            if res.get("note"):
                out += [f"> 💡 {res['note']}", ""]
            continue
        out.append(_section(sec, res, max_items))

    if manual_notes and manual_notes.strip():
        out += ["---", "", "## ✍️ 手动补充区（Manual Notes）", "", manual_notes.strip(), ""]

    state_ok = sum(1 for r in results if r["res"].get("ok"))
    out += ["---", "",
            f"**数据源可用率：{state_ok}/{len(results)}** · 报告由 joke_trends 自动化流水线每周生成，欢迎 PR 补充情报。",
            ""]
    return "\n".join(out)
