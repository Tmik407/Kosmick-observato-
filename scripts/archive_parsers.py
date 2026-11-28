"""Parsers for archived space-weather index payloads."""
from __future__ import annotations

import datetime as dt
import re


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


def parse_kp_value(value):
    """Convert numeric Kp values and conventional thirds notation to 0..9."""
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().lower()
        try:
            number = float(text)
        except ValueError:
            match = re.fullmatch(r"([0-9])\s*([+-]|o)?", text)
            if not match:
                return None
            number = float(match.group(1))
            suffix = match.group(2)
            if suffix == "+":
                number += 1 / 3
            elif suffix == "-":
                number -= 1 / 3
    return number if 0 <= number <= 9 else None


def extract_kp_series(payload):
    """Read GFZ parallel arrays, row tables, or timestamped object records."""
    found = {}

    def add(stamp, value):
        parsed = parse_utc(stamp)
        number = parse_kp_value(value)
        if parsed and number is not None:
            found[parsed] = number

    def walk(value):
        if isinstance(value, list):
            header = value[0] if value and isinstance(value[0], list) else value
            is_table = bool(header) and all(isinstance(x, str) for x in header) and any(
                str(x).lower() in ("time_tag", "datetime", "time", "date") for x in header
            )
            if is_table:
                headers = [str(x).lower() for x in header]
                ti = next((i for i, x in enumerate(headers) if x in ("time_tag", "datetime", "time", "date")), None)
                ki = next((i for i, x in enumerate(headers) if x in ("kp", "kp_index", "kpvalue")), None)
                if ti is not None and ki is not None:
                    rows = value[1:] if isinstance(value[0], list) else []
                    for row in rows:
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
