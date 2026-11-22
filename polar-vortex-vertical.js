(()=>{'use strict';
const $=id=>document.getElementById(id),FMT=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const levels=[10,30,50],API='https://api.open-meteo.com/v1/gfs';
const sites=[{name:'Severní Atlantik',lat:60,lon:-20},{name:'Severní Skandinávie',lat:70,lon:20},{name:'Západní Evropa',lat:50,lon:-10},{name:'Střední Evropa',lat:50,lon:15},{name:'Východní Evropa',lat:50,lon:35}];
async function x5VerticalFetch(url,init={}){
 const body=init.body?String(init.body):'',key='x5-gfs:'+url+':'+body;
 let cached=null;try{cached=JSON.parse(localStorage.getItem(key)||'null');}catch(_){}
 const save=async response=>{try{if(response.ok)localStorage.setItem(key,JSON.stringify({at:Date.now(),data:await response.clone().text()}));}catch(_){}};
 const run=async()=>{let last;for(let n=0;n<2;n++){try{const r=await fetch(url,init);if(r.status===429&&n===0){last=new Error('HTTP 429 – GFS dočasně omezuje požadavky');await new Promise(resolve=>setTimeout(resolve,12000));continue;}if(r.ok)await save(r);return r;}catch(e){last=e;if(n===0)await new Promise(resolve=>setTimeout(resolve,2500));}}throw last||new Error('Požadavek GFS selhal.');};
 const prev=window.__x5OpenMeteoQueue||Promise.resolve(),task=prev.then(run,run);
 window.__x5OpenMeteoQueue=task.then(()=>new Promise(resolve=>setTimeout(resolve,10000)),()=>new Promise(resolve=>setTimeout(resolve,10000)));
 if(cached?.data){task.catch(()=>{});return new Response(cached.data,{status:200,headers:{'Content-Type':'application/json','X-X5-Cache':'stale-ok'}});}
 return task;
}
async function getJSON(url){
 let r;
 if(url.startsWith(API)){const u=new URL(url);r=await x5VerticalFetch(API,{method:'POST',body:u.searchParams,cache:'no-store'});}
 else r=await fetch(url,{cache:'no-store'});
 if(!r.ok)throw Error('HTTP '+r.status);return r.json();
 }
async function run(){
 const status=$('pvx5VerticalStatus');if(status)status.textContent='Načítám stratosférický archiv a společná GFS data…';
 try{
  const [strat,data]=await Promise.all([getJSON('./data/polar-vortex/latest.json?vertical='+Date.now()),window.X5GFS.get()]);
  if(!Array.isArray(strat.rows)||!Array.isArray(strat.points)||!Array.isArray(strat.times))throw Error('Stratosférický archiv má neplatnou strukturu.');
  const offset=data.gridRows*data.gridCols,arr=sites.map((_,i)=>data.arr[offset+i]),t=data.times;
  const ti=0,si=strat.times.length-1,tbody=$('pvx5VerticalBody');
  const means=levels.map(level=>{
   const k='temperature_'+level+'hPa',w='wind_speed_'+level+'hPa',z='geopotential_height_'+level+'hPa';
   const valid=strat.rows.map(r=>({temp:r.hourly?.[k]?.[si],wind:r.hourly?.[w]?.[si],z:r.hourly?.[z]?.[si]})).filter(x=>Number.isFinite(x.temp)&&Number.isFinite(x.wind)&&Number.isFinite(x.z));
   return {level,temp:valid.length?valid.reduce((s,x)=>s+x.temp,0)/valid.length:null,wind:valid.length?valid.reduce((s,x)=>s+x.wind,0)/valid.length:null,z:valid.length?valid.reduce((s,x)=>s+x.z,0)/valid.length:null,n:valid.length};
  });
  const e=arr.map((x,i)=>({name:sites[i].name,z:x.hourly.geopotential_height_500hPa[ti],temp:x.hourly.temperature_500hPa[ti],wind:x.hourly.wind_speed_500hPa[ti]}));
  const central=e[3],west=e[2],east=e[4],delta=central.z-(west.z+east.z)/2,tempDelta=central.temp-(west.temp+east.temp)/2;
  const rows=means.map(x=>'<tr><td><b>'+x.level+' hPa</b></td><td>'+FMT(x.temp,1)+' °C / '+FMT(x.z,0)+' m</td><td>'+FMT(x.wind,1)+' m/s</td><td>NOAA GFS · globální průměr vzorku '+x.n+'/'+strat.points.length+' bodů</td></tr>');
  rows.push('<tr><td><b>500 hPa · střední Evropa</b></td><td>'+FMT(central.temp,1)+' °C / '+FMT(central.z,0)+' m</td><td>'+FMT(central.wind,1)+' km/h</td><td>NCEP GFS · bodové evropské srovnání</td></tr>');
  if(tbody)tbody.innerHTML=rows.join('');
  const sig=$('pvx5OutbreakSignal');
  if(sig){
   const trough=delta<=-60,colder=tempDelta<=-2;let level='Bez výrazného lokálního signálu v tomto bodovém srovnání.';
   if(trough&&colder)level='Zesílený screeningový signál: střední Evropa má nižší geopotenciál i chladnější teplotu než průměr západního a východního bodu.';
   else if(trough||colder)level='Částečný screeningový signál: splněna je pouze jedna ze dvou podmínek (geopotenciál / teplota).';
   sig.innerHTML='<b>'+level+'</b><br>Odchylka geopotenciálu střední Evropy od průměru západu a východu: '+FMT(delta,0)+' m. Teplotní rozdíl: '+FMT(tempDelta,1)+' °C. Platnost 500 hPa: '+t[ti]+' UTC. <br><b>Výsledek není pravděpodobnost vpádu.</b>';
  }
  const stamp=$('pvx5VerticalStamp');if(stamp)stamp.textContent='Stratosféra: '+strat.times[si]+' UTC · cyklus '+(strat.cycle_utc||'neuveden')+' | Troposféra: '+t[ti]+' UTC';
  if(status)status.innerHTML='<b class="good">Vertikální přehled sestaven.</b> Tři stratosférické hladiny a jedna troposférická hladina; GFS sdíleno jedním požadavkem.'+(data.stale?' Použita uložená data.':'');
 }catch(err){if(status)status.innerHTML='<b class="warn">Vertikální diagnostiku nelze dokončit:</b> '+String(err.message||err);}
}
run();
})();