#!/usr/bin/env python3
"""Build live station observations from CHMI 10-minute open data."""
import concurrent.futures
import datetime as dt
import json
import pathlib
import sys
import time
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "chmi-stations-latest.json"
BASE = "https://opendata.chmi.cz/meteorology/climate/recent"
NOW_BASE = "https://opendata.chmi.cz/meteorology/climate/now"
HEADERS = {"User-Agent": "PredpovedPocasiCR/1.2 (CHMI open data)"}
# Standard CHMI WIGOS network plus additional 0-203 partner/automatic sites.
SUPPORTED_WSI_PREFIXES = ("0-20000-0-", "0-203-0-")
TODAY = dt.datetime.now(dt.timezone.utc).date()
ALIASES = {
    "T": "temperature_c", "H": "humidity_pct", "F": "wind_ms",
    "D": "wind_direction_deg", "Fmax": "wind_gust_ms",
    "P": "pressure_hpa", "RR": "precipitation_mm", "SCE": "snow_depth_cm"
}

def get_json(url):
    response = requests.get(url, headers=HEADERS, timeout=35)
    response.raise_for_status()
    return response.json()

def number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def fetch_station(station, stamp, base=BASE):
    url = f"{base}/data/10min/10m-{station['id']}-{stamp}.json"
    try:
        doc = get_json(url)
        values = doc.get("data", {}).get("data", {}).get("values", [])
        latest = {}
        for row in values:
            if len(row) < 6:
                continue
            _, element, when, raw_value, flag, quality = row[:6]
            value = number(raw_value)
            if value is None:
                continue
            old = latest.get(element)
            if old is None or str(when) > old["time"]:
                latest[element] = {"value": value, "time": str(when), "flag": flag, "quality": quality}
        if not latest:
            return None, None
        out = dict(station)
        out["data_source"] = "now" if base == NOW_BASE else "recent"
        out["measurements"] = latest
        out["elements"] = sorted(latest)
        for element, target in ALIASES.items():
            if element in latest:
                out[target] = latest[element]["value"]
        times = [item["time"] for item in latest.values()]
        out["observed_utc"] = max(times) if times else None
        out["quality_fields"] = {key: item["quality"] for key, item in latest.items()}
        return out, None
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return None, None
        return None, f"{station['name']} {stamp}: HTTP {exc.response.status_code if exc.response else 'error'}"
    except Exception as exc:
        return None, f"{station['name']} {stamp}: {exc}"

def fetch_station_with_fallback(station, today_stamp, yesterday_stamp):
    # /now obsahuje průběžně aktualizované soubory automatizovaných stanic.
    # /recent je záloha po kontrole a publikuje se zpravidla dvakrát denně.
    candidates = []
    if station["id"].startswith("0-20000-0-"):
        candidates.append((NOW_BASE, today_stamp))
    candidates.extend(((BASE, today_stamp), (BASE, yesterday_stamp)))
    for base, stamp in candidates:
        item, error = fetch_station(station, stamp, base)
        if item:
            return item, None
        if error:
            print(error, flush=True)
    return None, None

def main():
    meta = None
    meta_date = None
    for day in (TODAY, TODAY - dt.timedelta(days=1)):
        stamp = day.strftime("%Y%m%d")
        try:
            meta = get_json(f"{BASE}/metadata/meta1-{stamp}.json")
            meta_date = stamp
            break
        except Exception as exc:
            print(f"Metadata {stamp}: {exc}", flush=True)
    if not meta:
        raise RuntimeError("CHMI station metadata unavailable")

    stations = {}
    for row in meta.get("data", {}).get("data", {}).get("values", []):
        if len(row) < 6:
            continue
        wsi, ghid, name, lon, lat, elevation = row[:6]
        # Keep station identifiers for networks that publish recent 10-minute files.
        if not str(wsi).startswith(SUPPORTED_WSI_PREFIXES) or lon is None or lat is None:
            continue
        lon, lat = float(lon), float(lat)
        if not (12.0 <= lon <= 19.0 and 48.4 <= lat <= 51.2):
            continue
        stations[str(wsi)] = {
            "id": str(wsi), "name": str(name), "lon": lon, "lat": lat,
            "elevation_m": number(elevation) or 0
        }

    today_stamp = TODAY.strftime("%Y%m%d")
    yesterday_stamp = (TODAY - dt.timedelta(days=1)).strftime("%Y%m%d")
    result = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(fetch_station_with_fallback, station, today_stamp, yesterday_stamp)
                   for station in stations.values()]
        for future in concurrent.futures.as_completed(futures):
            item, error = future.result()
            if item:
                result.append(item)
            elif error:
                print(error, flush=True)
    result.sort(key=lambda item: item["name"])
    if not result:
        raise RuntimeError("No station observations retrieved")
    generated = dt.datetime.now(dt.timezone.utc)
    newest = max((s.get("observed_utc") or "") for s in result)
    payload = {
        "source": "ČHMÚ Open Data · meteorology/climate/recent/data/10min",
        "license": "CC BY 4.0",
        "generated_utc": generated.isoformat(timespec="seconds"),
        "metadata_date": meta_date,
        "observation_date": today_stamp,
        "station_count": len(result),
        "fresh_now_station_count": sum(1 for s in result if s.get("data_source") == "now"),
        "recent_fallback_station_count": sum(1 for s in result if s.get("data_source") == "recent"),
        "station_networks": {prefix: sum(1 for s in result if s["id"].startswith(prefix)) for prefix in SUPPORTED_WSI_PREFIXES},
        "stations": result,
        "latest_observation_utc": newest,
        "available_elements": sorted({e for s in result for e in s.get("elements", [])}),
        "note": "Automatizované stanice přednostně používají průběžně aktualizovaný adresář ČHMÚ /now. Ostatní stanice nebo chybějící aktuální soubory používají /recent jako zálohu; tento archiv se aktualizuje po kontrole zpravidla dvakrát denně. Dostupné prvky se liší podle pozorovacího programu. Prázdné hodnoty jsou vynechány, kvalita je převzata ze zdroje ČHMÚ."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    tmp.replace(OUT)
    print(f"CHMI station snapshot: {len(result)} stations; newest observation {newest}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CHMI station update failed: {exc}", file=sys.stderr)
        raise
