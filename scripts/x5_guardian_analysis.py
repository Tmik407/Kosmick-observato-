#!/usr/bin/env python3
"""Transparent rule-based analysis for X-5 Guardian diagnostics.

This is an explainable expert-rules layer, not a hosted LLM. It never edits
website files, opens PRs, or deploys changes.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from datetime import datetime, timezone

DIAG = Path(sys.argv[1] if len(sys.argv) > 1 else "x5-guardian-diagnostics.json")
HISTORY = Path(sys.argv[2] if len(sys.argv) > 2 else "guardian-history/history.json")

def main() -> int:
    data = json.loads(DIAG.read_text(encoding="utf-8"))
    checks = {str(c.get("name")): c for c in data.get("checks", []) if isinstance(c, dict)}
    history = []
    if HISTORY.exists():
        try:
            raw = json.loads(HISTORY.read_text(encoding="utf-8"))
            if isinstance(raw, list): history = raw[-100:]
        except (OSError, ValueError): pass

    findings = []
    def add(severity, title, likely_cause, impact, recommendation, confidence="střední"):
        findings.append({
            "severity": severity, "title": title, "likely_cause": likely_cause,
            "impact": impact, "recommendation": recommendation,
            "confidence": confidence, "automatic_repair": False
        })

    def state(name):
        item = checks.get(name, {})
        return str(item.get("state", "UNKNOWN")).upper()

    page, om, ecmwf, metno, chmi = (
        state("GitHub Pages / HTML"), state("Open-Meteo"),
        state("ECMWF IFS přes Open-Meteo"), state("MET Norway"), state("ČHMÚ archiv")
    )

    if page == "FAIL":
        add("critical", "Meteorologická stránka není dostupná",
            "HTTP kontrola stránky selhala nebo stránka neobsahuje očekávané prvky.",
            "Uživatelé nemusí načíst hlavní meteorologickou stránku.",
            "Prověřit poslední GitHub Pages deployment, URL a poslední změny HTML/JavaScriptu.",
            "vysoká")
    if om in ("WARN", "FAIL") and metno == "OK":
        add("warning", "Primární předpověď Open-Meteo je nedostupná, záloha MET Norway funguje",
            "Pravděpodobný je výpadek primárního API, limit požadavků nebo problém konkrétního endpointu; dostupnost samotné stránky je samostatná kontrola.",
            "Předpověď může běžet ze záložního globálního modelu a některé proměnné nebo časové kroky se mohou lišit.",
            "Ponechat MET Norway jako označenou zálohu; zkontrolovat HTTP odpověď Open-Meteo a opakovat kontrolu později.",
            "vysoká")
    elif om in ("WARN", "FAIL") and metno != "OK":
        add("critical", "Primární i záložní meteorologický zdroj mají problém",
            "Nedostupnost Open-Meteo i MET Norway může ukazovat na síťový problém, omezení požadavků nebo souběžný výpadek API.",
            "Automatické načtení předpovědi může být omezené; ověřit lokální cache a náhradní měření.",
            "Neprovádět automatické přepnutí bez kontroly dat; ověřit oba endpointy a zachovat jasné označení stáří cache.",
            "střední")
    if ecmwf in ("WARN", "FAIL"):
        add("warning", "Model ECMWF IFS neodpovídá",
            "Endpoint ECMWF přes Open-Meteo je nedostupný nebo vrací neplatnou strukturu.",
            "Porovnání modelů nemusí být dostupné; ostatní zdroje mohou fungovat nezávisle.",
            "Prověřit endpoint ECMWF a jeho parametry odděleně od hlavního Open-Meteo.")
    if chmi in ("WARN", "FAIL"):
        add("warning", "Archiv měření ČHMÚ vyžaduje kontrolu",
            "Archiv může být nedostupný, neobsahovat platné časy měření nebo mít příliš stará data.",
            "Pozorovaná měření nemusí reprezentovat aktuální stav.",
            "Zkontrolovat aktualizační workflow archivu a časy observed_utc; stará měření neoznačovat jako aktuální.")
    if not findings:
        add("info", "Všechny sledované serverové kontroly jsou v pořádku",
            "Pravidlová analýza nenašla známý problém v kontrolovaných zdrojích.",
            "Tento výsledek nepotvrzuje vykreslení mapy ani ovládání v Android prohlížeči.",
            "Pokračovat v běžném monitoringu a provést samostatný vizuální test na tabletu.",
            "střední")

    # Detect repeated non-OK checks in the bounded history.
    recurring = []
    for name in ("Open-Meteo", "ECMWF IFS přes Open-Meteo", "MET Norway", "ČHMÚ archiv", "GitHub Pages / HTML"):
        recent = [row for row in history[-8:] if isinstance(row, dict)]
        bad = sum(1 for row in recent for c in row.get("checks", [])
                  if isinstance(c, dict) and c.get("name") == name and c.get("state") in ("WARN", "FAIL"))
        if bad >= 3:
            recurring.append({"source": name, "non_ok_in_last_8": bad,
                              "recommendation": "Prověřit opakující se problém a historii běhů GitHub Actions."})
    analysis = {
        "engine": "X-5 Guardian Expert Rules 1.0",
        "mode": "explainable_rules_not_llm",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": "Zjištěno " + str(sum(1 for f in findings if f["severity"] in ("critical", "warning"))) + " upozornění; analýza je návrhová a nic automaticky neopravuje.",
        "findings": findings,
        "recurring_issues": recurring,
        "limitations": ["Kontrola API neověřuje CORS, vykreslení mapy, běh JavaScriptu ani dotyková gesta.",
                        "Příčiny jsou pravděpodobné hypotézy založené na dostupných stavech, nikoli definitivní důkaz.",
                        "Automatické opravy a nasazení jsou vypnuté."]
    }
    data["analysis"] = analysis
    DIAG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# X-5 Guardian · analytický protokol", "", analysis["summary"], "",
             "**Analytický režim:** vysvětlitelná pravidla; nejde o externí LLM.", ""]
    for f in findings:
        lines += [f"## {f['severity'].upper()} · {f['title']}", "",
                  f"- Pravděpodobná příčina: {f['likely_cause']}",
                  f"- Dopad: {f['impact']}",
                  f"- Doporučení: {f['recommendation']}",
                  f"- Jistota: {f['confidence']}",
                  "- Automatická oprava: vypnuta", ""]
    if recurring:
        lines += ["## Opakující se problémy", ""] + [f"- {x['source']}: {x['non_ok_in_last_8']} neúspěšných/varovných kontrol z posledních 8; {x['recommendation']}" for x in recurring]
    lines += ["", "> Guardian pouze analyzuje a doporučuje. Změny webu vyžadují samostatné schválení."]
    report = "\n".join(lines) + "\n"
    Path("x5-guardian-analysis.md").write_text(report, encoding="utf-8")
    summary = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out: out.write(report)
    print(report)
    return 0

if __name__ == "__main__":
    sys.exit(main())
