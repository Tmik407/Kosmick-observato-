#!/usr/bin/env python3
"""Probe NASA SSCWeb availability and geomagnetic coordinates for GOES-18/19.

This is a non-production diagnostic: it never writes site data. It reports the
observatory identifiers returned by SSCWeb and tests a short UTC interval.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://sscweb.gsfc.nasa.gov/WS/sscr/2"
HEADERS = {"Accept": "application/json", "User-Agent": "Kosmicka-observator-X5/1.0"}

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read()
        print(f"HTTP {response.status}; content-type={response.headers.get('Content-Type')}; bytes={len(raw)}")
        return json.loads(raw.decode("utf-8"))

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

def find_observatory_id(catalog, satellite):
    aliases = {f"goes{satellite}", f"goes-{satellite}", f"goes {satellite}"}
    for item in walk(catalog):
        text = json.dumps(item, ensure_ascii=False).lower()
        if any(alias in text for alias in aliases):
            ident = next((item[k] for k in ("id", "observatoryId", "observatory") if isinstance(item.get(k), str)), None)
            if ident:
                return ident, item
    return None, None

def main():
    print("NASA SSCWeb GOES-18/19 diagnostic")
    catalog = get_json(BASE + "/observatories")
    print("Catalog top-level:", list(catalog) if isinstance(catalog, dict) else type(catalog).__name__)
    print("Catalog sample:", json.dumps(catalog[:3] if isinstance(catalog, list) else catalog, ensure_ascii=False)[:3000])
    flat = json.dumps(catalog, ensure_ascii=False).lower()
    for token in ("goes18", "goes-18", "goes 18", "goes19", "goes-19", "goes 19"):
        pos = flat.find(token)
        excerpt = flat[max(0, pos-180):pos+350] if pos >= 0 else "NOT PRESENT"
        print(f"catalog search {token}: {excerpt}")
    failures = 0
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(minutes=10)
    t0 = start.strftime("%Y%m%dT%H%M%SZ")
    t1 = end.strftime("%Y%m%dT%H%M%SZ")
    for sat in (18, 19):
        ident, item = find_observatory_id(catalog, sat)
        if not ident:
            print(f"GOES-{sat}: NOT FOUND in SSC observatory catalog")
            failures += 1
            continue
        print(f"GOES-{sat}: identifier={ident}; catalog_record={json.dumps(item, ensure_ascii=False)}")
        path = "/locations/" + urllib.parse.quote(ident, safe="") + f"/{t0},{t1}/gm/"
        try:
            result = get_json(BASE + path)
            print(f"GOES-{sat}: GM response:")
            print(json.dumps(result, ensure_ascii=False)[:12000])
            # Confirm that the service actually returned geomagnetic local time
            # and latitude, rather than assuming the field names.
            keys = {str(k).lower() for obj in walk(result) for k in obj.keys()}
            local_keys = {k for k in keys if "local" in k and "time" in k}
            lat_keys = {k for k in keys if "lat" in k}
            if not local_keys or not lat_keys:
                print(f"GOES-{sat}: INCOMPLETE GM fields; local_time_keys={sorted(local_keys)}, latitude_keys={sorted(lat_keys)}")
                failures += 1
            else:
                print(f"GOES-{sat}: GM field keys detected: local={sorted(local_keys)}, latitude={sorted(lat_keys)}")
        except Exception as exc:
            print(f"GOES-{sat}: REQUEST FAILED: {type(exc).__name__}: {exc}")
            failures += 1
    if failures:
        print(f"SSCWeb diagnostic finished with {failures} failure(s).")
        sys.exit(1)
    print("SSCWeb diagnostic passed for both satellites.")

if __name__ == "__main__":
    main()
