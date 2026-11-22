(()=>{'use strict';
const API='https://api.open-meteo.com/v1/gfs';
const LAT=Array.from({length:9},(_,i)=>40+i*5),LON=Array.from({length:15},(_,i)=>-30+i*5);
const sites=[{name:'Severní Atlantik',lat:60,lon:-20},{name:'Arktida / sever Skandinávie',lat:70,lon:20},{name:'Západní Evropa',lat:50,lon:-10},{name:'Střední Evropa',lat:50,lon:15},{name:'Východní Evropa',lat:50,lon:35}];
const fields=['geopotential_height_500hPa','temperature_500hPa','wind_speed_500hPa','wind_direction_500hPa','geopotential_height_850hPa','temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
const key='x5-gfs:shared-europe-135-v3',MAX_AGE=60*60*1000;
let pending=null,memory=null;
function cached(){try{return JSON.parse(localStorage.getItem(key)||localStorage.getItem('x5-gfs:shared-europe-v1')||'null');}catch(_){return null;}}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function fetchChunk(points){
 const q=new URLSearchParams({latitude:points.map(p=>p.lat).join(','),longitude:points.map(p=>p.lon).join(','),hourly:fields.join(','),forecast_days:'3',timezone:'GMT',wind_speed_unit:'kmh'});
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);
 try{
  const response=await fetch(API+'?'+q.toString(),{method:'GET',signal:controller.signal,cache:'default'});
  if(response.status===429)throw new Error('Open-Meteo omezuje počet požadavků (HTTP 429). Další automatické opakování bylo zastaveno.');
  if(!response.ok)throw new Error('Open-Meteo GFS HTTP '+response.status);
  const raw=await response.json(),arr=Array.isArray(raw)?raw:[raw];
  if(arr.length!==points.length)throw new Error('GFS vrátil '+arr.length+' z '+points.length+' bodů.');
  return arr;
 }catch(e){
  if(e.name==='AbortError')throw new Error('Požadavek na GFS překročil limit 25 sekund.');
  throw e;
 }finally{clearTimeout(timer);}
}
function coords(){return LAT.flatMap(lat=>LON.map(lon=>({lat,lon}))).concat(sites);}
async function request(){
 const points=coords(),arr=[];
 // Open-Meteo public endpoint: smaller sequential batches reduce rate-limit pressure.
 for(let i=0;i<points.length;i+=70){
  if(i)await sleep(1500);
  arr.push(...await fetchChunk(points.slice(i,i+70)));
 }
 const times=arr[0]?.hourly?.time;
 if(!Array.isArray(times)||!times.length)throw new Error('GFS nevrátil časovou osu.');
 for(const x of arr)for(const f of fields)if(!Array.isArray(x.hourly?.[f])||x.hourly[f].length!==times.length)throw new Error('GFS postrádá '+f+'.');
 const data={times,points,arr,gridRows:LAT.length,gridCols:LON.length,fields,updatedAt:new Date().toISOString()};
 try{localStorage.setItem(key,JSON.stringify({data,at:Date.now()}));}catch(_){}
 return data;
}
function get(options={}){
 if(memory&&!options.refresh)return Promise.resolve(memory);
 if(pending)return pending;
 const old=cached();
 if(old?.data&&!options.refresh){
  // Show the last successful forecast immediately; refresh it in the background.
  const d={...old.data,stale:true,cacheAgeHours:Math.round((Date.now()-(old.at||0))/3600000*10)/10};
  memory=d;
  pending=request().then(fresh=>{memory=fresh;return fresh;}).catch(()=>d).finally(()=>{pending=null;});
  return Promise.resolve(d);
 }
 pending=request().then(d=>{memory=d;return d;}).catch(err=>{
  if(old?.data){const d={...old.data,stale:true,cacheAgeHours:Math.round((Date.now()-(old.at||0))/3600000*10)/10,warning:String(err.message||err)};memory=d;return d;}
  throw err;
 }).finally(()=>{pending=null;});
 return pending;
}
function clear(){try{localStorage.removeItem(key);}catch(_){}pending=null;memory=null;}
window.X5GFS={get,clear,latitudes:LAT,longitudes:LON,sites,fields,api:API};
})();