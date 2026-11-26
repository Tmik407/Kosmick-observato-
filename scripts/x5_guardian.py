#!/usr/bin/env python3
"""X-5 Guardian phase 1: read-only health checks for the WEATHER VORTEX page.

This is deterministic monitoring, not an LLM-based repair agent. It never writes
to the repository, changes the website, or stores credentials.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone

BASE = "https://tmik407.github.io/Kosmick-observato-"
PAGE = BASE + "/mapa-cr-3d.html"
CHMI = BASE + "/data/chmi-stations-latest.json"
UA = "X5WeatherGuardian/1.0 (https://github.com/Tmik407/Kosmick-observato-)"
TIMEOUT = 20
checks: list[tuple[str, str, str]] = []\nchmi_age_h: float | None = None


def get(url: str, accept: str = "application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read()
        return raw, dict(response.headers.items())


def add(name: str, state: str, detail: str):
    checks.append((name, state, detail))
    print(f"{state}: {name} — {detail}")


def forecast_check(name: str, url: str):
    try:
        raw, _ = get(url)
        payload = json.loads(raw)
        rows = payload if isinstance(payload, list) else [payload]
        if not rows or not rows[0].get("hourly", {}).get("time"):
            raise ValueError("odpověď neobsahuje hodinovou časovou osu")
        times = rows[0]["hourly"]["time"]
        # Forecast arrays can begin at local midnight; that is not the issue time.
        # Avoid incorrectly flagging a valid forecast as stale from its first slot.
        add(name, "OK", f"časová osa dostupná ({len(times)} termínů); první termín {times[0]}")
    except Exception as exc:
        add(name, "WARN", f"zdroj nedostupný nebo neplatná odpověď: {type(exc).__name__}: {exc}")


def main() -> int:
    print("# X-5 AI System Guardian · diagnostika")
    print(f"Kontrola UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print("Režim: pouze čtení; žádné automatické opravy ani zápisy do repozitáře.\n")

    try:
        raw, headers = get(PAGE, "text/html")
        html = raw.decode("utf-8", errors="replace")
        required = ("weatherModelSelect", "forecastTimeline", "weatherVortex", "loadWeather")
        missing = [token for token in required if token not in html]
        if missing:
            add("GitHub Pages / HTML", "FAIL", "chybí očekávané prvky: " + ", ".join(missing))
        else:
            add("GitHub Pages / HTML", "OK", f"stránka dostupná ({len(raw)} B); Last-Modified: {headers.get('Last-Modified', 'neuvedeno')}")
    except Exception as exc:
        add("GitHub Pages / HTML", "FAIL", f"stránku nelze načíst: {type(exc).__name__}: {exc}")

    common = "latitude=50.5&longitude=13.6&hourly=temperature_2m,precipitation&forecast_days=2&timezone=Europe%2FPrague"
    forecast_check("Open-Meteo", "https://api.open-meteo.com/v1/forecast?" + common)
    forecast_check("ECMWF IFS přes Open-Meteo", "https://api.open-meteo.com/v1/ecmwf?" + common)

    try:
        raw, _ = get("https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=50.5&lon=13.6")
        doc = json.loads(raw)
        series = doc.get("properties", {}).get("timeseries", [])
        if not series:
            raise ValueError("chybí properties.timeseries")
        add("MET Norway", "OK", f"časová řada dostupná ({len(series)} bodů; první {series[0].get('time', 'čas neuveden')})")
    except Exception as exc:
        add("MET Norway", "WARN", f"zdroj nedostupný nebo neplatná odpověď: {type(exc).__name__}: {exc}")

    try:
        raw, headers = get(CHMI)
        doc = json.loads(raw)
        stations = doc.get("stations", [])
        observed = []
        for station in stations:
            stamp = station.get("observed_utc")
            if stamp:
                try:
                    dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    observed.append(dt.astimezone(timezone.utc))
                except ValueError:
                    pass
        newest = max(observed) if observed else None
        age_h = (datetime.now(timezone.utc) - newest).total_seconds() / 3600 if newest else None
        state = "OK" if age_h is not None and age_h <= 6 else "WARN"
        detail = f"{len(stations)} stanic; nejnovější měření {newest.isoformat(timespec='minutes') if newest else 'nenalezeno'}"
        if age_h is not None:
            detail += f"; stáří {age_h:.1f} h"
        detail += f"; archiv Last-Modified {headers.get('Last-Modified', 'neuvedeno')}"
        add("ČHMÚ archiv", state, detail)
    except Exception as exc:
        add("ČHMÚ archiv", "WARN", f"archiv nedostupný nebo neplatný: {type(exc).__name__}: {exc}")

    counts = {state: sum(1 for _, item_state, _ in checks if item_state == state) for state in ("OK", "WARN", "FAIL")}
    diagnoses = {
        "GitHub Pages / HTML": "Prověřit GitHub Pages deployment, cestu stránky a poslední workflow.",
        "Open-Meteo": "Prověřit HTTP odpověď, limit požadavků, síť a strukturu hourly.time.",
        "ECMWF IFS přes Open-Meteo": "Prověřit dostupnost endpointu ECMWF a parametry požadavku; jiné modely mohou fungovat nezávisle.",
        "MET Norway": "Prověřit odpověď API, síť a identifikační User-Agent; při výpadku ponechat jasně označenou zálohu.",
        "ČHMÚ archiv": "Prověřit aktualizační workflow archivu, generated_utc a observed_utc; stará měření neoznačovat jako aktuální.",
    }
    lines = [
        "# X-5 AI System Guardian · diagnostický protokol",
        f"Kontrola UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "| Stav | Počet |", "|---|---:|",
        *(f"| {state} | {counts[state]} |" for state in ("OK", "WARN", "FAIL")),
        "",
        "## Výsledky kontrol",
        "| Kontrola | Stav | Detail |", "|---|---|---|",
        *(f"| {name} | {state} | {detail.replace('|', '/')} |" for name, state, detail in checks),
        "",
        "## Doporučené další kroky",
    ]
    issues = [(name, state, detail) for name, state, detail in checks if state != "OK"]
    diagnostic_payload = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": [\n            ({ "name": name, "state": state, "detail": detail, **({ "freshness": { "status": ("fresh" if chmi_age_h <= 6 else "delayed" if chmi_age_h <= 12 else "stale"), "age_hours": round(chmi_age_h, 2), "fresh_threshold_hours": 6, "stale_threshold_hours": 12 } } if name == "ČHMÚ archiv" and chmi_age_h is not None else {}) })\n            for name, state, detail in checks\n        ],
    }
    with open("x5-guardian-diagnostics.json", "w", encoding="utf-8") as output:
        json.dump(diagnostic_payload, output, ensure_ascii=False, indent=2)

    if issues:
        lines.extend(f"- **{name} ({state}):** {diagnoses.get(name, 'Prověřit zdroj a jeho poslední chybovou odpověď.')} Detail: {detail}" for name, state, detail in issues)
    else:
        lines.append("- V rozsahu těchto serverových kontrol nebyl zjištěn problém.")
    lines.extend([
        "",
        "> Omezení: serverová dostupnost API nepotvrzuje CORS, vykreslení mapy, JavaScript ani gesta v Android prohlížeči. Doporučení jsou pravidlová diagnostika, nikoli automatická oprava.",
    ])
    report = "\n".join(lines) + "\n"
    print("\n" + report)
    summary_path = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(report)
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
