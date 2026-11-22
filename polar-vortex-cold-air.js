(()=>{'use strict';
const $=id=>document.getElementById(id),LAT=Array.from({length:13},(_,i)=>30+i*5),LON=Array.from({length:25},(_,i)=>-60+i*5),API='https://api.open-meteo.com/v1/gfs';
const fields=['temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
let times=[],cells=[],track=[];
async function x5QueuedFetch(url,init={}){
 const body=init.body?String(init.body):'',key='x5-gfs:'+url+':'+body;
 const readCache=()=>{try{const x=localStorage.getItem(key);return x?JSON.parse(x):null;}catch(_){return null;}};
 const saveCache=async response=>{try{if(response.ok){const data=await response.clone().text();localStorage.setItem(key,JSON.stringify({at:Date.now(),data}));}}catch(_){}};
 const cached=readCache();
 const run=async()=>{
  let last;
  for(let attempt=0;attempt<2;attempt++){
   try{
    const response=await fetch(url,init);
    if(response.status===429&&attempt===0){last=new Error('HTTP 429 – GFS dočasně omezuje požadavky');await new Promise(r=>setTimeout(r,12000));continue;}
    if(response.ok)await saveCache(response);
    return response;
   }catch(e){last=e;if(attempt===0)await new Promise(r=>setTimeout(r,2500));}
  }
  throw last||new Error('Požadavek GFS selhal.');
 };
 const previous=window.__x5OpenMeteoQueue||Promise.resolve();
 const task=previous.then(run,run);
 window.__x5OpenMeteoQueue=task.then(()=>new Promise(r=>setTimeout(r,3000)),()=>new Promise(r=>setTimeout(r,3000)));
 if(cached&&cached.data){
  // Zobraz poslední úspěšná data ihned; aktualizace proběhne na pozadí.
  task.catch(()=>{});
  return new Response(cached.data,{status:200,headers:{'Content-Type':'application/json','X-X5-Cache':'stale-ok'}});
 }
 return task;
}
async function load(){
 const status=$('pvx5ColdStatus');if(status)status.textContent='Čekám na volný přístup k GFS; načítám 325 bodů v jednom požadavku…';
 try{
  const coords=LAT.flatMap(lat=>LON.map(lon=>({lat,lon}))),res=[];
  const q=new URLSearchParams({latitude:coords.map(p=>p.lat).join(','),longitude:coords.map(p=>p.lon).join(','),hourly:fields.join(','),forecast_days:'3',timezone:'GMT',wind_speed_unit:'kmh'});const r=await x5QueuedFetch(API,{method:'POST',body:q,cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const a=await r.json();res.push(...(Array.isArray(a)?a:[a]));
  times=res[0]?.hourly?.time;if(!Array.isArray(times)||!times.length||res.length!==coords.length)throw Error('Neúplná odpověď GFS.');
  for(const r of res)for(const f of fields)if(!Array.isArray(r.hourly?.[f])||r.hourly[f].length!==times.length)throw Error('Chybí pole '+f);
  cells=coords.map((p,i)=>({lat:p.lat,lon:p.lon,temp:res[i].hourly.temperature_850hPa,speed:res[i].hourly.wind_speed_850hPa,direction:res[i].hourly.wind_direction_850hPa}));
  track=times.map((_,k)=>analyse(k));
  if(status)status.innerHTML='<b class="good">Diagnostika studeného vzduchu načtena.</b> 325 bodů · '+times.length+' hodinových kroků · GFS 850 hPa.';
  render();
 }catch(e){if(status)status.innerHTML='<b class="warn">Diagnostiku se nepodařilo načíst:</b> '+String(e.message||e);}
}
const sel=$('pv850mapTime'),tab=$('pv500Time'),refresh=$('pv850mapRefresh');
if(sel)sel.addEventListener('change',render);if(tab)tab.addEventListener('change',render);if(refresh)refresh.addEventListener('click',load);load();
})();