#!/usr/bin/env python3
"""NOAA NOMADS GFS archive for European 500/850 hPa maps."""
import datetime as dt, json, math, pathlib, sys, time, tempfile
from urllib.parse import urlencode
import requests, numpy as np
from eccodes import codes_grib_new_from_file, codes_get, codes_get_array, codes_release

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"europe-gfs"/"latest.json"
LAT=[40+i*5 for i in range(9)]
LON=[-30+i*5 for i in range(15)]
SITES=[{"name":"Severní Atlantik","lat":60,"lon":-20},
{"name":"Arktida / sever Skandinávie","lat":70,"lon":20},
{"name":"Západní Evropa","lat":50,"lon":-10},
{"name":"Střední Evropa","lat":50,"lon":15},
{"name":"Východní Evropa","lat":50,"lon":35}]
POINTS=[{"lat":a,"lon":b} for a in LAT for b in LON]+SITES
LEVELS=(500,850)
HOURS=tuple(range(0,73,3))
SESSION=requests.Session()
SESSION.headers["User-Agent"]="KosmickaObservator-X5/1.0"

def make_url(day,cycle,hour,west):
 name=f"gfs.t{cycle:02d}z.pgrb2.0p25.f{hour:03d}"
 params=[("file",name)]
 params += [(f"lev_{lev}_mb","on") for lev in LEVELS]
 params += [(f"var_{v}","on") for v in ("TMP","HGT","UGRD","VGRD")]
 left,right=("330","359.75") if west else ("0","40")
 params += [("subregion",""),("leftlon",left),("rightlon",right),
 ("toplat","80"),("bottomlat","40"),("dir",f"/gfs.{day:%Y%m%d}/{cycle:02d}/atmos")]
 return "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?"+urlencode(params)

def download(url):
 response=SESSION.get(url,timeout=(25,180))
 if response.status_code!=200:
  raise RuntimeError(f"NOMADS HTTP {response.status_code}: {response.text[:120]}")
 if not response.content.startswith(b"GRIB"):
  raise RuntimeError("NOMADS nevrátil GRIB2: "+response.text[:100])
 return response.content

def decode(body,indices):
 result={}
 with tempfile.TemporaryFile(mode="w+b") as stream:
  stream.write(body); stream.seek(0)
  while True:
   gid=codes_grib_new_from_file(stream)
   if gid is None: break
   try:
    short=str(codes_get(gid,"shortName")).lower()
    level=int(codes_get(gid,"level"))
    typ=str(codes_get(gid,"typeOfLevel"))
    key={"gh":"z","t":"t","u":"u","v":"v"}.get(short)
    if key and level in LEVELS and typ in ("isobaricInhPa","isobaricInPa"):
     lat=np.asarray(codes_get_array(gid,"latitudes"),float)
     lon=np.asarray(codes_get_array(gid,"longitudes"),float)
     values=np.asarray(codes_get_array(gid,"values"),float)
     picked=[]
     for point_index in indices:
      point=POINTS[point_index]
      dlon=((lon-point["lon"]+180)%360)-180
      distance=(lat-point["lat"])**2+(dlon*max(.2,math.cos(math.radians(point["lat"]))))**2
      ix=int(np.nanargmin(distance))
      picked.append(float(values[ix]) if np.isfinite(values[ix]) else None)
     result[(level,key)]=picked
   finally:
    codes_release(gid)
 return result

def combine(east,west):
 east_ids=[i for i,p in enumerate(POINTS) if p["lon"]>=0]
 west_ids=[i for i,p in enumerate(POINTS) if p["lon"]<0]
 merged={}
 for level in LEVELS:
  for key in ("z","t","u","v"):
   values=[None]*len(POINTS)
   for ids,part in ((east_ids,east),(west_ids,west)):
    subset=part.get((level,key),[])
    if len(subset)!=len(ids):
     raise RuntimeError(f"Chybí část GFS {key} na {level} hPa")
    for ix,value in zip(ids,subset):
     values[ix]=value
   merged[(level,key)]=values
 return merged

def main():
 now=dt.datetime.now(dt.timezone.utc)
 chosen=None
 for day in (now.date(),now.date()-dt.timedelta(days=1)):
  for cycle in (18,12,6,0):
   base=dt.datetime.combine(day,dt.time(cycle),tzinfo=dt.timezone.utc)
   if base>now+dt.timedelta(hours=1): continue
   try:
    first=(download(make_url(day,cycle,0,False)),download(make_url(day,cycle,0,True)))
    chosen=(day,cycle,first)
    break
   except Exception as exc:
    print(f"Cyklus {day} {cycle:02d}Z: {exc}",flush=True)
  if chosen: break
 if not chosen:
  raise RuntimeError("Na NOAA NOMADS není dostupný cyklus GFS.")
 day,cycle,first=chosen
 base=dt.datetime.combine(day,dt.time(cycle),tzinfo=dt.timezone.utc)
 names=("geopotential_height","temperature","wind_speed","wind_direction")
 rows=[{"hourly":{f"{name}_{lev}hPa":[] for lev in LEVELS for name in names}} for _ in POINTS]
 times=[]
 for step,hour in enumerate(HOURS):
  bodies=first if hour==0 else (download(make_url(day,cycle,hour,False)),download(make_url(day,cycle,hour,True)))
  east_ids=[i for i,p in enumerate(POINTS) if p["lon"]>=0]
  west_ids=[i for i,p in enumerate(POINTS) if p["lon"]<0]
  fields=combine(decode(bodies[0],east_ids),decode(bodies[1],west_ids))
  times.append((base+dt.timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M"))
  for lev in LEVELS:
   for key in ("z","t","u","v"):
    if not any(v is not None for v in fields[(lev,key)]):
     raise RuntimeError(f"Prázdné pole {key} na {lev} hPa, f{hour:03d}")
   for i in range(len(POINTS)):
    u,v=fields[(lev,"u")][i],fields[(lev,"v")][i]
    speed=math.hypot(u,v)*3.6 if u is not None and v is not None else None
    direction=math.degrees(math.atan2(-u,-v))%360 if u is not None and v is not None else None
    rows[i]["hourly"][f"geopotential_height_{lev}hPa"].append(fields[(lev,"z")][i])
    temp=fields[(lev,"t")][i]
    rows[i]["hourly"][f"temperature_{lev}hPa"].append(temp-273.15 if temp is not None else None)
    rows[i]["hourly"][f"wind_speed_{lev}hPa"].append(speed)
    rows[i]["hourly"][f"wind_direction_{lev}hPa"].append(direction)
  print(f"NOAA GFS Evropa f{hour:03d} hotovo",flush=True)
  if step<len(HOURS)-1: time.sleep(3)
 payload={"source":"NOAA NOMADS GFS 0.25° GRIB2","classification":"NUMERICAL_WEATHER_PREDICTION",
 "generated_utc":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"cycle_utc":base.strftime("%Y-%m-%dT%H:%MZ"),
 "step_hours":3,"points":POINTS,"times":times,"rows":rows,
 "grid":{"latitudes":LAT,"longitudes":LON,"rows":9,"columns":15},
 "note":"Modelová analýza a předpověď GFS, nikoli měření; evropská síť 5°."}
 OUT.parent.mkdir(parents=True,exist_ok=True)
 temporary=OUT.with_suffix(".tmp")
 temporary.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf-8")
 temporary.replace(OUT)
 print(f"Archiv NOAA uložen: {len(POINTS)} bodů × {len(times)} časů")

if __name__=="__main__":
 try:
  main()
 except Exception as exc:
  print(f"Chyba NOAA GFS: {exc}",file=sys.stderr)
  raise
