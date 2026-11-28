#!/usr/bin/env python3
"""Collect Best Available WDC Kyoto geomagnetic indices for Observatory X-5."""
from __future__ import annotations
import json, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASES = ["https://wdc.kugi.kyoto-u.ac.jp/hapi", "https://wdcvmweb.kugi.kyoto-u.ac.jp/hapi"]
OUT = Path("data/space-weather/kyoto-indices.json")
UTC = timezone.utc
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z")

def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def get_json(url: str, timeout: int = 25):
    req = Request(url, headers={"User-Agent": "Observatory-X5/1.0 (WDC Kyoto HAPI client)", "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8-sig")
    obj = json.loads(raw)
    if isinstance(obj, dict) and isinstance(obj.get("status"), dict):
        code = obj["status"].get("code")
        if code not in (None, 1200):
            raise RuntimeError(f"HAPI {code}: {obj['status'].get('message', '')}")
    return obj

def parse_availability(obj):
    """Accept Kyoto's non-standard availability JSON shapes without guessing gaps."""
    intervals = []
    def walk(node):
        if isinstance(node, dict):
            low = {str(k).lower(): v for k, v in node.items()}
            start = next((low[k] for k in ("start", "startdate", "begin", "from") if k in low), None)
            stop = next((low[k] for k in ("stop", "stopdate", "end", "to") if k in low), None)
            if isinstance(start, str) and isinstance(stop, str):
                if ISO_RE.fullmatch(start) and ISO_RE.fullmatch(stop):
                    intervals.append((start, stop))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, list) and len(item) >= 2 and all(isinstance(x, str) for x in item[:2]):
                    if ISO_RE.fullmatch(item[0]) and ISO_RE.fullmatch(item[1]):
                        intervals.append((item[0], item[1]))
                else:
                    walk(item)
    walk(obj)
    return sorted(set(intervals), key=lambda x: x[1])

def get_info(base, dataset):
    return get_json(base + "/info?" + urlencode({"dataset": dataset}))

def get_availability(base, dataset):
    return get_json(base + "/availability?" + urlencode({"dataset": dataset}))

def get_data(base, dataset, start, stop):
    return get_json(base + "/data?" + urlencode({
        "dataset": dataset, "start": start, "stop": stop, "format": "json"
    }))

def decode_rows(payload):
    params = payload.get("parameters") or []
    names = [p.get("name") for p in params]
    fills = {p.get("name"): p.get("fill") for p in params}
    rows = []
    for raw in payload.get("data") or []:
        if isinstance(raw, list):
            row = {name: raw[i] for i, name in enumerate(names) if name and i < len(raw)}
        elif isinstance(raw, dict):
            row = raw
        else:
            continue
        t = row.get("Time") or row.get("time") or row.get("timestamp")
        if not t:
            continue
        row["_time"] = str(t)
        valid = False
        for key, value in row.items():
            if key in ("Time", "time", "timestamp", "_time", "versionCode"):
                continue
            try:
                number = float(value)
                fill = fills.get(key)
                is_fill = fill is not None and number == float(fill)
                if number not in (99999, 99999.0) and not is_fill:
                    valid = True
                    break
            except (TypeError, ValueError):
                pass
        if valid:
            rows.append(row)
    rows.sort(key=lambda r: r["_time"])
    return rows

def fetch_dataset(dataset):
    errors = []
    for base in BASES:
        try:
            info = get_info(base, dataset)
            start_meta = info.get("startDate")
            stop_meta = info.get("stopDate")
            if not start_meta or not stop_meta:
                raise RuntimeError("HAPI info neobsahuje startDate/stopDate")
            meta_start = datetime.fromisoformat(start_meta.replace("Z", "+00:00"))
            meta_stop = datetime.fromisoformat(stop_meta.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            intervals = []
            availability_status = "dostupnost ověřena"
            try:
                intervals = parse_availability(get_availability(base, dataset))
            except Exception as exc:
                availability_status = "availability endpoint nedostupný; použit rozsah info: " + str(exc)[:180]
            if intervals:
                candidates = []
                for left, right in intervals:
                    lo = datetime.fromisoformat(left.replace("Z", "+00:00"))
                    hi = datetime.fromisoformat(right.replace("Z", "+00:00"))
                    if lo <= now and hi >= meta_start:
                        candidates.append((max(lo, meta_start), min(hi, now + timedelta(minutes=1))))
                candidates = [x for x in candidates if x[0] < x[1]]
                if not candidates:
                    raise RuntimeError("availability neobsahuje interval v minulosti")
                range_start, range_stop = max(candidates, key=lambda x: x[1])
            else:
                range_start, range_stop = meta_start, min(meta_stop + timedelta(minutes=1), now + timedelta(minutes=1))
            if range_start >= range_stop:
                raise RuntimeError("neplatný interval dostupnosti")
            last_error = "žádná data"
            for hours in (168, 24, 6, 1):
                stop_dt = range_stop
                start_dt = max(range_start, stop_dt - timedelta(hours=hours))
                if start_dt >= stop_dt:
                    continue
                try:
                    payload = get_data(base, dataset, iso(start_dt), iso(stop_dt))
                    rows = decode_rows(payload)
                    if rows:
                        return {
                            "dataset": dataset, "base": base, "rows": rows,
                            "last": rows[-1], "count": len(rows),
                            "availability": availability_status,
                            "intervalStart": iso(range_start), "intervalStop": iso(range_stop),
                            "requestedHours": hours,
                            "metadataStart": start_meta, "metadataStop": stop_meta
                        }
                    last_error = "HAPI odpověděl bez platných datových řádků"
                except Exception as exc:
                    last_error = str(exc)
                    if "1201" not in last_error and "no data for time range" not in last_error.lower():
                        # A malformed/unsupported request should not be hidden by repeated smaller requests.
                        if "1408" not in last_error:
                            break
            raise RuntimeError(last_error)
        except Exception as exc:
            errors.append(base.replace("https://", "") + ": " + str(exc)[:300])
    raise RuntimeError(" | ".join(errors))

def main():
    result = {
        "schemaVersion": 1,
        "generatedAt": iso(datetime.now(UTC)),
        "source": "WDC Kyoto HAPI · Best Available datasets",
        "citation": {"AE": "doi:10.17593/15031-54800", "ASY_SYM": "doi:10.14989/267216"},
        "datasets": {},
        "errors": {}
    }
    for key, dataset in (("ae", "min_ae"), ("asysym", "min_asysym")):
        try:
            pack = fetch_dataset(dataset)
            result["datasets"][key] = {k: v for k, v in pack.items() if k != "rows"}
            result["datasets"][key]["latest"] = pack["last"]
            print(f"{dataset}: {pack['count']} valid rows; latest {pack['last'].get('_time')}; {pack['base']}")
        except Exception as exc:
            result["errors"][key] = str(exc)
            print(f"{dataset}: ERROR {exc}", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Avoid a repository commit every polling cycle when Kyoto has not published new records.
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
            if previous.get("datasets") == result["datasets"] and previous.get("errors", {}) == result["errors"]:
                result["generatedAt"] = previous.get("generatedAt", result["generatedAt"])
        except (OSError, json.JSONDecodeError):
            pass
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Keep workflow successful when one dataset is temporarily unavailable; the JSON reports it explicitly.
    print(f"Wrote {OUT}")
    if not result["datasets"]:
        print("No Kyoto dataset returned valid rows; see errors above.", file=sys.stderr)

if __name__ == "__main__":
    main()
