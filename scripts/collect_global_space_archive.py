#!/usr/bin/env python3
"""Collect endpoint health and quality metadata for the independent X-5 global archive."""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("data/global-archive")
ROOT.mkdir(parents=True, exist_ok=True)
CATALOG_PATH = ROOT / "sources.json"
TIME_KEYS = ("time_tag", "time", "timestamp", "date", "eventTime", "ObservationTime")
EXPECTED_CADENCE_SECONDS = {"noaa-wind": 60, "noaa-mag": 60, "goes-xray": 60, "noaa-kp": 10800}
SERIES_KEYS = ("satellite", "satellite_id", "energy", "energy_range", "channel", "parameter", "instrument", "flux_type")
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



def analyze_completeness(payload, source_id):
    """Estimate gaps/duplicates in returned timestamped samples where cadence is configured."""
    cadence = EXPECTED_CADENCE_SECONDS.get(source_id)
    result = {"state": "not_assessed", "expected_cadence_seconds": cadence,
              "timestamped_samples": 0, "unique_samples": 0, "duplicate_samples": 0,
              "gap_count": None, "missing_samples_estimate": None,
              "completeness_percent_estimate": None, "max_gap_seconds": None,
              "method": "Returned-window estimate only; not full-archive completeness."}
    if cadence is None:
        result["state"] = "cadence_unknown"
        return result
    groups = {}
    duplicate_supported = [True]
    def walk(value):
        if isinstance(value, dict):
            stamp = None
            for key in TIME_KEYS:
                if value.get(key):
                    stamp = parse_utc(value[key])
                    if stamp:
                        break
            if stamp:
                series_fields = [(k, value.get(k)) for k in SERIES_KEYS if value.get(k) not in (None, "")]
                if not series_fields:
                    duplicate_supported[0] = False
                series = tuple((k, str(v)) for k, v in series_fields)
                groups.setdefault(series, []).append(stamp)
            for item in value.values():
                if isinstance(item, (dict, list)):
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    walk(item)
    walk(payload)
    if not groups:
        result["state"] = "no_timestamps"
        return result
    total = unique = duplicates = gaps = missing = max_gap = expected_slots = 0
    for stamps in groups.values():
        ordered = sorted(stamps)
        distinct = sorted(set(ordered))
        total += len(ordered)
        unique += len(distinct)
        if duplicate_supported[0]:
            duplicates += len(ordered) - len(distinct)
        if len(distinct) < 2:
            continue
        expected_slots += max(1, round((distinct[-1] - distinct[0]).total_seconds() / cadence)) + 1
        for left, right in zip(distinct, distinct[1:]):
            delta = (right - left).total_seconds()
            max_gap = max(max_gap, round(delta))
            if delta > cadence * 1.5:
                gaps += 1
                missing += max(0, round(delta / cadence) - 1)
    result.update({"state": "assessed", "timestamped_samples": total,
        "unique_samples": unique, "duplicate_samples": duplicates if duplicate_supported[0] else None, "duplicate_detection": "assessed" if duplicate_supported[0] else "not_assessed_missing_series_identifier", "gap_count": gaps,
        "missing_samples_estimate": missing,
        "completeness_percent_estimate": round(max(0, 100 * (1 - missing / max(1, expected_slots))), 2) if expected_slots else None,
        "max_gap_seconds": max_gap or None})
    return result


def quality_score(row):
    """Provisional operational score, not a scientific validity score."""
    if row.get("access_state") == "requires_registration" or row.get("ok") is None:
        return None
    completeness = row.get("completeness") or {}
    if completeness.get("state") != "assessed":
        return None
    score = 30 if row.get("ok") else 0
    if row.get("freshness_state") == "fresh":
        score += 30
    elif row.get("freshness_state") == "not_applicable":
        score += 15
    pct = completeness.get("completeness_percent_estimate")
    if pct is not None:
        score += 30 * pct / 100
    duplicates = completeness.get("duplicate_samples")
    samples = max(1, completeness.get("timestamped_samples", 0))
    if duplicates is not None:
        score += 10 * max(0, 1 - duplicates / samples)
    return round(score, 1)


def request_url(source, now):
    url = source["endpoint"]
    if source["id"] == "gfz-kp":
        start = (now - dt.timedelta(days=2)).date().isoformat() + "T00:00:00Z"
        end = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        url += "?" + urllib.parse.urlencode({
            "start": start, "end": end, "index": "Kp", "status": "def"
        })
    return url


PAYLOADS = {}


def collect(source, now):
    sid = source["id"]
    result = {
        "id": sid, "name": source["name"], "institution": source["institution"],
        "endpoint": source["endpoint"], "checked_at_utc": now.isoformat(),
        "ok": None, "access_state": "not_checked", "http_status": None,
        "latency_ms": None, "record_count": None, "latest_data_time": None,
        "latest_data_age_seconds": None, "freshness_limit_seconds": FRESHNESS_LIMITS_SECONDS.get(sid),
        "freshness_state": "not_assessed", "completeness": {"state": "not_assessed"}, "quality_score": None, "error": None,
    }
    if source.get("access_mode") == "registration_required":
        result["access_state"] = "requires_registration"
        result["error"] = "Automatická kontrola vyžaduje přístupové údaje; tajemství nejsou uložena v repozitáři."
        result["freshness_state"] = "requires_registration"
        result["completeness"] = {"state": "requires_registration"}
        return result

    started = time.monotonic()
    try:
        request = urllib.request.Request(
            request_url(source, now),
            headers={"User-Agent": "X5-Global-Space-Archive/1.3",
                     "Accept": "application/json, application/xml, text/plain"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
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
            PAYLOADS[sid] = payload
            result["latest_data_time"] = latest_time(payload, now)
            result["completeness"] = analyze_completeness(payload, sid)

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
    result["quality_score"] = quality_score(result)
    return result



def extract_kp_series(payload):
    found = {}
    def add(stamp, value):
        parsed = parse_utc(stamp)
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        if parsed and 0 <= number <= 9:
            found[parsed] = number
    def walk(value):
        if isinstance(value, list):
            if value and isinstance(value[0], str) and any(str(x).lower() in ("time_tag", "datetime", "time", "date") for x in value):
                headers = [str(x).lower() for x in value]
                ti = next((i for i, x in enumerate(headers) if x in ("time_tag", "datetime", "time", "date")), None)
                ki = next((i for i, x in enumerate(headers) if x in ("kp", "kp_index", "kpvalue")), None)
                if ti is not None and ki is not None:
                    for row in value[1:]:
                        if isinstance(row, list) and max(ti, ki) < len(row):
                            add(row[ti], row[ki])
            else:
                for item in value:
                    if isinstance(item, (dict, list)):
                        walk(item)
        elif isinstance(value, dict):
            lower = {str(k).lower(): k for k in value}
            tk = next((lower[k] for k in ("datetime", "time_tag", "time", "date") if k in lower), None)
            kk = next((lower[k] for k in ("kp", "kp_index", "kpvalue") if k in lower), None)
            if tk is not None and kk is not None:
                if isinstance(value[tk], list) and isinstance(value[kk], list):
                    for stamp, val in zip(value[tk], value[kk]):
                        add(stamp, val)
                else:
                    add(value[tk], value[kk])
            for item in value.values():
                if isinstance(item, (dict, list)):
                    walk(item)
    walk(payload)
    return found


def archive_samples(source_id, payload):
    """Normalize timestamped observations without changing the provider payload."""
    samples = []
    def add(stamp, values):
        parsed = parse_utc(stamp)
        if not parsed:
            return
        clean = {}
        for key, value in values.items():
            if key.lower() in ("time", "time_tag", "timestamp", "datetime", "date"):
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                clean[key] = value
        if clean:
            samples.append({"source": source_id, "time_utc": parsed.isoformat().replace("+00:00", "Z"),
                            "values": clean})
    def walk(value):
        if isinstance(value, dict):
            lower = {str(k).lower(): k for k in value}
            time_key = next((lower[k] for k in ("time_tag", "datetime", "time", "timestamp", "date") if k in lower), None)
            if time_key is not None and not isinstance(value[time_key], list):
                add(value[time_key], value)
            # GFZ API documents parallel datetime and index arrays.
            if "datetime" in lower and isinstance(value[lower["datetime"]], list):
                time_values = value[lower["datetime"]]
                for key, original in lower.items():
                    if key in ("datetime", "status") or not isinstance(value[original], list):
                        continue
                    vals = value[original]
                    status_key = lower.get("status")
                    statuses = value[status_key] if status_key and isinstance(value[status_key], list) else []
                    for i, (stamp, val) in enumerate(zip(time_values, vals)):
                        row = {original: val}
                        if i < len(statuses):
                            row["status"] = statuses[i]
                        add(stamp, row)
            for item in value.values():
                if isinstance(item, (dict, list)):
                    walk(item)
        elif isinstance(value, list):
            # NOAA table endpoints use a header row followed by positional rows.
            if value and isinstance(value[0], list) and value[0] and all(isinstance(x, str) for x in value[0]):
                headers = value[0]
                normalized = [str(x).lower() for x in headers]
                ti = next((i for i, x in enumerate(normalized) if x in ("time_tag", "datetime", "time", "date")), None)
                if ti is not None:
                    for row in value[1:]:
                        if isinstance(row, list) and ti < len(row):
                            add(row[ti], {headers[i]: row[i] for i in range(min(len(headers), len(row)))})
                    return
            for item in value:
                if isinstance(item, (dict, list)):
                    walk(item)
    walk(payload)
    # Deduplicate within a single collection pass, preserving the last occurrence.
    unique = {}
    for sample in samples:
        key = (sample["source"], sample["time_utc"], json.dumps(sample["values"], sort_keys=True))
        unique[key] = sample
    return list(unique.values())


def persist_timeseries(payloads, now):
    """Merge normalized samples into UTC-day JSON files; repeated polls do not duplicate rows."""
    archive_dir = ROOT / "timeseries"
    archive_dir.mkdir(parents=True, exist_ok=True)
    additions = 0
    for source_id, payload in payloads.items():
        for sample in archive_samples(source_id, payload):
            day = sample["time_utc"][:10]
            path = archive_dir / f"{day}.json"
            try:
                existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            except (json.JSONDecodeError, OSError):
                existing = []
            key = (sample["source"], sample["time_utc"], json.dumps(sample["values"], sort_keys=True))
            known = {(row.get("source"), row.get("time_utc"), json.dumps(row.get("values", {}), sort_keys=True)) for row in existing}
            if key not in known:
                existing.append(sample)
                additions += 1
                path.write_text(json.dumps(sorted(existing, key=lambda row: (row.get("time_utc", ""), row.get("source", ""))), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return additions


def compare_kp_sources(payloads):
    result = {"comparison": "NOAA SWPC Kp vs GFZ Kp", "state": "not_assessed",
              "matched_samples": 0, "mean_absolute_difference": None,
              "max_absolute_difference": None, "disagreements_over_0_33": None,
              "method": "Exact UTC timestamp matches only; differences > 0.33 are flagged, not treated as source failure."}
    if "noaa-kp" not in payloads or "gfz-kp" not in payloads:
        result["state"] = "source_unavailable"
        return result
    noaa = extract_kp_series(payloads["noaa-kp"])
    gfz = extract_kp_series(payloads["gfz-kp"])
    common = sorted(set(noaa) & set(gfz))
    if not common:
        result["state"] = "no_common_timestamps_or_unrecognized_format"
        result["noaa_samples_parsed"] = len(noaa)
        result["gfz_samples_parsed"] = len(gfz)
        return result
    diffs = [abs(noaa[t] - gfz[t]) for t in common]
    result.update({"state": "assessed", "matched_samples": len(common),
        "noaa_samples_parsed": len(noaa), "gfz_samples_parsed": len(gfz),
        "mean_absolute_difference": round(sum(diffs) / len(diffs), 3),
        "max_absolute_difference": round(max(diffs), 3),
        "disagreements_over_0_33": sum(1 for x in diffs if x > 0.33),
        "latest_common_time_utc": common[-1].isoformat()})
    return result


catalogue = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
sources = catalogue.get("sources", [])
if not sources:
    raise SystemExit("Source catalogue is empty")

now_dt = dt.datetime.now(dt.timezone.utc)
now = now_dt.isoformat()
# Fetch independent providers concurrently so one slow endpoint cannot delay every other source.
with ThreadPoolExecutor(max_workers=5) as pool:
    rows = list(pool.map(lambda source: collect(source, now_dt), sources))
archived_samples_added = persist_timeseries(PAYLOADS, now_dt)
cross_source = compare_kp_sources(PAYLOADS)
checked = [row for row in rows if row["ok"] is not None]
available = sum(1 for row in checked if row["ok"] is True)
unavailable = sum(1 for row in checked if row["ok"] is False)
requires_registration = sum(1 for row in rows if row["access_state"] == "requires_registration")
latencies = [row["latency_ms"] for row in checked if row["latency_ms"] is not None]
freshness_assessed = [row for row in rows if row["freshness_state"] in ("fresh", "stale")]
fresh_count = sum(1 for row in freshness_assessed if row["freshness_state"] == "fresh")
stale_count = sum(1 for row in freshness_assessed if row["freshness_state"] == "stale")

status = {
    "schema_version": "1.3",
    "project": "X-5 GLOBAL SPACE DATA ARCHIVE",
    "checked_at_utc": now,
    "collector": "GitHub Actions / scripts/collect_global_space_archive.py",
    "methodology": {
        "freshness": "Age is calculated from the newest parseable source timestamp and compared with conservative per-source limits.",
        "completeness": "Estimated only for returned timestamped samples where a conservative cadence is configured; does not establish completeness of the provider full archive.",
        "quality_score": "Provisional operational score from availability, freshness, estimated completeness and duplicates; not scientific validity or calibration.",
        "availability": "HTTP/API response from the collector runner; not a guarantee of scientific data quality.",
    },
    "summary": {
        "total": len(rows), "checked": len(checked), "available": available,
        "unavailable": unavailable, "requires_registration": requires_registration,
        "average_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "freshness_assessed": len(freshness_assessed),
        "fresh": fresh_count, "stale": stale_count,
        "completeness_assessed": sum(1 for row in rows if row.get("completeness", {}).get("state") == "assessed"),
        "quality_scores_available": sum(1 for row in rows if row.get("quality_score") is not None),
    },
    "sources": rows,
    "cross_source_checks": [cross_source],
    "timeseries_archive": {"format": "UTC daily JSON", "samples_added_this_run": archived_samples_added, "directory": "data/global-archive/timeseries/"},
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
    "cross_source_checks": [cross_source],
    "sources": [
        {key: row.get(key) for key in (
            "id", "ok", "access_state", "http_status", "latency_ms",
            "record_count", "latest_data_time", "latest_data_age_seconds",
            "freshness_state", "completeness", "quality_score", "error"
        )}
        for row in rows
    ],
})
history["runs"] = history["runs"][-1000:]
history["updated_at_utc"] = now
history["schema_version"] = "1.3"
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(status["summary"], ensure_ascii=False))
for row in rows:
    print(f"{row['id']}: ok={row['ok']} state={row['access_state']} latency_ms={row['latency_ms']} error={row['error']}")
