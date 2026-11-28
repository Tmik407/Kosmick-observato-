#!/usr/bin/env python3
"""Collect endpoint health and lightweight quality metadata for the X-5 global archive."""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("data/global-archive")
ROOT.mkdir(parents=True, exist_ok=True)
CATALOG_PATH = ROOT / "sources.json"
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
        for value in payload.values():
            found = latest_time(value) if isinstance(value, (list, dict)) else None
            if found:
                return found
    return None


def request_url(source, now):
    url = source["endpoint"]
    if source["id"] == "gfz-kp":
        start = (now - dt.timedelta(days=2)).date().isoformat() + "T00:00:00Z"
        end = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        url += "?" + urllib.parse.urlencode({
            "start": start, "end": end, "index": "Kp", "status": "def"
        })
    return url


def collect(source, now):
    sid = source["id"]
    result = {
        "id": sid,
        "name": source["name"],
        "institution": source["institution"],
        "endpoint": source["endpoint"],
        "checked_at_utc": now.isoformat(),
        "ok": None,
        "access_state": "not_checked",
        "http_status": None,
        "latency_ms": None,
        "record_count": None,
        "latest_data_time": None,
        "error": None,
    }
    if source.get("access_mode") == "registration_required":
        result["access_state"] = "requires_registration"
        result["error"] = "Automatická kontrola vyžaduje přístupové údaje; žádná tajemství nejsou uložena v repozitáři."
        return result

    started = time.monotonic()
    try:
        url = request_url(source, now)
        request = urllib.request.Request(
            url, headers={"User-Agent": "X5-Global-Space-Archive/1.1", "Accept": "application/json, application/xml, text/plain"}
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read()
            result["http_status"] = response.status
        result["latency_ms"] = round((time.monotonic() - started) * 1000)
        text = raw.decode("utf-8-sig", errors="replace").strip()
        if not text:
            raise ValueError("Empty response body")
        if text.startswith("<"):
            root = ET.fromstring(text)
            result["record_count"] = sum(
                1 for node in root.iter()
                if node.tag.split("}")[-1].lower() in ("observatory", "observatoryid")
            ) or sum(1 for node in root if len(node))
        else:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                # GFZ's JSON service may return a text error or an ASCII table.
                if sid == "gfz-kp":
                    raise ValueError("GFZ response was not valid JSON; check API response format")
                raise
            if isinstance(payload, dict) and payload.get("status", {}).get("code") not in (None, 1200):
                raise ValueError(f"API status: {payload['status']}")
            if isinstance(payload, dict) and "catalog" in payload:
                result["record_count"] = len(payload["catalog"])
            elif isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], list):
                result["record_count"] = len(payload["data"])
            elif isinstance(payload, list):
                result["record_count"] = len(payload)
            elif isinstance(payload, dict):
                result["record_count"] = len(payload)
            result["latest_data_time"] = latest_time(payload)
        result["ok"] = True
        result["access_state"] = "available"
    except Exception as exc:
        result["latency_ms"] = round((time.monotonic() - started) * 1000)
        result["ok"] = False
        result["access_state"] = "unavailable_or_blocked"
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return result


catalogue = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
sources = catalogue.get("sources", [])
if not sources:
    raise SystemExit("Source catalogue is empty")

now_dt = dt.datetime.now(dt.timezone.utc)
now = now_dt.isoformat()
rows = [collect(source, now_dt) for source in sources]
checked = [row for row in rows if row["ok"] is not None]
available = sum(1 for row in checked if row["ok"])
unavailable = sum(1 for row in checked if not row["ok"])
requires_registration = sum(1 for row in rows if row["access_state"] == "requires_registration")
latencies = [row["latency_ms"] for row in checked if row["latency_ms"] is not None]

status = {
    "schema_version": "1.1",
    "project": "X-5 GLOBAL SPACE DATA ARCHIVE",
    "checked_at_utc": now,
    "collector": "GitHub Actions / scripts/collect_global_space_archive.py",
    "summary": {
        "total": len(rows),
        "checked": len(checked),
        "available": available,
        "unavailable": unavailable,
        "requires_registration": requires_registration,
        "average_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
    },
    "sources": rows,
}
(ROOT / "latest-status.json").write_text(
    json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

history_path = ROOT / "history.json"
if history_path.exists():
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        history = {"schema_version": "1.1", "runs": []}
else:
    history = {"schema_version": "1.1", "runs": []}

history.setdefault("runs", []).append({
    "checked_at_utc": now,
    "total": len(rows),
    "checked": len(checked),
    "available": available,
    "unavailable": unavailable,
    "requires_registration": requires_registration,
    "average_latency_ms": status["summary"]["average_latency_ms"],
    "sources": [
        {key: row.get(key) for key in (
            "id", "ok", "access_state", "http_status", "latency_ms",
            "record_count", "latest_data_time", "error"
        )}
        for row in rows
    ],
})
history["runs"] = history["runs"][-1000:]
history["updated_at_utc"] = now
history["schema_version"] = "1.1"
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(status["summary"], ensure_ascii=False))
