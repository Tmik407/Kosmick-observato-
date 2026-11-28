#!/usr/bin/env python3
"""Collect endpoint health and lightweight data-quality metadata for X-5 archive."""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path("data/global-archive")
ROOT.mkdir(parents=True, exist_ok=True)
SOURCES = [
    ("noaa-wind", "NOAA SWPC RTSW solar wind", "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"),
    ("noaa-mag", "NOAA SWPC RTSW IMF", "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"),
    ("noaa-kp", "NOAA planetary Kp", "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"),
    ("goes-xray", "GOES X-ray flux", "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"),
    ("nasa-ssc", "NASA SSCWeb observatory catalogue", "https://sscweb.gsfc.nasa.gov/WS/sscr/2/observatories"),
]
TIME_KEYS = ("time_tag", "time", "timestamp", "date", "eventTime", "ObservationTime")

def latest_time(payload):
    if isinstance(payload, list):
        for row in reversed(payload):
            if isinstance(row, dict):
                for key in TIME_KEYS:
                    if row.get(key):
                        return str(row[key])
    if isinstance(payload, dict):
        for key in TIME_KEYS:
            if payload.get(key):
                return str(payload[key])
    return None

def collect(source):
    sid, name, url = source
    started = time.monotonic()
    result = {
        "id": sid, "name": name, "endpoint": url,
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ok": False, "http_status": None, "latency_ms": None,
        "record_count": None, "latest_data_time": None, "error": None,
    }
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "X5-Global-Space-Archive/1.0"})
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read()
            result["http_status"] = response.status
        result["latency_ms"] = round((time.monotonic() - started) * 1000)
        payload = json.loads(raw.decode("utf-8-sig"))
        result["ok"] = True
        result["record_count"] = len(payload) if isinstance(payload, list) else (
            len(payload.get("observatories", [])) if isinstance(payload, dict) and isinstance(payload.get("observatories"), list) else 1
        )
        result["latest_data_time"] = latest_time(payload)
    except Exception as exc:
        result["latency_ms"] = round((time.monotonic() - started) * 1000)
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return result

now = dt.datetime.now(dt.timezone.utc).isoformat()
rows = [collect(source) for source in SOURCES]
status = {
    "schema_version": "1.0",
    "project": "X-5 GLOBAL SPACE DATA ARCHIVE",
    "checked_at_utc": now,
    "collector": "GitHub Actions / scripts/collect_global_space_archive.py",
    "summary": {
        "total": len(rows),
        "available": sum(1 for row in rows if row["ok"]),
        "unavailable": sum(1 for row in rows if not row["ok"]),
        "average_latency_ms": round(sum(row["latency_ms"] or 0 for row in rows) / len(rows)),
    },
    "sources": rows,
}
status_path = ROOT / "latest-status.json"
status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

history_path = ROOT / "history.json"
if history_path.exists():
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        history = {"schema_version": "1.0", "runs": []}
else:
    history = {"schema_version": "1.0", "runs": []}

history.setdefault("runs", []).append({
    "checked_at_utc": now,
    "total": len(rows),
    "available": status["summary"]["available"],
    "unavailable": status["summary"]["unavailable"],
    "average_latency_ms": status["summary"]["average_latency_ms"],
    "sources": [
        {k: row.get(k) for k in ("id", "ok", "http_status", "latency_ms", "record_count", "latest_data_time", "error")}
        for row in rows
    ],
})
history["runs"] = history["runs"][-1000:]
history["updated_at_utc"] = now
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(status["summary"], ensure_ascii=False))
