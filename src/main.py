"""joke_trends main orchestrator.

Usage:
    python -m src.main --profile joke   # public weekly report
    python -m src.main --profile hr     # private HR weekly report

Reads sources.yml, runs each enabled source, caches per-source state into
data/state-{profile}.json and renders reports/{year}-W{ww}.md + reports/weekly.md.
"""
import argparse
import datetime as dt
import importlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config          # noqa: E402
from src.render import render               # noqa: E402
from src import mailer as mail              # noqa: E402
from src.util import iso_week               # noqa: E402

REGISTRY = {
    "github_stars": "github_stars",
    "predictions": "predictions",
    "ai_models": "ai_models",
    "hotnets": "hotnets",
    "crypto": "crypto",
    "macro": "macro",
    "trade": "trade",
    "rss": "news",
    "hiring": "hiring",
    "research": "research",
    "manual": "manual",
}


def state_path(profile: str) -> Path:
    return REPO_ROOT / "data" / f"state-{profile}.json"


def load_state(profile: str) -> dict:
    p = state_path(profile)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(profile: str, state: dict) -> None:
    p = state_path(profile)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def run_source(entry: dict, prev_payload: dict) -> dict:
    stype = entry.get("type")
    mod_name = REGISTRY.get(stype)
    if not mod_name:
        return {"ok": False, "error": f"未知数据源类型 {stype}"}
    try:
        mod = importlib.import_module(f"src.sources.{mod_name}")
        return mod.fetch(entry, prev_payload or {})
    except Exception as e:  # noqa: BLE001 — one bad source must never kill the report
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=["joke", "hr"])
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()

    cfg = load_config(str(REPO_ROOT))
    profile = cfg["profiles"][args.profile]
    state = load_state(args.profile)
    prev_sources = state.get("sources") or {}

    results = []
    new_state = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "sources": {}}
    for entry in profile.get("sources", []):
        if not entry.get("enabled", True):
            continue
        key = entry.get("key", entry.get("type"))
        prev_payload = prev_sources.get(key) or {}
        res = run_source(entry, prev_payload)
        results.append({"cfg": entry, "res": res})
        if res.get("state") is not None:
            payload = dict(res["state"])
            payload.pop("charts", None)
            new_state["sources"][key] = payload
        print(f"[{key}] ok={res.get('ok')} bullets={len(res.get('bullets') or [])}", file=sys.stderr)

    manual_notes = None
    mn = profile.get("manual_notes")
    if mn:
        mp = REPO_ROOT / mn
        try:
            manual_notes = mp.read_text(encoding="utf-8")
        except Exception:
            manual_notes = None

    md = render(profile, results, manual_notes)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    year, wk = iso_week()
    fname = out_dir / f"{year}-{wk}.md"
    fname.write_text(md, encoding="utf-8")
    (out_dir / "weekly.md").write_text(md, encoding="utf-8")
    save_state(args.profile, new_state)
    print(f"报告已生成：{fname}（副本 weekly.md）", file=sys.stderr)

    # ---- optional email delivery (only if secrets present AND profile opts in)
    if mail.enabled(profile):
        from src.util import week_label
        try:
            mail.send(subject=f"[{profile.get('title', 'Trends')}] {week_label()} 周报",
                      md_text=md,
                      attach_path=str(fname))
            print("邮件已发送", file=sys.stderr)
        except Exception as e:
            print(f"邮件发送失败（不影响报告产出）：{type(e).__name__}: {e}", file=sys.stderr)
    elif profile.get("mail"):
        print("未配置 SMTP_USER/SMTP_PASS，跳过邮件发送", file=sys.stderr)


if __name__ == "__main__":
    main()
