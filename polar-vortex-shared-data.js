(()=>{'use strict';
const API='https://api.open-meteo.com/v1/gfs';
const LAT=Array.from({length:7},(_,i)=>30+i*10),LON=Array.from({length:13},(_,i)=>-60+i*10);
const sites=[{name:'Severní Atlantik',lat:60,lon:-20},{name:'Arktida / sever Skandinávie',lat:70,lon:20},{name:'Západní Evropa',lat:50,lon:-10},{name:'Střední Evropa',lat:50,lon:15},{name:'Východní Evropa',lat:50,lon:35}];
const fields=['geopotential_height_500hPa','temperature_500hPa','wind_speed_500hPa','wind_direction_500hPa','geopotential_height_850hPa','temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
const key='x5-gfs:shared-europe-v1';
let pending=null;
function cached(){try{return JSON.parse(localStorage.getItem(key)||'null');}catch(_){return null;}}
function coords(){return LAT.flatMap(lat=>LON.map(lon=>({lat,lon}))).concat(sites);}
async function request(){
 const points=coords(),q=new URLSearchParams({latitude:points.map(p=>p.lat).join(','),longitude:points.map(p=>p.lon).join(','),hourly:fields.join(','),forecast_days:'7',timezone:'GMT',wind_speed_unit:'kmh'});
 const r=await fetch(API,{method:'POST',body:q,cache:'no-store'});
 if(!r.ok)throw Error('Open-Meteo GFS HTTP '+r.status);
 const raw=await r.json(),arr=Array.isArray(raw)?raw:[raw];
 if(arr.length!==points.length)throw Error('GFS vrátil '+arr.length+' z '+points.length+' bodů.');
 const times=arr[0]?.hourly?.time;
 if(!Array.isArray(times)||!times.length)throw Error('GFS nevrátil časovou osu.');
 for(const x of arr)for(const f of fields)if(!Array.isArray(x.hourly?.[f])||x.hourly[f].length!==times.length)throw Error('GFS postrádá '+f+'.');
 const data={times,points,arr,gridRows:LAT.length,gridCols:LON.length,fields,updatedAt:new Date().toISOString()};
 try{localStorage.setItem(key,JSON.stringify({data,at:Date.now()}));}catch(_){}
 return data;
}
function get(options={}){
 if(pending)return pending;
 const old=cached();
 pending=request().catch(err=>{
  if(old?.data){const d=old.data;d.stale=true;d.cacheAgeHours=Math.round((Date.now()-old.at)/3600000*10)/10;d.warning=String(err.message||err);return d;}
  throw err;
 }).finally(()=>{pending=null;});
 return pending;
}
function clear(){try{localStorage.removeItem(key);}catch(_){}pending=null;}
window.X5GFS={get,clear,latitudes:LAT,longitudes:LON,sites,fields,api:API};
})();