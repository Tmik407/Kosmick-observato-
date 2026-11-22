(()=>{'use strict';
const LAT=Array.from({length:9},(_,i)=>40+i*5),LON=Array.from({length:15},(_,i)=>-30+i*5);
const sites=[{name:'Severní Atlantik',lat:60,lon:-20},{name:'Arktida / sever Skandinávie',lat:70,lon:20},{name:'Západní Evropa',lat:50,lon:-10},{name:'Střední Evropa',lat:50,lon:15},{name:'Východní Evropa',lat:50,lon:35}];
const fields=['geopotential_height_500hPa','temperature_500hPa','wind_speed_500hPa','wind_direction_500hPa','geopotential_height_850hPa','temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
const URL='./data/europe-gfs/latest.json',KEY='x5-gfs:noaa-europe-v1';let pending=null,memory=null;
function cached(){try{return JSON.parse(localStorage.getItem(KEY)||'null');}catch(_){return null;}}
function shape(raw){
 if(!raw||!Array.isArray(raw.points)||raw.points.length!==140||!Array.isArray(raw.rows)||raw.rows.length!==140||!Array.isArray(raw.times)||!raw.times.length)throw Error('Archiv NOAA GFS má neúplnou strukturu.');
 const arr=raw.rows.map(r=>({hourly:r.hourly||{}}));
 for(const r of arr)for(const f of fields)if(!Array.isArray(r.hourly[f])||r.hourly[f].length!==raw.times.length)throw Error('V archivu NOAA chybí '+f+'.');
 return {times:raw.times,points:raw.points,arr,gridRows:9,gridCols:15,fields,updatedAt:raw.generated_utc,cycle:raw.cycle_utc,source:raw.source,stale:false};
}
async function request(){const r=await fetch(URL+'?v=1',{cache:'no-store'});if(!r.ok)throw Error('Archiv NOAA GFS HTTP '+r.status);const d=shape(await r.json());try{localStorage.setItem(KEY,JSON.stringify({data:d,at:Date.now()}));}catch(_){}return d;}
function get(options={}){
 if(memory&&!options.refresh)return Promise.resolve(memory);if(pending)return pending;const old=cached();
 if(old?.data&&!options.refresh){const d={...old.data,stale:true,cacheAgeHours:Math.round((Date.now()-(old.at||0))/3600000*10)/10};memory=d;pending=request().then(x=>(memory=x)).catch(()=>d).finally(()=>{pending=null;});return Promise.resolve(d);}
 pending=request().then(d=>(memory=d)).catch(e=>{if(old?.data){const d={...old.data,stale:true,cacheAgeHours:Math.round((Date.now()-(old.at||0))/3600000*10)/10,warning:String(e.message||e)};memory=d;return d;}throw e;}).finally(()=>{pending=null;});return pending;
}
function clear(){try{localStorage.removeItem(KEY);}catch(_){}memory=null;pending=null;}
window.X5GFS={get,clear,latitudes:LAT,longitudes:LON,sites,fields,api:'NOAA NOMADS GFS',archive:URL};
})();