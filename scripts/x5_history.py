#!/usr/bin/env python3
"""Build a bounded history of X-5 Guardian health checks (read-only)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_HISTORY = 100
VALID_STATES = {"OK", "WARN", "FAIL"}

def read_snapshot(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("checks"), list):
        raise ValueError("Diagnostika musí obsahovat seznam checks.")
    checks = []
    for item in data["checks"]:
        if not isinstance(item, dict):
            raise ValueError("Položka kontroly musí být objekt.")
        state = str(item.get("state", "WARN")).upper()
        if state not in VALID_STATES:
            state = "WARN"
        checks.append({
            "name": str(item.get("name", "Neznámá kontrola"))[:120],
            "state": state,
            "detail": str(item.get("detail", ""))[:500],
        })
    return {
        "checked_at_utc": str(data.get("checked_at_utc") or datetime.now(timezone.utc).isoformat()),
        "checks": checks,
    }

def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [row for row in data if isinstance(row, dict)][-MAX_HISTORY:]
    except (OSError, ValueError, json.JSONDecodeError):
        return []

def build_report(history: list[dict]) -> str:
    lines = [
        "# X-5 Guardian · historie kontrol",
        "",
        f"Počet uložených kontrol: **{len(history)}** (maximum {MAX_HISTORY})",
        "",
    ]
    if not history:
        lines.append("Zatím nejsou k dispozici žádné historické kontroly.")
        return "\n".join(lines) + "\n"
    names = sorted({c.get("name", "Neznámá kontrola") for row in history for c in row.get("checks", [])})
    lines.extend(["| Čas UTC | OK | WARN | FAIL |", "|---|---:|---:|---:|"])
    for row in history[-20:]:
        states = [c.get("state") for c in row.get("checks", [])]
        lines.append(
            f"| {row.get('checked_at_utc', 'neuvedeno')} | {states.count('OK')} | "
            f"{states.count('WARN')} | {states.count('FAIL')} |"
        )
    lines.extend(["", "## Vývoj jednotlivých zdrojů", ""])
    for name in names:
        states = []
        for row in history[-20:]:
            match = next((c for c in row.get("checks", []) if c.get("name") == name), None)
            if match:
                states.append(match.get("state", "WARN"))
        if states:
            lines.append(f"- **{name}:** " + " → ".join(states))
    lines.extend([
        "",
        "> Historie vychází pouze z automatických serverových kontrol. Neověřuje vykreslení stránky, CORS ani ovládání na tabletu.",
    ])
    return "\n".join(lines) + "\n"

def main() -> int:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "x5-guardian-diagnostics.json")
    history_path = Path(sys.argv[2] if len(sys.argv) > 2 else "guardian-history/history.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = read_snapshot(source)
    history = load_history(history_path)
    history.append(snapshot)
    history = history[-MAX_HISTORY:]
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = build_report(history)
    Path("x5-guardian-history.md").write_text(report, encoding="utf-8")
    print(report)
    summary = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(report)
    return 0

if __name__ == "__main__":
    sys.exit(main())
