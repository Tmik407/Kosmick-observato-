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
STATUS = ROOT / "irtam-status.json"
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
    # Use the newest 15-minute model epoch that is at least 48 hours delayed.
    # This avoids the old fixed 12:00 UTC target, which made the displayed age
    # vary from roughly 36 to 60 hours even when a fresh build succeeded.
    target_dt = now - timedelta(hours=48)
    minute = (target_dt.minute // 15) * 15
    # PyIRTAM/GAMBIT coefficient products are requested at 12:00 UTC.
    # Select the latest 12:00 epoch that is at least 48 h behind now.
    requested_day = target_dt.date()
    if target_dt.hour < 12:
        requested_day -= timedelta(days=1)
    requested_target = datetime.combine(requested_day, datetime.min.time()).replace(hour=12)
    lats = np.arange(-85, 86, STEP_DEG, dtype=float)
    lons = np.arange(-180, 180, STEP_DEG, dtype=float)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    alon = lon_grid.ravel()
    alat = lat_grid.ravel()
    altitudes = np.array([100., 150., 200., 250., 300., 350., 400., 500., 600.])
    # GAMBIT coefficients may be published late. Try this epoch and up to
    # three earlier daily epochs; always label the actual model epoch.
    result = None
    fallback_errors = []
    for fallback_days in range(4):
        target = requested_target - timedelta(days=fallback_days)
        target_day = target.date()
        try:
            f107, f107_day = get_f107(target_day)
            model_ut = np.array([12.0])
            result = PyIRTAM.run_PyIRTAM(
                target.year, target.month, target.day, model_ut,
                alon, alat, altitudes, f107, download=True,
            )
            break
        except Exception as exc:
            fallback_errors.append({
                "target_utc": target.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "error": str(exc)[:500],
            })
            print(f"IRTAM epoch {target.isoformat()} unavailable: {exc}", file=sys.stderr)
    if result is None:
        raise RuntimeError("No usable GAMBIT coefficient epoch in 4-day window: " + json.dumps(fallback_errors))

    edp = np.asarray(result[-1], dtype=float)
    if edp.ndim != 3 or edp.shape[0] < 1 or edp.shape[1] != len(altitudes):
        raise RuntimeError(f"Nečekaný rozměr IRTAM EDP: {edp.shape}")
    # Global vertical profile: spatial statistics for every modeled altitude.
    # This is a global grid summary, not a local vertical sounding.
    profile = []
    for alt_idx, altitude in enumerate(altitudes):
        vals = edp[0, alt_idx, :]
        vals = vals[np.isfinite(vals) & (vals >= 0) & (vals <= 5e12)] / 1e12
        if len(vals) < 250:
            raise RuntimeError(f"Příliš málo platných bodů profilu ve výšce {altitude} km: {len(vals)}")
        profile.append({
            "altitude_km": int(altitude),
            "mean_ne_1e6_cm3": round(float(np.mean(vals)), 5),
            "median_ne_1e6_cm3": round(float(np.median(vals)), 5),
            "min_ne_1e6_cm3": round(float(np.min(vals)), 5),
            "max_ne_1e6_cm3": round(float(np.max(vals)), 5),
            "valid_points": int(len(vals)),
        })

    levels = {}
    for altitude in (200., 300., 400., 500.):
        alt_idx = int(np.where(altitudes == altitude)[0][0])
        ne_m3 = edp[0, alt_idx, :]
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
            raise RuntimeError(f"Příliš málo platných bodů IRTAM ve výšce {altitude} km: {len(points)}")
        levels[str(int(altitude))] = points
    points = levels["300"]
    payload = {
        "source": "PyIRTAM / GIRO GAMBIT coefficients; IRTAM electron density profile",
        "source_url": "https://lgdc.uml.edu/rix/gambit-coeffs",
        "model": "IRTAM",
        "target_utc": target.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delay_hours": round((now - target.replace(tzinfo=timezone.utc)).total_seconds()/3600, 2),
        "altitude_km": ALT_KM,
        "available_altitudes_km": [200, 300, 400, 500],
        "levels": levels,
        "global_vertical_profile": profile,
        "profile_description": "Globální prostorové statistiky elektronové hustoty pro každou výšku; nejde o lokální vertikální sondáž.",
        "f107_sfu": f107,
        "f107_date": f107_day,
        "requested_target_utc": requested_target.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coefficient_fallback_days": (requested_target.date() - target.date()).days,
        "coefficient_fallback_errors": fallback_errors,
        "grid_step_deg": STEP_DEG,
        "units": "10^6 electrons cm^-3",
        "valid_points": len(points),
        "points": points,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    STATUS.write_text(json.dumps({
        "source": "PyIRTAM / GIRO GAMBIT",
        "status": "success" if not fallback_errors else "success_with_older_epoch",
        "requested_target_utc": payload["requested_target_utc"],
        "actual_model_target_utc": payload["target_utc"],
        "generated_utc": payload["generated_utc"],
        "data_age_hours": payload["delay_hours"],
        "coefficient_fallback_days": payload["coefficient_fallback_days"],
        "fallback_errors": fallback_errors,
        "note": "Older epochs are explicitly identified; no interpolation or relabeling."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"IRTAM: {len(points)} points at {ALT_KM} km, target {payload['target_utc']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        STATUS.write_text(json.dumps({
            "source": "PyIRTAM / GIRO GAMBIT",
            "status": "failed",
            "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": str(exc)[:1500],
            "previous_output_preserved": OUT.exists(),
            "note": "Existing irtam-density.json is preserved; failed run did not replace model data."
        }, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        print(f"IRTAM build failed: {exc}", file=sys.stderr)
        raise
