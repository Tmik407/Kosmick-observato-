#!/usr/bin/env python3
"""Build a delayed, global IRTAM electron-density map for X-5.

The target is deliberately 48 hours behind UTC to use public GAMBIT data.
Only model output is published; source coefficients remain temporary.
"""
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import urllib.request

import numpy as np
import PyIRTAM

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "irtam-density.json"
STEP_DEG = 10
ALT_KM = 300.0


def get_f107(day):
    # Canadian Space Weather daily Penticton observations (observed flux, not monthly mean).
    url = "https://www.spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt"
    req = urllib.request.Request(url, headers={"User-Agent": "X5-Ionosphere/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        lines = response.read().decode("utf-8", errors="replace").splitlines()
    daily = {}
    for line in lines:
        cols = line.split()
        if len(cols) < 7 or not cols[0].isdigit() or len(cols[0]) != 8:
            continue
        try:
            d = datetime.strptime(cols[0], "%Y%m%d").date()
            observed = float(cols[4])
        except (ValueError, TypeError):
            continue
        if d <= day and math.isfinite(observed) and 40 <= observed <= 400:
            daily.setdefault(d, []).append(observed)
    if not daily:
        raise RuntimeError("Kanadská databáze: žádný platný pozorovaný F10.7 index")
    d = max(daily)
    if (day - d).days > 7:
        raise RuntimeError("Poslední pozorovaný F10.7 je starší než 7 dní")
    # Use the mean of all actual observations on the most recent available day.
    return float(np.mean(daily[d])), d.isoformat()


def main():
    now = datetime.now(timezone.utc)
    target_day = (now - timedelta(days=2)).date()
    # Coefficient products are available on 15-minute epochs. Use 12:00 UTC.
    target = datetime(target_day.year, target_day.month, target_day.day, 12, 0)
    f107, f107_day = get_f107(target_day)

    lats = np.arange(-85, 86, STEP_DEG, dtype=float)
    lons = np.arange(-180, 180, STEP_DEG, dtype=float)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    alon = lon_grid.ravel()
    alat = lat_grid.ravel()
    altitudes = np.array([100., 150., 200., 250., 300., 350., 400., 500., 600.])
    aUT = np.array([12.0])

    result = PyIRTAM.run_PyIRTAM(
        target.year, target.month, target.day, aUT,
        alon, alat, altitudes, f107,
        download=True,
    )
    edp = np.asarray(result[-1], dtype=float)
    if edp.ndim != 3 or edp.shape[0] < 1 or edp.shape[1] != len(altitudes):
        raise RuntimeError(f"Nečekaný rozměr IRTAM EDP: {edp.shape}")
    alt_idx = int(np.where(altitudes == ALT_KM)[0][0])
    ne_m3 = edp[0, alt_idx, :]
    if not np.isfinite(ne_m3).any():
        raise RuntimeError("IRTAM vrátil prázdnou elektronovou hustotu")
    points = []
    for lat, lon, val in zip(alat, alon, ne_m3):
        if not np.isfinite(val) or val < 0 or val > 5e12:
            continue
        points.append({
            "lat": round(float(lat), 1),
            "lon": round(float(lon), 1),
            "ne_1e6_cm3": round(float(val) / 1e12, 5),
        })
    if len(points) < 250:
        raise RuntimeError(f"Příliš málo platných bodů IRTAM: {len(points)}")
    payload = {
        "source": "PyIRTAM / GIRO GAMBIT coefficients; IRTAM electron density profile",
        "source_url": "https://lgdc.uml.edu/rix/gambit-coeffs",
        "model": "IRTAM",
        "target_utc": target.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delay_hours": round((now - target.replace(tzinfo=timezone.utc)).total_seconds()/3600, 2),
        "altitude_km": ALT_KM,
        "f107_sfu": f107,
        "f107_date": f107_day,
        "grid_step_deg": STEP_DEG,
        "units": "10^6 electrons cm^-3",
        "valid_points": len(points),
        "points": points,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"IRTAM: {len(points)} points at {ALT_KM} km, target {payload['target_utc']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"IRTAM build failed: {exc}", file=sys.stderr)
        raise
