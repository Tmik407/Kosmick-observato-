#!/usr/bin/env python3
"""Download and aggregate ECMWF IFS 10 hPa fields for the X-5 polar-vortex viewer.
The job retrieves one forecast step and publishes a compact, versioned JSON product.
"""
from __future__ import annotations
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from eccodes import (
    codes_get, codes_get_values, codes_grib_new_from_file, codes_release,
)
from ecmwf.opendata import Client

OUT = Path("data/polar-vortex-10hpa.json")
GRIB = Path("/tmp/x5-ifs-10hpa.grib2")
PARAMS = ["t", "u", "v", "z"]
LEVEL = 10
STEP = 24


def read_fields(path: Path):
    fields = {}
    with path.open("rb") as f:
        while True:
            gid = codes_grib_new_from_file(f)
            if gid is None:
                break
            try:
                short = str(codes_get(gid, "shortName")).lower()
                level = int(codes_get(gid, "level"))
                if level != LEVEL or short not in PARAMS:
                    continue
                values = np.asarray(codes_get_values(gid), dtype=float)
                lats = np.asarray(__import__("eccodes").codes_get_array(gid, "latitudes"), dtype=float)
                lons = np.asarray(__import__("eccodes").codes_get_array(gid, "longitudes"), dtype=float)
                if values.size != lats.size or values.size != lons.size:
                    raise RuntimeError(f"GRIB grid mismatch for {short}")
                fields[short] = (lats, lons, values)
            finally:
                codes_release(gid)
    missing = sorted(set(PARAMS) - set(fields))
    if missing:
        raise RuntimeError("Missing 10 hPa fields: " + ", ".join(missing))
    base = fields["t"][0]
    for key, (lat, lon, _) in fields.items():
        if lat.size != base.size:
            raise RuntimeError(f"Inconsistent grid for {key}")
    return fields


def weighted_mean(values, lats):
    weights = np.cos(np.deg2rad(lats))
    good = np.isfinite(values) & np.isfinite(weights)
    if not np.any(good):
        return None
    return float(np.average(values[good], weights=weights[good]))


def aggregate(fields):
    lats, lons, _ = fields["t"]
    mask = (lats >= 40.0) & (lats <= 90.0)
    if not np.any(mask):
        raise RuntimeError("No Northern Hemisphere polar-cap grid points found")
    # Compact 5-degree latitude x 10-degree longitude grid for browser delivery.
    cells = {}
    for idx in np.where(mask)[0]:
        lat = float(lats[idx])
        lon = float(lons[idx]) % 360.0
        lat0 = min(85, int(math.floor(lat / 5.0) * 5))
        lon0 = int(math.floor(lon / 10.0) * 10) % 360
        key = (lat0, lon0)
        cell = cells.setdefault(key, {k: [] for k in PARAMS})
        for name in PARAMS:
            cell[name].append(float(fields[name][2][idx]))
    grid = []
    for (lat0, lon0), bucket in sorted(cells.items()):
        item = {"lat": lat0 + 2.5, "lon": lon0 + 5.0}
        for name in PARAMS:
            vals = np.asarray(bucket[name], dtype=float)
            vals = vals[np.isfinite(vals)]
            item[name] = round(float(np.mean(vals)), 3) if vals.size else None
        grid.append(item)

    profile = []
    for lat0 in range(40, 90, 5):
        band = (lats >= lat0) & (lats < lat0 + 5)
        if not np.any(band):
            continue
        row = {"lat": lat0 + 2.5}
        for name in PARAMS:
            row[name] = round(weighted_mean(fields[name][2][band], lats[band]), 3)
        profile.append(row)

    u60 = weighted_mean(fields["u"][2][(lats >= 57.5) & (lats < 62.5)], lats[(lats >= 57.5) & (lats < 62.5)])
    polar_t = weighted_mean(fields["t"][2][lats >= 60], lats[lats >= 60])
    return {
        "grid": grid,
        "zonal_profile": profile,
        "diagnostics": {
            "zonal_wind_60N_ms": round(u60, 3) if u60 is not None else None,
            "polar_cap_temperature_10hpa_k": round(polar_t, 3) if polar_t is not None else None,
            "grid_points_north_of_40N": int(np.count_nonzero(mask)),
            "aggregated_cells": len(grid),
        },
    }


def main():
    client = Client(source="ecmwf", model="ifs", resol="0p25")
    latest = client.latest(
        stream="oper", type="fc", step=STEP, levtype="pl",
        levelist=LEVEL, param=PARAMS, target=str(GRIB),
    )
    if latest is None:
        raise RuntimeError("ECMWF did not report a matching recent forecast run")
    run = latest if isinstance(latest, datetime) else datetime.fromisoformat(str(latest))
    client.retrieve(
        date=run.strftime("%Y%m%d"), time=run.hour, stream="oper",
        type="fc", step=STEP, levtype="pl", levelist=LEVEL,
        param=PARAMS, target=str(GRIB),
    )
    fields = read_fields(GRIB)
    result = aggregate(fields)
    payload = {
        "schema_version": 1,
        "product": "ECMWF IFS operational forecast",
        "source": "ECMWF Open Data",
        "license": "CC-BY-4.0",
        "attribution": "Contains modified Copernicus/ECMWF information",
        "pressure_level_hpa": LEVEL,
        "forecast_step_hours": STEP,
        "run_utc": run.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valid_time_utc": ((run.replace(tzinfo=timezone.utc) if run.tzinfo is None else run.astimezone(timezone.utc)) + timedelta(hours=STEP)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "units": {"t": "K", "u": "m s-1", "v": "m s-1", "z": "m2 s-2"},
        "field_notes": {
            "t": "Air temperature",
            "u": "Eastward wind component",
            "v": "Northward wind component",
            "z": "Geopotential",
        },
        **result,
        "method": "Forecast fields sampled at 10 hPa, aggregated to 5-degree latitude by 10-degree longitude bins north of 40N. Zonal means use cosine-latitude weighting.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    # Keep a compact forecast history for the viewer's time series.
    history_path = Path("data/polar-vortex-history.json")
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
        if not isinstance(history, dict) or not isinstance(history.get("records"), list):
            raise RuntimeError("Invalid polar-vortex history file")
    else:
        history = {"schema_version": 1, "source": "ECMWF IFS Open Data", "records": []}
    record = {
        "run_utc": payload["run_utc"],
        "valid_time_utc": payload["valid_time_utc"],
        "generated_utc": payload["generated_utc"],
        "zonal_wind_60N_ms": payload["diagnostics"]["zonal_wind_60N_ms"],
        "polar_cap_temperature_10hpa_k": payload["diagnostics"]["polar_cap_temperature_10hpa_k"],
    }
    records = [r for r in history["records"] if r.get("run_utc") != record["run_utc"]]
    records.append(record)
    records.sort(key=lambda r: r.get("run_utc", ""))
    history["records"] = records[-365:]
    history["updated_utc"] = payload["generated_utc"]
    history_path.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}: {len(payload['grid'])} grid cells; run {payload['run_utc']}")
    print(f"Wrote {history_path}: {len(history['records'])} forecast records")


if __name__ == "__main__":
    main()
