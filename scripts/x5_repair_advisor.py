#!/usr/bin/env python3
"""Create human-reviewable repair suggestions from Guardian JSON.

This tool never edits website files, opens PRs, commits, or applies fixes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GUIDANCE = {
    "GitHub Pages / HTML": (
        "Zkontrolovat stav nasazení GitHub Pages, publikovanou větev/složku a HTTP odpověď.",
        "Neprovádět změny HTML, dokud není ověřeno, že jde o chybu nasazení.",
    ),
    "Open-Meteo": (
        "Prověřit HTTP status, odpověď API, parametry požadavku a případný limit služby.",
        "Ověřit stejný požadavek z prohlížeče; serverová dostupnost sama nepotvrzuje CORS.",
    ),
    "ECMWF IFS přes Open-Meteo": (
        "Prověřit endpoint ECMWF, podporované parametry a strukturu hodinových dat.",
        "Zachovat ostatní funkční modely; chybu ECMWF neopravovat vypnutím celé meteorologické vrstvy.",
    ),
    "MET Norway": (
        "Prověřit odpověď Locationforecast, síť a identifikační User-Agent.",
        "Při výpadku ponechat zřetelně označený jiný funkční zdroj; nevydávat uloženou kopii za živá data.",
    ),
    "ČHMÚ archiv": (
        "Prověřit generated_utc, observed_utc, aktualizační úlohu archivu a stáří jednotlivých stanic.",
        "Starší měření označit jako opožděná; nulové hodnoty z měření nepřevádět na potvrzení absence předpovězených srážek.",
    ),
}

def build_proposals(payload: dict) -> list[dict]:
    proposals = []
    for check in payload.get("checks", []):
        name = str(check.get("name", "Neznámá kontrola"))
        state = str(check.get("state", "WARN")).upper()
        if state == "OK":
            continue
        inspect, safe_action = GUIDANCE.get(
            name,
            ("Prověřit původní odpověď, časový údaj a poslední chybový záznam.", "Neprovádět změny bez reprodukce problému a testu."),
        )
        proposals.append({
            "component": name,
            "severity": "high" if state == "FAIL" else "review",
            "observed": str(check.get("detail", "")),
            "investigation": inspect,
            "safe_next_step": safe_action,
            "requires_human_approval": True,
            "auto_applied": False,
        })
    return proposals


def render(payload: dict, proposals: list[dict]) -> str:
    lines = [
        "# X-5 Guardian · návrhy oprav",
        f"Diagnostika: {payload.get('checked_at_utc', 'čas neuveden')}",
        "",
        "**Režim: pouze návrhy. Žádná změna zdrojového kódu nebyla provedena.**",
        "",
    ]
    if not proposals:
        lines.append("Nebyly nalezeny žádné položky vyžadující kontrolu.")
    for item in proposals:
        lines.extend([
            f"## {item['component']} · {item['severity']}",
            f"- Zjištění: {item['observed']}",
            f"- Prověřit: {item['investigation']}",
            f"- Bezpečný další krok: {item['safe_next_step']}",
            "- Vyžaduje lidské schválení: ano",
            "- Automaticky provedeno: ne",
            "",
        ])
    lines.append("> Návrhy jsou pravidlové. Před úpravou je nutné chybu reprodukovat, připravit změnu v testovací větvi a ověřit testy.")
    return "\n".join(lines) + "\n"


def main() -> int:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "x5-guardian-diagnostics.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    proposals = build_proposals(payload)
    report = render(payload, proposals)
    print(report)
    summary = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(report)
    Path("x5-repair-proposals.md").write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
