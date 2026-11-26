#!/usr/bin/env python3
"""X-5 Guardian phase 1: read-only health checks for the WEATHER VORTEX page.

This is deterministic monitoring, not an LLM-based repair agent. It never writes
to the repository, changes the website, or stores credentials.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

BASE = "https://tmik407.github.io/Kosmick-observato-"
PAGE = BASE + "/mapa-cr-3d.html"
CHMI = BASE + "/data/chmi-stations-latest.json"
UA = "X5WeatherGuardian/1.0 (https://github.com/Tmik407/Kosmick-observato-)"
TIMEOUT = 20
checks: list[tuple[str, str, str]] = []


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
        newest = datetime.fromisoformat(times[0].replace("Z", "+00:00"))
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - newest.astimezone(timezone.utc)).total_seconds() / 3600
        add(name, "OK" if age_h < 3 else "WARN", f"časová osa dostupná; první termín {times[0]} (odchylka {age_h:.1f} h)")
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

    print("\n## Shrnutí")
    for state in ("OK", "WARN", "FAIL"):
        print(f"- {state}: {sum(1 for _, s, _ in checks if s == state)}")
    print("\nPoznámka: jde o serverovou dostupnost API. Tato kontrola nepotvrzuje CORS, vykreslení mapy ani chování prohlížeče na tabletu.")
    return 1 if any(state == "FAIL" for _, state, _ in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
