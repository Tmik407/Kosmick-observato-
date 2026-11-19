#!/usr/bin/env python3
"""Build a compact northern-stratosphere JSON cache from NOAA NOMADS GFS GRIB2."""
import datetime as dt
import json
import math
import os
import pathlib
import sys
import time
import tempfile
import requests
import numpy as np
from eccodes import codes_grib_new_from_file, codes_get, codes_get_array, codes_release

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "polar-vortex" / "latest.json"
POINTS = [(lat, lon) for lat in (60, 68, 76, 84, 88)
          for lon in (-157.5, -112.5, -67.5, -22.5, 22.5, 67.5, 112.5, 157.5)]
LEVELS = (10, 30, 50)
HOURS = tuple(range(0, 49, 3))
VARS = ("TMP", "HGT", "UGRD", "VGRD")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "KosmickaObservator-X5/1.0 (NOAA GFS backup cache)"})

def filter_url(day, cycle, hour):
    name = f"gfs.t{cycle:02d}z.pgrb2.0p25.f{hour:03d}"
    params = [("file", name)]
    params += [(f"lev_{lev}_mb", "on") for lev in LEVELS]
    params += [(f"var_{var}", "on") for var in VARS]
    params += [("subregion", ""), ("leftlon", "0"), ("rightlon", "360"),
               ("toplat", "90"), ("bottomlat", "60"),
               ("dir", f"/gfs.{day:%Y%m%d}/{cycle:02d}/atmos")]
    from urllib.parse import urlencode
    return "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?" + urlencode(params)

def fetch_bytes(url):
    response = SESSION.get(url, timeout=180)
    if response.status_code != 200:
        raise RuntimeError(f"NOMADS HTTP {response.status_code}: {response.text[:180]}")
    body = response.content
    if not body.startswith(b"GRIB"):
        preview = body[:240].decode("utf-8", "replace").replace("\\n", " ")
        raise RuntimeError("NOMADS nevrátil GRIB2 data: " + preview)
    return body

def nearest_indices(lats, lons):
    latv = np.asarray(lats, dtype=float)
    lonv = np.asarray(lons, dtype=float)
    result = []
    for lat, lon in POINTS:
        dlon = ((lonv - lon + 180.0) % 360.0) - 180.0
        dist = (latv - lat) ** 2 + (dlon * max(0.2, math.cos(math.radians(lat)))) ** 2
        result.append(int(np.nanargmin(dist)))
    return result

def decode_grib(body):
    found = {}
    # ecCodes' file reader requires a real file descriptor; BytesIO has no fileno().
    # Use a temporary binary file so the GRIB decoder can read the downloaded message.
    with tempfile.TemporaryFile(mode="w+b") as stream:
        stream.write(body)
        stream.seek(0)
        while True:
            gid = codes_grib_new_from_file(stream)
            if gid is None:
                break
            try:
                short = str(codes_get(gid, "shortName")).lower()
                level = int(codes_get(gid, "level"))
                typ = str(codes_get(gid, "typeOfLevel"))
                if typ not in ("isobaricInhPa", "isobaricInPa") or level not in LEVELS:
                    continue
                key = {"t": "temperature", "gh": "geopotential_height",
                       "u": "u", "v": "v"}.get(short)
                if not key:
                    continue
                # Stable array access across ecCodes Python binding versions.
                glat = codes_get_array(gid, "latitudes")
                glon = codes_get_array(gid, "longitudes")
                values = codes_get_array(gid, "values")
                if not (len(glat) == len(glon) == len(values)):
                    raise RuntimeError(f"GRIB pole array lengths differ: lat={len(glat)} lon={len(glon)} values={len(values)}")
                indices = nearest_indices(glat, glon)
                vals = np.asarray(values, dtype=float)
                picked = [float(vals[i]) if np.isfinite(vals[i]) else None for i in indices]
                found[(level, key)] = picked
            finally:
                codes_release(gid)
    return found

def main():
    now = dt.datetime.now(dt.timezone.utc)
    # Try newest operational cycles first; use f000 to establish availability.
    cycles = []
    for day in (now.date(), now.date() - dt.timedelta(days=1)):
        for cycle in (18, 12, 6, 0):
            stamp = dt.datetime.combine(day, dt.time(cycle), tzinfo=dt.timezone.utc)
            if stamp <= now + dt.timedelta(hours=1):
                cycles.append((day, cycle))
    chosen = None
    for day, cycle in cycles:
        try:
            first = fetch_bytes(filter_url(day, cycle, 0))
            chosen = (day, cycle, first)
            break
        except Exception as exc:
            print(f"Cycle {day} {cycle:02d}Z není připraven: {exc}", flush=True)
    if chosen is None:
        raise RuntimeError("Na NOMADS nebyl nalezen dostupný cyklus GFS.")
    day, cycle, first = chosen
    base = dt.datetime.combine(day, dt.time(cycle), tzinfo=dt.timezone.utc)
    rows = [{"hourly": {f"{name}_{lev}hPa": [] for lev in LEVELS
                        for name in ("temperature", "geopotential_height", "wind_speed", "wind_direction")}}
            for _ in POINTS]
    times = []
    for n, fh in enumerate(HOURS):
        if fh == 0:
            body = first
        else:
            # NOMADS recommends spacing scripted downloads to protect the service.
            time.sleep(10)
            body = fetch_bytes(filter_url(day, cycle, fh))
        fields = decode_grib(body)
        times.append((base + dt.timedelta(hours=fh)).strftime("%Y-%m-%dT%H:%M"))
        for lev in LEVELS:
            temp = fields.get((lev, "temperature"), [None] * len(POINTS))
            height = fields.get((lev, "geopotential_height"), [None] * len(POINTS))
            u = fields.get((lev, "u"), [None] * len(POINTS))
            v = fields.get((lev, "v"), [None] * len(POINTS))
            for p in range(len(POINTS)):
                uu, vv = u[p], v[p]
                speed = math.hypot(uu, vv) if uu is not None and vv is not None else None
                direction = (math.degrees(math.atan2(-uu, -vv)) % 360.0
                             if uu is not None and vv is not None else None)
                rows[p]["hourly"][f"temperature_{lev}hPa"].append(temp[p] - 273.15 if temp[p] is not None else None)
                rows[p]["hourly"][f"geopotential_height_{lev}hPa"].append(height[p])
                rows[p]["hourly"][f"wind_speed_{lev}hPa"].append(speed)
                rows[p]["hourly"][f"wind_direction_{lev}hPa"].append(direction)
        print(f"Zpracováno NOAA GFS f{fh:03d}", flush=True)
    payload = {
        "source": "NOAA NOMADS GFS 0.25° GRIB2",
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cycle_utc": base.strftime("%Y-%m-%dT%H:%MZ"),
        "step_hours": 3,
        "points": [{"lat": lat, "lon": lon} for lat, lon in POINTS],
        "times": times,
        "rows": rows
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    tmp.replace(OUT)
    print(f"Uloženo {OUT} · {len(rows)} bodů · {len(times)} kroků", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"NOAA backup failed: {exc}", file=sys.stderr)
        raise
