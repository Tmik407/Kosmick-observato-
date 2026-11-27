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
NOAA_STATUS = BASE + "/space-weather-status.json"
ACE_ARCHIVE = BASE + "/ace-mag-archive.json"
GIRO_STATUS = BASE + "/giro-status.json"
IRTAM_STATUS = BASE + "/irtam-status.json"
checks: list[tuple[str, str, str]] = []
check_metadata: dict[str, dict] = {}
chmi_age_h: float | None = None


def get(url: str, accept: str = "application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read()
        return raw, dict(response.headers.items())


def add(name: str, state: str, detail: str, metadata: dict | None = None):
    checks.append((name, state, detail))
    if metadata:
        check_metadata[name] = metadata
    print(f"{state}: {name} — {detail}")


def parse_utc(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def age_minutes(value, now=None):
    stamp = parse_utc(value)
    if stamp is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - stamp).total_seconds() / 60.0)


def freshness_state(age, limit):
    return "fresh" if age is not None and age <= limit else "stale"


def check_json_freshness(name: str, url: str, fetched_field: str,
                         measurement_field: str | None, fetched_limit: int,
                         measurement_limit: int | None = None):
    """Check both publication time and, where available, actual observation time."""
    try:
        raw, _ = get(url)
        doc = json.loads(raw)
        now = datetime.now(timezone.utc)
        fetched_age = age_minutes(doc.get(fetched_field), now)
        measurement_age = age_minutes(doc.get(measurement_field), now) if measurement_field else None
        problems = []
        if fetched_age is None or fetched_age > fetched_limit:
            problems.append(f"publikace stará {fetched_age:.0f} min" if fetched_age is not None else "čas publikace chybí")
        if measurement_field and (measurement_age is None or measurement_age > (measurement_limit or fetched_limit)):
            problems.append(f"poslední měření staré {measurement_age:.0f} min" if measurement_age is not None else "čas měření chybí")
        state = "WARN" if problems else "OK"
        detail = f"publikováno {doc.get(fetched_field, 'neuvedeno')}; stáří publikace {fetched_age:.0f} min" if fetched_age is not None else "čas publikace chybí"
        if measurement_field:
            detail += f"; poslední měření {doc.get(measurement_field, 'neuvedeno')}; stáří {measurement_age:.0f} min" if measurement_age is not None else "; čas posledního měření chybí"
        if problems:
            detail += "; upozornění: " + ", ".join(problems)
        add(name, state, detail, {"freshness": {
            "status": "fresh" if not problems else "stale",
            "published_age_minutes": round(fetched_age, 1) if fetched_age is not None else None,
            "published_limit_minutes": fetched_limit,
            "measurement_age_minutes": round(measurement_age, 1) if measurement_age is not None else None,
            "measurement_limit_minutes": measurement_limit,
        }})
    except Exception as exc:
        add(name, "WARN", f"zdroj nedostupný nebo neplatný: {type(exc).__name__}: {exc}",
            {"freshness": {"status": "unavailable"}})


def check_noaa_status():
    try:
        raw, _ = get(NOAA_STATUS)
        doc = json.loads(raw)
        now = datetime.now(timezone.utc)
        published_age = age_minutes(doc.get("updated_utc"), now)
        sources = doc.get("source_status", {})
        problems = []
        if published_age is None or published_age > 15:
            problems.append("stavový soubor je starší než 15 minut nebo nemá čas")
        source_summary = {}
        for key in ("wind", "mag", "kp"):
            item = sources.get(key, {})
            measured_age = age_minutes(item.get("last_measurement_utc"), now)
            limit = int(item.get("freshness_limit_minutes", 10 if key != "kp" else 240))
            ok = item.get("request_status") == "success" and measured_age is not None and measured_age <= limit
            source_summary[key] = {
                "status": "fresh" if ok else "stale_or_unavailable",
                "age_minutes": round(measured_age, 1) if measured_age is not None else None,
                "limit_minutes": limit,
                "request_status": item.get("request_status"),
                "error": item.get("error"),
            }
            if not ok:
                problems.append(f"{key}: " + (f"měření staré {measured_age:.0f} min (limit {limit})" if measured_age is not None else "měření chybí") +
                                (f", požadavek {item.get('request_status')}" if item.get("request_status") != "success" else ""))
        state = "WARN" if problems else "OK"
        detail = f"stavový soubor {published_age:.0f} min starý" if published_age is not None else "čas aktualizace chybí"
        detail += "; " + "; ".join(f"{k}: {v['status']} ({v['age_minutes']} min)" for k, v in source_summary.items())
        if problems:
            detail += "; upozornění: " + ", ".join(problems)
        add("NOAA SWPC – sluneční vítr / IMF / Kp", state, detail, {
            "freshness": {"status": "fresh" if not problems else "stale",
                          "published_age_minutes": round(published_age, 1) if published_age is not None else None,
                          "sources": source_summary}
        })
    except Exception as exc:
        add("NOAA SWPC – sluneční vítr / IMF / Kp", "WARN",
            f"stavový soubor nedostupný nebo neplatný: {type(exc).__name__}: {exc}",
            {"freshness": {"status": "unavailable"}})


def check_giro_status():
    try:
        raw, _ = get(GIRO_STATUS)
        doc = json.loads(raw)
        now = datetime.now(timezone.utc)
        fetched_age = age_minutes(doc.get("fetched_utc"), now)
        stations = doc.get("stations", [])
        observed = [parse_utc(item.get("time")) for item in stations if isinstance(item, dict)]
        observed = [stamp for stamp in observed if stamp is not None]
        newest = max(observed) if observed else None
        measurement_age = max(0.0, (now - newest).total_seconds() / 60) if newest else None
        problems = []
        if fetched_age is None or fetched_age > 90:
            problems.append("snapshot nebyl obnoven během posledních 90 minut")
        if measurement_age is None or measurement_age > 90:
            problems.append("nejnovější ionosférické měření je starší než 90 minut nebo chybí")
        state = "WARN" if problems else "OK"
        detail = f"{len(stations)} stanic; poslední měření {newest.isoformat(timespec='minutes') if newest else 'chybí'}"
        detail += f"; stáří měření {measurement_age:.0f} min" if measurement_age is not None else ""
        detail += f"; staženo před {fetched_age:.0f} min" if fetched_age is not None else "; čas stažení chybí"
        if problems:
            detail += "; upozornění: " + ", ".join(problems)
        add("GIRO – ionosférická měření", state, detail, {"freshness": {
            "status": "fresh" if not problems else "stale",
            "published_age_minutes": round(fetched_age, 1) if fetched_age is not None else None,
            "measurement_age_minutes": round(measurement_age, 1) if measurement_age is not None else None,
            "stations": len(stations),
        }})
    except Exception as exc:
        add("GIRO – ionosférická měření", "WARN", f"snapshot nedostupný nebo neplatný: {type(exc).__name__}: {exc}",
            {"freshness": {"status": "unavailable"}})


def check_ace_archive():
    try:
        raw, _ = get(ACE_ARCHIVE)
        doc = json.loads(raw)
        now = datetime.now(timezone.utc)
        published_age = age_minutes(doc.get("updated"), now)
        rows = doc.get("rows", [])
        latest = max((int(row.get("t", 0)) for row in rows if isinstance(row, dict)), default=0)
        latest_stamp = datetime.fromtimestamp(latest / 1000, timezone.utc) if latest else None
        measurement_age = (now - latest_stamp).total_seconds() / 60 if latest_stamp else None
        problems = []
        if published_age is None or published_age > 120:
            problems.append("archiv nebyl stažen během posledních 120 minut")
        if measurement_age is None or measurement_age > 360:
            problems.append("nejnovější ACE měření je starší než 6 hodin nebo chybí")
        state = "WARN" if problems else "OK"
        detail = f"{len(rows)} záznamů; poslední měření {latest_stamp.isoformat(timespec='minutes') if latest_stamp else 'chybí'}"
        detail += f"; stáří měření {measurement_age:.0f} min" if measurement_age is not None else ""
        detail += f"; poslední stažení před {published_age:.0f} min" if published_age is not None else "; čas stažení chybí"
        if problems:
            detail += "; upozornění: " + ", ".join(problems)
        add("NASA ACE MAG archiv", state, detail, {"freshness": {
            "status": "fresh" if not problems else "stale",
            "published_age_minutes": round(published_age, 1) if published_age is not None else None,
            "measurement_age_minutes": round(measurement_age, 1) if measurement_age is not None else None,
            "records": len(rows),
        }})
    except Exception as exc:
        add("NASA ACE MAG archiv", "WARN", f"archiv nedostupný nebo neplatný: {type(exc).__name__}: {exc}",
            {"freshness": {"status": "unavailable"}})


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
        chmi_age_h = age_h
        state = "OK" if age_h is not None and age_h <= 6 else "WARN"
        detail = f"{len(stations)} stanic; nejnovější měření {newest.isoformat(timespec='minutes') if newest else 'nenalezeno'}"
        if age_h is not None:
            detail += f"; stáří {age_h:.1f} h"
        detail += f"; archiv Last-Modified {headers.get('Last-Modified', 'neuvedeno')}"
        add("ČHMÚ archiv", state, detail)
    except Exception as exc:
        add("ČHMÚ archiv", "WARN", f"archiv nedostupný nebo neplatný: {type(exc).__name__}: {exc}")

    check_giro_status()
    check_ace_archive()
    check_noaa_status()
    check_json_freshness("IRTAM – model elektronové hustoty", IRTAM_STATUS, "generated_utc", None, 1440)

    counts = {state: sum(1 for _, item_state, _ in checks if item_state == state) for state in ("OK", "WARN", "FAIL")}
    diagnoses = {
        "GitHub Pages / HTML": "Prověřit GitHub Pages deployment, cestu stránky a poslední workflow.",
        "Open-Meteo": "Prověřit HTTP odpověď, limit požadavků, síť a strukturu hourly.time.",
        "ECMWF IFS přes Open-Meteo": "Prověřit dostupnost endpointu ECMWF a parametry požadavku; jiné modely mohou fungovat nezávisle.",
        "MET Norway": "Prověřit odpověď API, síť a identifikační User-Agent; při výpadku ponechat jasně označenou zálohu.",
        "ČHMÚ archiv": "Prověřit aktualizační workflow archivu, generated_utc a observed_utc; stará měření neoznačovat jako aktuální.",
        "GIRO – ionosférická měření": "Prověřit hodinový čas stažení GIRO a dostupnost stanic; jednotlivé stanice mohou mít rozdílný čas posledního měření.",
        "NASA ACE MAG archiv": "Prověřit hodinové workflow NASA ACE a skutečný čas posledního řádku; starý archiv neprezentovat jako živá data.",
        "NOAA SWPC – sluneční vítr / IMF / Kp": "Prověřit pětiminutové workflow NOAA; samostatně rozlišit stáří slunečního větru, IMF a tříhodinového Kp indexu.",
        "IRTAM – model elektronové hustoty": "Prověřit poslední běh modelu. Čas modelovaného období má záměrné zpoždění a nesmí se zaměňovat za čas vytvoření souboru.",
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
        "checks": [
            {
                "name": name,
                "state": state,
                "detail": detail,
                **check_metadata.get(name, {}),
                **(
                    {
                        "freshness": {
                            "status": "fresh" if chmi_age_h <= 6 else "delayed" if chmi_age_h <= 12 else "stale",
                            "age_hours": round(chmi_age_h, 2),
                            "fresh_threshold_hours": 6,
                            "stale_threshold_hours": 12,
                        }
                    }
                    if name == "ČHMÚ archiv" and chmi_age_h is not None
                    else {}
                ),
            }
            for name, state, detail in checks
        ],
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
