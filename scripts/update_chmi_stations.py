#!/usr/bin/env python3
"""Build compact live station observations from CHMI 10-minute open data."""
import datetime as dt
import json
import pathlib
import sys
import time
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "chmi-stations-latest.json"
BASE = "https://opendata.chmi.cz/meteorology/climate/recent"
S = requests.Session()
S.headers["User-Agent"] = "KosmickaObservator-X5/1.0 (CHMI open data)"
TODAY = dt.datetime.now(dt.timezone.utc).date()

def get_json(url):
    r = S.get(url, timeout=45)
    r.raise_for_status()
    return r.json()

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
    for row in meta["data"]["data"]["values"]:
        if len(row) < 6:
            continue
        wsi, ghid, name, lon, lat, elevation = row[:6]
        # The 10-minute synoptic/climatological stream has this WSI namespace.
        if not str(wsi).startswith("0-20000-0-") or lon is None or lat is None:
            continue
        if not (12.0 <= float(lon) <= 19.0 and 48.4 <= float(lat) <= 51.2):
            continue
        stations[str(wsi)] = {"id": str(wsi), "name": str(name), "lon": float(lon),
                              "lat": float(lat), "elevation_m": float(elevation or 0)}
    result = []
    dates_tried = []
    for day in (TODAY, TODAY - dt.timedelta(days=1)):
        stamp = day.strftime("%Y%m%d")
        dates_tried.append(stamp)
        pending = []
        for station in stations.values():
            code = station["id"]
            url = f"{BASE}/data/10min/10m-{code}-{stamp}.json"
            try:
                doc = get_json(url)
                values = doc.get("data", {}).get("data", {}).get("values", [])
                latest = {}
                for row in values:
                    if len(row) < 6:
                        continue
                    _, element, when, value, flag, quality = row[:6]
                    if value is None:
                        continue
                    # Preserve latest published value per element; quality is retained as metadata.
                    old = latest.get(element)
                    if old is None or str(when) > old["time"]:
                        latest[element] = {"value": float(value), "time": str(when),
                                           "flag": flag, "quality": quality}
                aliases = {"T": "temperature_c", "H": "humidity_pct", "F": "wind_ms",
                           "D": "wind_direction_deg", "Fmax": "wind_gust_ms",
                           "P": "pressure_hpa", "RR": "precipitation_mm",
                           "SCE": "snow_depth_cm"}
                obs = {target: latest[source]["value"] for source, target in aliases.items()
                       if source in latest}
                if not any(k in obs for k in ("temperature_c", "humidity_pct", "wind_ms")):
                    continue
                times = [latest[k]["time"] for k in aliases if k in latest]
                station_out = dict(station)
                station_out.update(obs)
                station_out["observed_utc"] = max(times) if times else None
                station_out["elements"] = sorted(latest.keys())
                station_out["quality_fields"] = {k: latest[k]["quality"] for k in aliases if k in latest}
                pending.append(station_out)
            except Exception as exc:
                print(f"{station['name']} {stamp}: {exc}", flush=True)
            time.sleep(0.08)
        if pending:
            result = pending
            break
    payload = {
        "source": "ČHMÚ Open Data · meteorology/climate/recent/data/10min",
        "license": "CC BY 4.0",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "metadata_date": meta_date,
        "observation_date": dates_tried[-1] if result else None,
        "station_count": len(result),
        "stations": result,
        "note": "Přímá měření stanic; dostupné prvky se liší podle pozorovacího programu. Kvalita je převzata ze zdroje ČHMÚ."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    tmp.replace(OUT)
    print(f"CHMI station snapshot: {len(result)} stations")
    if not result:
        raise RuntimeError("No station observations retrieved")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CHMI station update failed: {exc}", file=sys.stderr)
        raise
