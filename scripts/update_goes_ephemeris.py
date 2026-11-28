#!/usr/bin/env python3
"""Extract the latest daily GOES-R ephemeris records from NOAA NCEI."""
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
    pattern = re.compile(r"(dn_ephe-l2-orb1m_g" + str(sat) + r"_d(\\d{8})_v[\\w.-]+\\.nc)", re.I)
    for folder in months:
        html = get(folder).decode("utf-8", "replace")
        for href, day in pattern.findall(html):
            candidates.append((day, folder + href))
    if not candidates:
        raise RuntimeError(f"No daily ephemeris file found for GOES-{sat}")
    day, url = max(candidates, key=lambda item: item[0])
    return day, url

def scalar(var, index):
    value = var[index]
    if np.ma.is_masked(value):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result) or abs(result) > 1e20:
        return None
    return result

def extract(sat: int) -> dict:
    day, url = latest_file(sat)
    raw = get(url)
    with Dataset("inmemory.nc", mode="r", memory=raw) as ds:
        variables = {name.lower(): var for name, var in ds.variables.items()}
        def find(*names):
            for name in names:
                if name.lower() in variables:
                    return variables[name.lower()]
            raise RuntimeError(f"GOES-{sat}: missing NetCDF variable, expected one of {names}; got {list(ds.variables)}")
        epoch = find("Epoch", "time", "epoch")
        mlt = find("GM_LCT_T")
        gm_lat = find("GM_LAT")
        gsm_lat = find("GSM_LAT")
        units = getattr(epoch, "units", "")
        if "since" not in units.lower():
            raise RuntimeError(f"GOES-{sat}: unsupported epoch units {units!r}")
        times = num2date(epoch[:], units=units, calendar=getattr(epoch, "calendar", "standard"),
                         only_use_cftime_datetimes=False, only_use_python_datetimes=True)
        rows = []
        for i, stamp in enumerate(times):
            vals = (scalar(mlt, i), scalar(gm_lat, i), scalar(gsm_lat, i))
            if all(v is None for v in vals):
                continue
            dt = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
            rows.append((dt, vals))
        if not rows:
            raise RuntimeError(f"GOES-{sat}: no valid ephemeris records")
        dt, (mlt_value, gm_value, gsm_value) = max(rows, key=lambda row: row[0])
        return {
            "satellite": sat,
            "time_utc": dt.isoformat().replace("+00:00", "Z"),
            "mlt_hours": mlt_value,
            "gm_lat_deg": gm_value,
            "gsm_lat_deg": gsm_value,
            "source_file": url.rsplit("/", 1)[-1],
            "source_url": url,
            "source_day": day,
        }

def main():
    result = {
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "source": "NOAA NCEI GOES-R Level-2 Ephemeris, 1-minute daily files",
        "cadence": "PT1M",
        "note": "Archivní ephemerida; není to živý minutový feed. Každá družice nese vlastní čas posledního záznamu.",
        "satellites": {
            "18": extract(18),
            "19": extract(19),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["time_utc"] for k, v in result["satellites"].items()}, indent=2))
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
