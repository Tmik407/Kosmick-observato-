(()=>{'use strict';
const $=id=>document.getElementById(id),LAT=Array.from({length:7},(_,i)=>30+i*10),LON=Array.from({length:13},(_,i)=>-60+i*10),API='https://api.open-meteo.com/v1/gfs';
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
 window.__x5OpenMeteoQueue=task.then(()=>new Promise(r=>setTimeout(r,10000)),()=>new Promise(r=>setTimeout(r,10000)));
 if(cached&&cached.data){
  // Zobraz poslední úspěšná data ihned; aktualizace proběhne na pozadí.
  task.catch(()=>{});
  return new Response(cached.data,{status:200,headers:{'Content-Type':'application/json','X-X5-Cache':'stale-ok'}});
 }
 return task;
}
async function load(){
 const status=$('pvx5ColdStatus');if(status)status.textContent='Načítám společné evropské pole GFS pro detekci studeného vzduchu…';
 try{
  const data=await window.X5GFS.get();times=data.times;
  const coords=LAT.flatMap(lat=>LON.map(lon=>({lat,lon})));
  cells=coords.map(p=>{const i=data.points.findIndex(q=>q.lat===p.lat&&q.lon===p.lon),h=data.arr[i].hourly;return {lat:p.lat,lon:p.lon,temp:h.temperature_850hPa,speed:h.wind_speed_850hPa,direction:h.wind_direction_850hPa};});
  track=times.map((_,k)=>analyse(k));
  if(status)status.innerHTML='<b class="good">Diagnostika studeného vzduchu načtena.</b> '+cells.length+' bodů · '+times.length+' hodinových kroků · '+(data.stale?'uložená data':'aktuální GFS');
  render();
 }catch(e){if(status)status.innerHTML='<b class="warn">Diagnostiku se nepodařilo načíst:</b> '+String(e.message||e);}
}
const sel=$('pv850mapTime'),tab=$('pv500Time'),refresh=$('pv850mapRefresh');
if(sel)sel.addEventListener('change',render);if(tab)tab.addEventListener('change',render);if(refresh)refresh.addEventListener('click',load);load();
})();