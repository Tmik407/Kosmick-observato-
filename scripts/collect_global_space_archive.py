#!/usr/bin/env python3
"""Collect endpoint health and quality metadata for the independent X-5 global archive."""
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
# Conservative freshness limits. Metadata catalogues intentionally have no age limit.
FRESHNESS_LIMITS_SECONDS = {
    "noaa-wind": 15 * 60,
    "noaa-mag": 15 * 60,
    "noaa-kp": 8 * 60 * 60,
    "goes-xray": 15 * 60,
    "gfz-kp": 8 * 60 * 60,
}


def parse_utc(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def latest_time(payload, reference_time):
    candidates = []
    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in TIME_KEYS and item:
                    parsed = parse_utc(item)
                    if parsed:
                        candidates.append((parsed, str(item)))
                elif isinstance(item, (dict, list)):
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(payload)
    return max(candidates, default=(None, None), key=lambda item: item[0])[1]


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
        "id": sid, "name": source["name"], "institution": source["institution"],
        "endpoint": source["endpoint"], "checked_at_utc": now.isoformat(),
        "ok": None, "access_state": "not_checked", "http_status": None,
        "latency_ms": None, "record_count": None, "latest_data_time": None,
        "latest_data_age_seconds": None, "freshness_limit_seconds": FRESHNESS_LIMITS_SECONDS.get(sid),
        "freshness_state": "not_assessed", "error": None,
    }
    if source.get("access_mode") == "registration_required":
        result["access_state"] = "requires_registration"
        result["error"] = "Automatická kontrola vyžaduje přístupové údaje; tajemství nejsou uložena v repozitáři."
        result["freshness_state"] = "requires_registration"
        return result

    started = time.monotonic()
    try:
        request = urllib.request.Request(
            request_url(source, now),
            headers={"User-Agent": "X5-Global-Space-Archive/1.2",
                     "Accept": "application/json, application/xml, text/plain"}
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
            except json.JSONDecodeError as exc:
                raise ValueError("Response is not valid JSON") from exc
            api_status = payload.get("status") if isinstance(payload, dict) else None
            if isinstance(api_status, dict) and api_status.get("code") not in (None, 1200):
                raise ValueError(f"API status: {api_status}")
            if isinstance(payload, dict) and isinstance(payload.get("catalog"), list):
                result["record_count"] = len(payload["catalog"])
            elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
                result["record_count"] = len(payload["data"])
            elif isinstance(payload, list):
                result["record_count"] = len(payload)
            elif isinstance(payload, dict):
                result["record_count"] = len(payload)
            result["latest_data_time"] = latest_time(payload)

        result["ok"] = True
        result["access_state"] = "available"
        limit = result["freshness_limit_seconds"]
        timestamp = parse_utc(result["latest_data_time"])
        if limit is None:
            result["freshness_state"] = "not_applicable"
        elif timestamp is None:
            result["freshness_state"] = "unknown"
        else:
            age = max(0, round((now - timestamp).total_seconds()))
            result["latest_data_age_seconds"] = age
            result["freshness_state"] = "fresh" if age <= limit else "stale"
    except Exception as exc:
        result["latency_ms"] = round((time.monotonic() - started) * 1000)
        result["ok"] = False
        result["access_state"] = "unavailable_or_blocked"
        result["freshness_state"] = "not_assessed"
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
available = sum(1 for row in checked if row["ok"] is True)
unavailable = sum(1 for row in checked if row["ok"] is False)
requires_registration = sum(1 for row in rows if row["access_state"] == "requires_registration")
latencies = [row["latency_ms"] for row in checked if row["latency_ms"] is not None]
freshness_assessed = [row for row in rows if row["freshness_state"] in ("fresh", "stale")]
fresh_count = sum(1 for row in freshness_assessed if row["freshness_state"] == "fresh")
stale_count = sum(1 for row in freshness_assessed if row["freshness_state"] == "stale")

status = {
    "schema_version": "1.2",
    "project": "X-5 GLOBAL SPACE DATA ARCHIVE",
    "checked_at_utc": now,
    "collector": "GitHub Actions / scripts/collect_global_space_archive.py",
    "methodology": {
        "freshness": "Age is calculated from the newest parseable source timestamp and compared with conservative per-source limits.",
        "completeness": "Not assessed in this collector version; record counts alone do not prove missing samples or gaps.",
        "availability": "HTTP/API response from the collector runner; not a guarantee of scientific data quality.",
    },
    "summary": {
        "total": len(rows), "checked": len(checked), "available": available,
        "unavailable": unavailable, "requires_registration": requires_registration,
        "average_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "freshness_assessed": len(freshness_assessed),
        "fresh": fresh_count, "stale": stale_count,
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
        history = {"schema_version": "1.2", "runs": []}
else:
    history = {"schema_version": "1.2", "runs": []}

history.setdefault("runs", []).append({
    "checked_at_utc": now, "total": len(rows), "checked": len(checked),
    "available": available, "unavailable": unavailable,
    "requires_registration": requires_registration,
    "average_latency_ms": status["summary"]["average_latency_ms"],
    "fresh": fresh_count, "stale": stale_count,
    "sources": [
        {key: row.get(key) for key in (
            "id", "ok", "access_state", "http_status", "latency_ms",
            "record_count", "latest_data_time", "latest_data_age_seconds",
            "freshness_state", "error"
        )}
        for row in rows
    ],
})
history["runs"] = history["runs"][-1000:]
history["updated_at_utc"] = now
history["schema_version"] = "1.2"
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(status["summary"], ensure_ascii=False))
