#!/usr/bin/env python3
"""Extract the latest daily GOES-R geographic/GSE ephemeris records from NOAA NCEI."""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from netCDF4 import Dataset, num2date
import numpy as np

ROOT = "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes"
OUT = Path("data/space-weather/goes-ephemeris.json")
NOW = datetime.now(timezone.utc)

def get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Kosmicka-observator-X5/1.0"})
    with urlopen(req, timeout=45) as response:
        return response.read()

def latest_file(sat: int) -> tuple[str, str]:
    base = f"{ROOT}/goes{sat}/l2/data/ephe-l2-orb1m"
    months = []
    for offset in range(0, 3):
        year, month = NOW.year, NOW.month - offset
        while month <= 0:
            year -= 1
            month += 12
        months.append(f"{base}/{year:04d}/{month:02d}/")
    candidates = []
    pattern = re.compile(r"(dn_ephe-l2-orb1m_g" + str(sat) + r"_d(\d{8})_v[\w.-]+\.nc)", re.I)
    for folder in months:
        html = get(folder).decode("utf-8", "replace")
        for filename, day in pattern.findall(html):
            candidates.append((day, folder + filename))
    if not candidates:
        raise RuntimeError(f"No daily ephemeris file found for GOES-{sat}")
    day, url = max(candidates, key=lambda item: item[0])
    return day, url

def value(var, index):
    raw = var[index]
    if np.ma.is_masked(raw):
        return None
    try:
        arr = np.asarray(raw, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return None
    arr = [float(x) if np.isfinite(x) and abs(float(x)) < 1e20 else None for x in arr]
    return arr[0] if len(arr) == 1 else arr

def extract(sat: int) -> dict:
    day, url = latest_file(sat)
    raw = get(url)
    with Dataset("inmemory.nc", mode="r", memory=raw) as ds:
        variables = {name.lower(): var for name, var in ds.variables.items()}
        def find(name):
            if name.lower() not in variables:
                raise RuntimeError(f"GOES-{sat}: missing NetCDF variable {name}; available: {list(ds.variables)}")
            return variables[name.lower()]
        epoch = find("time")
        geo = find("geo_llr")
        local_time = find("local_time")
        gse = find("gse_xyz")
        gse_local_time = find("gse_local_time")
        units = getattr(epoch, "units", "")
        if "since" not in units.lower():
            raise RuntimeError(f"GOES-{sat}: unsupported time units {units!r}")
        times = num2date(epoch[:], units=units, calendar=getattr(epoch, "calendar", "standard"),
                         only_use_cftime_datetimes=False, only_use_python_datetimes=True)
        rows = []
        for i, stamp in enumerate(times):
            geo_value, gse_value = value(geo, i), value(gse, i)
            if geo_value is None and gse_value is None:
                continue
            dt = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
            rows.append((dt, geo_value, value(local_time, i), gse_value, value(gse_local_time, i)))
        if not rows:
            raise RuntimeError(f"GOES-{sat}: no valid ephemeris records")
        dt, geo_value, geo_lt, gse_value, gse_lt = max(rows, key=lambda row: row[0])
        geo_value = geo_value if isinstance(geo_value, list) else []
        gse_value = gse_value if isinstance(gse_value, list) else []
        return {
            "satellite": sat,
            "time_utc": dt.isoformat().replace("+00:00", "Z"),
            "geo_lat_deg": geo_value[0] if len(geo_value) > 0 else None,
            "geo_lon_deg": geo_value[1] if len(geo_value) > 1 else None,
            "geo_radius_km": geo_value[2] if len(geo_value) > 2 else None,
            "geo_local_time_hours": geo_lt,
            "gse_x_km": gse_value[0] if len(gse_value) > 0 else None,
            "gse_y_km": gse_value[1] if len(gse_value) > 1 else None,
            "gse_z_km": gse_value[2] if len(gse_value) > 2 else None,
            "gse_local_time_hours": gse_lt,
            "source_file": url.rsplit("/", 1)[-1],
            "source_url": url,
            "source_day": day,
        }

def main():
    result = {
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "source": "NOAA NCEI GOES-R Level-2 Ephemeris, 1-minute daily files",
        "cadence": "PT1M",
        "note": "Produkt poskytuje GEO a GSE souřadnice a GEO místní čas; neobsahuje MLT ani geomagnetickou šířku.",
        "satellites": {"18": extract(18), "19": extract(19)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {"time": v["time_utc"], "geo_local_time": v["geo_local_time_hours"],
                          "geo_llr": [v["geo_lat_deg"], v["geo_lon_deg"], v["geo_radius_km"]]}
                      for k, v in result["satellites"].items()}, indent=2))
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
