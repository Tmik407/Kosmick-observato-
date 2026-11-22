#!/usr/bin/env python3
"""NOAA NOMADS GFS archive for the shared European 500/850 hPa maps."""
import datetime as dt,json,math,pathlib,sys,time,tempfile
from urllib.parse import urlencode
import requests,numpy as np
from eccodes import codes_grib_new_from_file,codes_get,codes_get_array,codes_release
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/"data/europe-gfs/latest.json"
LAT=[40+i*5 for i in range(9)]; LON=[-30+i*5 for i in range(15)]
SITES=[{"name":"Severní Atlantik","lat":60,"lon":-20},{"name":"Arktida / sever Skandinávie","lat":70,"lon":20},{"name":"Západní Evropa","lat":50,"lon":-10},{"name":"Střední Evropa","lat":50,"lon":15},{"name":"Východní Evropa","lat":50,"lon":35}]
POINTS=[{"lat":a,"lon":b} for a in LAT for b in LON]+SITES
LEVELS=(500,850); HOURS=tuple(range(0,73,3)); S=requests.Session(); S.headers["User-Agent"]="KosmickaObservator-X5/1.0"
def url(day,cycle,h):
 name=f"gfs.t{cycle:02d}z.pgrb2.0p25.f{h:03d}"
 p=[("file",name)]+[(f"lev_{z}_mb","on") for z in LEVELS]+[(f"var_{v}","on") for v in ("TMP","HGT","UGRD","VGRD")]
 p += [("subregion",""),("leftlon","330"),("rightlon","40"),("toplat","80"),("bottomlat","40"),("dir",f"/gfs.{day:%Y%m%d}/{cycle:02d}/atmos")]
 return "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?"+urlencode(p)
def get(u):
 r=S.get(u,timeout=(25,180))
 if r.status_code!=200: raise RuntimeError(f"NOMADS HTTP {r.status_code}: {r.text[:120]}")
 if not r.content.startswith(b"GRIB"): raise RuntimeError("NOMADS nevrátil GRIB2")
 return r.content
def decode(body):
 out={}
 with tempfile.TemporaryFile(mode="w+b") as f:
  f.write(body);f.seek(0)
  while True:
   g=codes_grib_new_from_file(f)
   if g is None:break
   try:
    sh=str(codes_get(g,"shortName")).lower(); lev=int(codes_get(g,"level")); typ=str(codes_get(g,"typeOfLevel"))
    key={"gh":"z","t":"t","u":"u","v":"v"}.get(sh)
    if key and lev in LEVELS and typ in ("isobaricInhPa","isobaricInPa"):
     la=np.asarray(codes_get_array(g,"latitudes"),float);lo=np.asarray(codes_get_array(g,"longitudes"),float);v=np.asarray(codes_get_array(g,"values"),float);ids=[]
     for p in POINTS:
      dl=((lo-p["lon"]+180)%360)-180; d=(la-p["lat"])**2+(dl*max(.2,math.cos(math.radians(p["lat"]))))**2;ids.append(int(np.nanargmin(d)))
     out[(lev,key)]=[float(v[i]) if np.isfinite(v[i]) else None for i in ids]
   finally:codes_release(g)
 return out
def main():
 now=dt.datetime.now(dt.timezone.utc);chosen=None
 for day in (now.date(),now.date()-dt.timedelta(days=1)):
  for cyc in (18,12,6,0):
   base=dt.datetime.combine(day,dt.time(cyc),tzinfo=dt.timezone.utc)
   if base>now+dt.timedelta(hours=1):continue
   try:chosen=(day,cyc,get(url(day,cyc,0)));break
   except Exception as e:print(f"Cyklus {day} {cyc:02d}Z: {e}",flush=True)
  if chosen:break
 if not chosen:raise RuntimeError("Není dostupný cyklus GFS.")
 day,cyc,first=chosen;base=dt.datetime.combine(day,dt.time(cyc),tzinfo=dt.timezone.utc)
 names=("geopotential_height","temperature","wind_speed","wind_direction")
 rows=[{"hourly":{f"{n}_{z}hPa":[] for z in LEVELS for n in names}} for _ in POINTS];times=[]
 for k,h in enumerate(HOURS):
  d=decode(first if h==0 else get(url(day,cyc,h)));times.append((base+dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"))
  for z in LEVELS:
   for key in ("z","t","u","v"):
    if (z,key) not in d:raise RuntimeError(f"Chybí pole {key} na {z} hPa v kroku f{h:03d}")
   for i in range(len(POINTS)):
    u,v=d[(z,"u")][i],d[(z,"v")][i]; speed=math.hypot(u,v)*3.6 if u is not None and v is not None else None
    direction=math.degrees(math.atan2(-u,-v))%360 if u is not None and v is not None else None
    rows[i]["hourly"][f"geopotential_height_{z}hPa"].append(d[(z,"z")][i])
    t=d[(z,"t")][i];rows[i]["hourly"][f"temperature_{z}hPa"].append(t-273.15 if t is not None else None)
    rows[i]["hourly"][f"wind_speed_{z}hPa"].append(speed);rows[i]["hourly"][f"wind_direction_{z}hPa"].append(direction)
  print(f"NOAA GFS Evropa f{h:03d} OK",flush=True)
  if k<len(HOURS)-1:time.sleep(3)
 payload={"source":"NOAA NOMADS GFS 0.25° GRIB2","classification":"NUMERICAL_WEATHER_PREDICTION","generated_utc":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"cycle_utc":base.strftime("%Y-%m-%dT%H:%MZ"),"step_hours":3,"points":POINTS,"times":times,"rows":rows,"grid":{"latitudes":LAT,"longitudes":LON,"rows":9,"columns":15},"note":"Modelová analýza a předpověď GFS, nikoli měření; evropská síť 5°."}
 OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix(".tmp");tmp.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf-8");tmp.replace(OUT)
 print(f"Archiv NOAA uložen: {len(POINTS)} bodů × {len(times)} časů")
if __name__=="__main__":
 try:main()
 except Exception as e:print(f"Chyba NOAA GFS: {e}",file=sys.stderr);raise
