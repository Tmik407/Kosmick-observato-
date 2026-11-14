#!/usr/bin/env python3
"""Build a transparent CH1411 solar-wind impact comparison from archived NOAA observations."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(".")
EVENTS=ROOT/"coronal-hole-history.json"
WIND=ROOT/"space-weather-history.json"
OUT=ROOT/"ch1411-impact.json"

def dt(v):
    try:
        x=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except (ValueError,TypeError):
        return None

def stats(rows):
    fields=("speed_kms","density_cm3","bt_nt","bz_gsm_nt","pdyn_npa","ey_mv_m")
    out={"samples":len(rows)}
    for key in fields:
        vals=[float(r[key]) for r in rows if isinstance(r.get(key),(int,float))]
        out[key]={"n":len(vals),"mean":round(sum(vals)/len(vals),3) if vals else None,
                  "min":round(min(vals),3) if vals else None,"max":round(max(vals),3) if vals else None}
    bz=[float(r["bz_gsm_nt"]) for r in rows if isinstance(r.get("bz_gsm_nt"),(int,float))]
    out["south_bz_minutes_estimate"]=sum(1 for v in bz if v<=-5)
    out["strong_south_bz_minutes_estimate"]=sum(1 for v in bz if v<=-10)
    out["note"]="Počet minutových vzorků; není to souvislá doba, pokud v datech jsou mezery."
    return out

def main():
    events=json.loads(EVENTS.read_text(encoding="utf-8"))
    history=json.loads(WIND.read_text(encoding="utf-8"))
    event=next((x for x in events.get("events",[]) if x.get("id")=="CH1411"),None)
    if not event: raise SystemExit("CH1411 event not found")
    rows=[]
    for r in history.get("rows",[]):
        t=dt(r.get("t"))
        if not t: continue
        clean={"t":t.isoformat().replace("+00:00","Z")}
        for k in ("speed_kms","density_cm3","bt_nt","bz_gsm_nt","pdyn_npa","ey_mv_m","kp"):
            v=r.get(k)
            clean[k]=float(v) if isinstance(v,(int,float)) else None
        rows.append((t,clean))
    start=datetime(2026,11,13,tzinfo=timezone.utc)
    end=datetime(2026,11,20,tzinfo=timezone.utc)
    baseline=[r for t,r in rows if start<=t<datetime(2026,11,16,tzinfo=timezone.utc)]
    arrival=[r for t,r in rows if datetime(2026,11,16,tzinfo=timezone.utc)<=t<end]
    observed=[r for t,r in rows if start<=t<end]
    now=datetime.now(timezone.utc)
    payload={
      "event_id":"CH1411","updated_utc":now.isoformat().replace("+00:00","Z"),
      "event_date_utc":"2026-11-13",
      "expected_window_utc":["2026-11-16","2026-11-17"],
      "data_latest_utc":rows[-1][0].isoformat().replace("+00:00","Z") if rows else None,
      "archive_updated_utc":history.get("updated_utc"),
      "baseline":{"start_utc":"2026-11-13T00:00:00Z","end_utc":"2026-11-16T00:00:00Z","statistics":stats(baseline)},
      "expected_arrival_period":{"start_utc":"2026-11-16T00:00:00Z","end_utc":"2026-11-20T00:00:00Z","statistics":stats(arrival)},
      "observed_since_event":{"statistics":stats(observed),"series":[r for t,r in rows if start<=t<end][-600:]},
      "assessment":"Čeká se na očekávané období příletu." if now<datetime(2026,11,16,tzinfo=timezone.utc) else ("Probíhá sledování očekávaného období; příčinná souvislost s CH1411 zatím není prokázána." if now<end else "Období sledování skončilo; porovnejte odchylky proti výchozímu stavu."),
      "method":"Bez interpolace. Baseline 13.–15. 11. UTC; sledované období 16.–19. 11. UTC. Statistika vychází pouze z dostupných minutových vzorků NOAA RTSW; Kp se uvádí pouze pokud je časově spárované. Dst není součástí archivu.",
      "quality":{"baseline_samples":len(baseline),"arrival_samples":len(arrival),"observed_samples":len(observed),"missing_fields":["Dst"],"causality":"Koronální díra je hypotetický zdroj; časová shoda sama neprokazuje příčinnou souvislost."}
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("CH1411 impact:",len(baseline),"baseline samples;",len(arrival),"arrival samples; latest",payload["data_latest_utc"])
if __name__=="__main__": main()
