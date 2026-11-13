#!/usr/bin/env python3
"""Archive NOAA SWPC solar wind, IMF and planetary Kp without interpolation."""
import json, math, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT=Path("space-weather-history.json")
SOURCES={
 "wind":"https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json",
 "mag":"https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json",
 "kp":"https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"}
INVALID={-999.9,-999.0,-9999.0,9999.0}
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Kosmicka-Observator-X5/1.0"})
 with urllib.request.urlopen(req,timeout=40) as r: return json.loads(r.read().decode("utf-8"))
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
def main():
 now=datetime.now(timezone.utc)
 wind=[]; mag=[]; kp=[]
 for r in records(fetch(SOURCES["wind"])):
  t=stamp(r.get("time_tag",r.get("time"))); s=num(r.get("proton_speed",r.get("speed")),0,3000); d=num(r.get("proton_density",r.get("density")),0,10000)
  if t and r.get("active",True) is True and (s is not None or d is not None): wind.append({"dt":t,"speed":s,"density":d})
 for r in records(fetch(SOURCES["mag"])):
  t=stamp(r.get("time_tag",r.get("time")))
  v={"bx":num(r.get("bx_gsm",r.get("bx")),-200,200),"by":num(r.get("by_gsm",r.get("by")),-200,200),"bz":num(r.get("bz_gsm",r.get("bz")),-200,200),"bt":num(r.get("bt"),0,300)}
  if t and r.get("active",True) is True and any(x is not None for x in v.values()): mag.append({"dt":t,**v})
 for r in records(fetch(SOURCES["kp"])):
  t=stamp(r.get("time_tag",r.get("time"))); k=num(r.get("Kp",r.get("kp")),0,9)
  if t and k is not None: kp.append({"dt":t,"kp":k})
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
 try: old=json.loads(OUT.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): old={}
 bytime={r["t"]:r for r in old.get("rows",[]) if isinstance(r,dict) and r.get("t")}
 bytime.update({r["t"]:r for r in rows})
 cutoff=now-timedelta(days=90)
 kept=[r for r in bytime.values() if stamp(r["t"]) and stamp(r["t"])>=cutoff]
 kept.sort(key=lambda r:r["t"])
 payload={"source":SOURCES,"updated_utc":now.isoformat().replace("+00:00","Z"),"sampling_interval_minutes":5,
 "retention_days":90,"timestamp_basis":"NOAA measurement timestamps in UTC; anchored to actual wind timestamps",
 "derived_fields":["pdyn_npa","ey_mv_m"],"quality":{"invalid_sentinels_rejected":sorted(INVALID),
 "magnetic_pair_tolerance_seconds":90,"kp_pair_tolerance_seconds":5400,"interpolation":False},
 "note":"Dst není zahrnuto: zatím není připojen a ověřen samostatný zdroj Dst.",
 "rows":kept}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 print(f"NOAA records wind={len(wind)}, mag={len(mag)}, Kp={len(kp)}; archive={len(kept)}")
if __name__=="__main__": main()
