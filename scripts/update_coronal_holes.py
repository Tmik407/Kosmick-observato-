#!/usr/bin/env python3
"""Fetch the newest NOAA GOES-19 SUVI L2 coronal-hole boundary product."""
import json, os, re, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from netCDF4 import Dataset
import numpy as np

BASE = "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes19/l2/data/suvi-l2-chbnd/"
OUT = Path("coronal-hole-history.json")

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href: self.hrefs.append(href)

def listing(url):
    req=urllib.request.Request(url, headers={"User-Agent":"Kosmicka-Observator-X5/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r: html=r.read().decode("utf-8","replace")
    p=Links(); p.feed(html); return p.hrefs

def newest_product():
    root_links=listing(BASE)
    print("NOAA CHBND root links:", root_links[:30], flush=True)
    years=sorted([x.strip("/") for x in root_links if re.fullmatch(r"20\d{2}/?",x)], reverse=True)
    for year in years:
        yu=BASE+year+"/"
        month_links=listing(yu)
        print("NOAA year links:", month_links[:30], flush=True)
        months=sorted([x.strip("/") for x in month_links if re.fullmatch(r"\d{2}/?",x)], reverse=True)
        for month in months:
            mu=yu+month+"/"
            day_links=listing(mu)
            print("NOAA month links:", day_links[:30], flush=True)
            days=sorted([x.strip("/") for x in day_links if re.fullmatch(r"\d{2}/?",x)], reverse=True)
            for day in days:
                du=mu+day+"/"
                file_links=listing(du)
                files=sorted([x for x in file_links if ".nc" in x and "_s" in x])
                if file_links and not files: print("NOAA day links:", file_links[:5], flush=True)
                if files: return du+files[-1], files[-1]
    raise RuntimeError("NOAA SUVI L2 CHBND directory contains no NetCDF products")

def scalar(ds, name, default=None):
    if name not in ds.variables: return default
    a=np.ma.asarray(ds.variables[name][:]).filled(np.nan)
    if a.size == 0: return default
    value=np.asarray(a).reshape(-1)[0]
    value=value.item() if hasattr(value,"item") else value
    return value.decode("utf-8","replace") if isinstance(value,bytes) else value

def arr(ds, name):
    if name not in ds.variables: return []
    a=np.ma.asarray(ds.variables[name][:]).filled(np.nan)
    return np.asarray(a).tolist()

def parse_file(url, filename):
    local=Path("/tmp/suvi-chbnd.nc")
    req=urllib.request.Request(url, headers={"User-Agent":"Kosmicka-Observator-X5/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r: local.write_bytes(r.read())
    with Dataset(local) as ds:
        n=int(scalar(ds,"num_chbnd",0) or 0)
        areas=np.asarray(arr(ds,"chbnd_area"),dtype=float).reshape(-1).tolist()
        ext=np.asarray(arr(ds,"chbnd_extent_hg"),dtype=float)
        if ext.size: ext=ext.reshape((-1,4)).tolist()
        else: ext=[]
        degraded=scalar(ds,"degraded_status","unknown")
        t=scalar(ds,"time",None)
        observed=None
        if t is not None and np.isfinite(float(t)):
            from datetime import timedelta
            observed=(datetime(2000,1,1,12,tzinfo=timezone.utc)+timedelta(seconds=float(t))).isoformat().replace("+00:00","Z")
        holes=[]
        for i in range(n):
            e=ext[i] if i<len(ext) else [None]*4
            area=areas[i] if i<len(areas) else None
            holes.append({"id":i+1,"area_px2":area if area is not None and np.isfinite(area) else None,
                          "north_deg":float(e[0]) if e[0] is not None and np.isfinite(float(e[0])) else None,
                          "south_deg":float(e[1]) if e[1] is not None and np.isfinite(float(e[1])) else None,
                          "east_deg":float(e[2]) if e[2] is not None and np.isfinite(float(e[2])) else None,
                          "west_deg":float(e[3]) if e[3] is not None and np.isfinite(float(e[3])) else None})
        return {"source":"NOAA GOES-19 SUVI L2 CHBND","product":filename,"url":url,
                "observed_utc":observed,"retrieved_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
                "num_coronal_holes":n,"degraded_status":degraded,"holes":holes}

def main():
    url, filename=newest_product()
    current=parse_file(url,filename)
    try: old=json.loads(OUT.read_text(encoding="utf-8"))
    except Exception: old={"rows":[]}
    rows=old.get("rows",[])
    if not any(x.get("product")==filename for x in rows): rows.append(current)
    rows=rows[-180:]
    # Preserve curated event annotations across automatic NOAA archive refreshes.
    events=old.get("events",[]) if isinstance(old,dict) else []
    payload={"source":"NOAA NCEI GOES-19 SUVI Level 2 Coronal Hole Boundaries",
             "updated_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
             "latest":current,"rows":rows,"events":events}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"NOAA product {filename}: {current['num_coronal_holes']} holes; degraded_status={current['degraded_status']}")

if __name__=="__main__": main()
