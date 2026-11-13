#!/usr/bin/env python3
"""Fetch GIRO/KC2G station measurements and provider status for X-5."""
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://prop.kc2g.com"
HEADERS = {"User-Agent": "Kosmicka-Observator-X5/1.0 (+https://github.com/Tmik407/Kosmick-observato-)"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read()
        return body, response.status, response.headers.get("Content-Type", "")


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    out = {
        "schema_version": 1,
        "fetched_utc": now,
        "source": BASE,
        "stations": [],
        "station_http_status": None,
        "station_error": None,
        "provider": {
            "checked_utc": now,
            "status_text": "Stav poskytovatele nebyl ověřen.",
            "stale": None,
            "last_data_utc": None,
            "error": None,
        },
    }

    try:
        body, status, content_type = fetch(BASE + "/api/stations.json")
        out["station_http_status"] = status
        payload = json.loads(body.decode("utf-8-sig"))
        if isinstance(payload, list):
            out["stations"] = payload
        elif isinstance(payload, dict):
            rows = payload.get("stations")
            if isinstance(rows, list):
                out["stations"] = rows
            else:
                out["station_error"] = "API odpovědělo JSON objektem bez pole stations."
        else:
            out["station_error"] = "API nevrátilo seznam ani objekt JSON."
        out["station_content_type"] = content_type
    except Exception as exc:
        out["station_error"] = f"{type(exc).__name__}: {exc}"

    try:
        body, status, _ = fetch(BASE + "/about/")
        page = body.decode("utf-8", errors="replace")
        out["provider"]["http_status"] = status
        stale = bool(re.search(r"Data is stale|No data has been received from GIRO", page, re.I))
        out["provider"]["stale"] = stale
        out["provider"]["status_text"] = (
            "Poskytovatel hlásí zastaralá data." if stale
            else "Stavová stránka byla načtena; zastaralost nebyla výslovně potvrzena."
        )
        match = re.search(r"Last data was at\s*([^<\r\n]+)", page, re.I)
        if match:
            stamp = re.sub(r"\s+", " ", match.group(1)).strip().rstrip(".;")
            try:
                dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
                out["provider"]["last_data_utc"] = dt.isoformat().replace("+00:00", "Z")
            except ValueError:
                out["provider"]["last_data_text"] = stamp
    except Exception as exc:
        out["provider"]["error"] = f"{type(exc).__name__}: {exc}"
        out["provider"]["status_text"] = "Stavová stránka poskytovatele není dostupná."

    out["station_count"] = len(out["stations"])
    Path("giro-status.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"GIRO snapshot: stations={out['station_count']}, "
        f"station_http={out['station_http_status']}, "
        f"station_error={out['station_error']}, "
        f"provider_stale={out['provider']['stale']}, "
        f"last_data={out['provider']['last_data_utc']}"
    )


if __name__ == "__main__":
    main()
