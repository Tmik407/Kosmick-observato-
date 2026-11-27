#!/usr/bin/env python3
"""Archive NOAA SWPC solar wind, IMF and planetary Kp without interpolation.

Each upstream source is isolated: a temporary outage is recorded in metadata,
while the last known archive rows remain available and are never relabelled fresh.
"""
import json, math, urllib.request, subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT=Path("space-weather-history.json")
STATUS=Path("space-weather-status.json")
SOURCES={
 "wind":"https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json",
 "mag":"https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json",
 "kp":"https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"}
INVALID={-999.9,-999.0,-9999.0,9999.0}

def fetch(url):
 # Unique query parameter prevents stale intermediary/CDN responses on every scheduled run.
 separator="&" if "?" in url else "?"
 url=f"{url}{separator}_x5={int(datetime.now(timezone.utc).timestamp()*1000)}"
 req=urllib.request.Request(url,headers={"User-Agent":"Kosmicka-Observator-X5/1.2","Cache-Control":"no-cache","Pragma":"no-cache"})
 with urllib.request.urlopen(req,timeout=25) as r:
  return json.loads(r.read().decode("utf-8"))

def stamp(v):
 try:
  d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
  return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
 except (ValueError,TypeError): return None

def num(v,lo=-1e6,hi=1e6):
 try: x=float(v)
 except (ValueError,TypeError): return None
 return x if math.isfinite(x) and x not in INVALID and lo<=x<=hi else None

def records(payload):
 if not isinstance(payload,list) or not payload:return []
 if isinstance(payload[0],dict): return payload
 if isinstance(payload[0],list):
  h=[str(x).strip() for x in payload[0]]
  return [dict(zip(h,r)) for r in payload[1:] if isinstance(r,list)]
 return []

def nearest(items,t,limit):
 if not items:return None
 x=min(items,key=lambda a:abs((a["dt"]-t).total_seconds()))
 return x if abs((x["dt"]-t).total_seconds())<=limit else None

def latest_cached(rows, key):
 fields={"wind":("speed_kms","density_cm3"),"mag":("bx_gsm_nt","by_gsm_nt","bz_gsm_nt","bt_nt"),"kp":("kp",)}[key]
 times=[stamp(r.get("t")) for r in rows if any(r.get(f) is not None for f in fields)]
 times=[t for t in times if t is not None]
 return max(times) if times else None

def main():
 now=datetime.now(timezone.utc)
 wind=[]; mag=[]; kp=[]
 fetch_state={}
 for key in ("wind","mag","kp"):
  try:
   payload=fetch(SOURCES[key])
   fetch_state[key]={"ok":True,"error":None}
   if key=="wind":
    for r in records(payload):
     t=stamp(r.get("time_tag",r.get("time"))); s=num(r.get("proton_speed",r.get("speed")),0,3000); d=num(r.get("proton_density",r.get("density")),0,10000)
     if t and r.get("active",True) is True and (s is not None or d is not None): wind.append({"dt":t,"speed":s,"density":d})
   elif key=="mag":
    for r in records(payload):
     t=stamp(r.get("time_tag",r.get("time")))
     v={"bx":num(r.get("bx_gsm",r.get("bx")),-200,200),"by":num(r.get("by_gsm",r.get("by")),-200,200),"bz":num(r.get("bz_gsm",r.get("bz")),-200,200),"bt":num(r.get("bt"),0,300)}
     if t and r.get("active",True) is True and any(x is not None for x in v.values()): mag.append({"dt":t,**v})
   else:
    for r in records(payload):
     t=stamp(r.get("time_tag",r.get("time"))); k=num(r.get("Kp",r.get("kp")),0,9)
     if t and k is not None: kp.append({"dt":t,"kp":k})
  except Exception as exc:
   fetch_state[key]={"ok":False,"error":f"{type(exc).__name__}: {str(exc)[:500]}"}
   print(f"NOAA source {key} fetch failed: {fetch_state[key]['error']}")

 def parse_archive(raw):
  try:
   value,end=json.JSONDecoder().raw_decode(raw.lstrip())
   return value if isinstance(value,dict) else {}
  except json.JSONDecodeError:
   return {}
 try: old=parse_archive(OUT.read_text(encoding="utf-8"))
 except OSError: old={}
 old_rows=[r for r in old.get("rows",[]) if isinstance(r,dict) and r.get("t")]
 # Search recent archive revisions, not just HEAD^: a bad run may already
 # have committed a shortened archive after the last complete historical copy.
 try:
  revisions=subprocess.check_output(["git","log","-n","20","--format=%H","--","space-weather-history.json"],stderr=subprocess.DEVNULL,text=True).splitlines()
  best_rows=list(old_rows)
  for revision in revisions:
   try:
    raw=subprocess.check_output(["git","show",f"{revision}:space-weather-history.json"],stderr=subprocess.DEVNULL,text=True)
    candidate=parse_archive(raw)
    candidate_rows=[r for r in candidate.get("rows",[]) if isinstance(r,dict) and r.get("t")]
    if len(candidate_rows)>len(best_rows):
     best_rows=candidate_rows
   except (subprocess.CalledProcessError, OSError):
    continue
  if len(best_rows)>len(old_rows):
   print(f"Recovered historical archive rows from Git history: {len(best_rows)}")
   old_rows=best_rows
 except (subprocess.CalledProcessError, OSError):
  pass
 rows=[]
 for w in wind:
  m=nearest(mag,w["dt"],90); k=nearest(kp,w["dt"],5400)
  row={"t":w["dt"].isoformat().replace("+00:00","Z"),"speed_kms":w["speed"],"density_cm3":w["density"],
       "bx_gsm_nt":m["bx"] if m else None,"by_gsm_nt":m["by"] if m else None,
       "bz_gsm_nt":m["bz"] if m else None,"bt_nt":m["bt"] if m else None,
       "mag_delta_s":round(abs((m["dt"]-w["dt"]).total_seconds()),1) if m else None,
       "kp":k["kp"] if k else None,"kp_time":k["dt"].isoformat().replace("+00:00","Z") if k else None}
  row["pdyn_npa"]=round(1.6726e-6*w["density"]*w["speed"]**2,4) if w["density"] is not None and w["speed"] is not None else None
  row["ey_mv_m"]=round(w["speed"]*max(0,-m["bz"])*.001,4) if m and w["speed"] is not None and m["bz"] is not None else None
  rows.append(row)
 bytime={r["t"]:r for r in old_rows if stamp(r["t"])}
 bytime.update({r["t"]:r for r in rows})
 cutoff=now-timedelta(days=90)
 kept=[r for r in bytime.values() if stamp(r["t"]) and stamp(r["t"])>=cutoff]
 kept.sort(key=lambda r:r["t"])

 def source_meta(key, items, limit):
  measured=max((x["dt"] for x in items),default=None) if fetch_state[key]["ok"] else None
  if measured is None: measured=latest_cached(kept,key)
  # NOAA planetary Kp timestamps mark the start of a 3-hour interval.
  # For freshness, compare against the interval end; keep the original start
  # timestamp separately so the observation is never relabelled.
  reference=measured+timedelta(hours=3) if key=="kp" and measured else measured
  age=(now-reference).total_seconds() if reference else None
  if fetch_state[key]["ok"]:
   state="fresh" if age is not None and age<=limit*60 else "stale_or_missing"
  else:
   state="fetch_failed_cached_data" if age is not None else "fetch_failed_no_data"
  return {"last_measurement_utc":measured.isoformat().replace("+00:00","Z") if measured else None,
          "freshness_reference_utc":reference.isoformat().replace("+00:00","Z") if reference else None,
          "measurement_interval_minutes":180 if key=="kp" else 1,
          "fetched_utc":now.isoformat().replace("+00:00","Z") if fetch_state[key]["ok"] else None,
          "last_attempt_utc":now.isoformat().replace("+00:00","Z"),
          "request_status":"success" if fetch_state[key]["ok"] else "failed",
          "error":fetch_state[key]["error"],
          "age_seconds_at_fetch":round(age,1) if age is not None else None,
          "freshness_limit_minutes":limit,"status":state,
          "records_received":len(items) if fetch_state[key]["ok"] else 0}
 source_status={"wind":source_meta("wind",wind,10),"mag":source_meta("mag",mag,10),"kp":source_meta("kp",kp,240)}
 payload={"source":SOURCES,"updated_utc":now.isoformat().replace("+00:00","Z"),
 "fetched_utc":now.isoformat().replace("+00:00","Z"),"source_status":source_status,"sampling_interval_minutes":5,
 "retention_days":90,"sampling_interval_minutes":1,"workflow_schedule_interval_minutes":5,"timestamp_basis":"NOAA measurement timestamps in UTC; source feed is 1-minute cadence; workflow attempts every 5 minutes",
 "derived_fields":["pdyn_npa","ey_mv_m"],"quality":{"invalid_sentinels_rejected":sorted(INVALID),
 "magnetic_pair_tolerance_seconds":90,"kp_pair_tolerance_seconds":5400,"interpolation":False},
 "note":"Dst není zahrnuto: zatím není připojen a ověřen samostatný zdroj Dst.",
 "rows":kept}
 tmp=OUT.with_suffix(".json.tmp")
 tmp.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 tmp.replace(OUT)
 status_payload={
  "source":"NOAA SWPC real-time solar wind, IMF and planetary Kp",
  "updated_utc":payload["updated_utc"],
  "fetched_utc":payload["fetched_utc"],
  "sampling_interval_minutes":payload["sampling_interval_minutes"],
  "workflow_schedule_interval_minutes":payload["workflow_schedule_interval_minutes"],
  "archive_records":len(kept),
  "archive_latest_measurement_utc":kept[-1]["t"] if kept else None,
  "source_status":source_status
 }
 status_tmp=STATUS.with_suffix(".json.tmp")
 status_tmp.write_text(json.dumps(status_payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 status_tmp.replace(STATUS)
 print("NOAA fetch status:",json.dumps({k:{"ok":v["ok"],"error":v["error"]} for k,v in fetch_state.items()}))
 print(f"NOAA records wind={len(wind)}, mag={len(mag)}, Kp={len(kp)}; archive={len(kept)}")
if __name__=="__main__": main()
