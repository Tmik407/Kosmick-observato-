(()=>{'use strict';
const $=id=>document.getElementById(id),FMT=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const levels=[10,30,50],API='https://api.open-meteo.com/v1/gfs';
const sites=[{name:'Severní Atlantik',lat:60,lon:-20},{name:'Severní Skandinávie',lat:70,lon:20},{name:'Západní Evropa',lat:50,lon:-10},{name:'Střední Evropa',lat:50,lon:15},{name:'Východní Evropa',lat:50,lon:35}];
async function getJSON(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}
async function run(){
 const status=$('pvx5VerticalStatus');if(status)status.textContent='Načítám společné GFS pole a stratosférický archiv…';
 try{
  const strat=await getJSON('./data/polar-vortex/latest.json?vertical='+Date.now());
  const data=await window.X5GFS.get();
  if(!Array.isArray(strat.rows)||!Array.isArray(strat.points)||!Array.isArray(strat.times))throw Error('Stratosférický archiv má neplatnou strukturu.');
  const index=new Map(data.points.map((p,i)=>[p.lat+','+p.lon,i]));
  const select=$('pv500Time');
  const requestedIndex=Math.max(0,Math.min(data.times.length-1,Number(select?.value||0)));
  const targetTime=data.times[requestedIndex];
  const targetMs=Date.parse(targetTime+'Z');
  const si=strat.times.reduce((best,t,i)=>Math.abs(Date.parse(t+'Z')-targetMs)<Math.abs(Date.parse(strat.times[best]+'Z')-targetMs)?i:best,0);
  const ti=requestedIndex,tbody=$('pvx5VerticalBody');
  const stratTime=strat.times[si];
  const exactMatch=stratTime===targetTime;
  const means=levels.map(level=>{
   const k='temperature_'+level+'hPa',w='wind_speed_'+level+'hPa',z='geopotential_height_'+level+'hPa';
   const valid=strat.rows.map(r=>({temp:r.hourly?.[k]?.[si],wind:r.hourly?.[w]?.[si],z:r.hourly?.[z]?.[si]})).filter(x=>Number.isFinite(x.temp)&&Number.isFinite(x.wind)&&Number.isFinite(x.z));
   return {level,temp:valid.length?valid.reduce((s,x)=>s+x.temp,0)/valid.length:null,wind:valid.length?valid.reduce((s,x)=>s+x.wind,0)/valid.length:null,z:valid.length?valid.reduce((s,x)=>s+x.z,0)/valid.length:null,n:valid.length};
  });
  const e=sites.map(p=>{const i=index.get(p.lat+','+p.lon),h=data.arr[i].hourly;return {name:p.name,z:h.geopotential_height_500hPa[ti],temp:h.temperature_500hPa[ti],wind:h.wind_speed_500hPa[ti]};});
  const central=e[3],west=e[2],east=e[4],delta=central.z-(west.z+east.z)/2,tempDelta=central.temp-(west.temp+east.temp)/2;
  const rows=means.map(x=>'<tr><td><b>'+x.level+' hPa</b></td><td>'+FMT(x.temp,1)+' °C / '+FMT(x.z,0)+' m</td><td>'+FMT(x.wind,1)+' m/s</td><td>NOAA GFS · globální průměr vzorku '+x.n+'/'+strat.points.length+' bodů</td></tr>');
  rows.push('<tr><td><b>500 hPa · střední Evropa</b></td><td>'+FMT(central.temp,1)+' °C / '+FMT(central.z,0)+' m</td><td>'+FMT(central.wind,1)+' km/h</td><td>NCEP GFS · bodové evropské srovnání</td></tr>');
  if(tbody)tbody.innerHTML=rows.join('');
  const sig=$('pvx5OutbreakSignal');
  if(sig){const trough=delta<=-60,colder=tempDelta<=-2;let level='Bez výrazného lokálního signálu v tomto bodovém srovnání.';if(trough&&colder)level='Zesílený screeningový signál: střední Evropa má nižší geopotenciál i chladnější teplotu než průměr západního a východního bodu.';else if(trough||colder)level='Částečný screeningový signál: splněna je pouze jedna ze dvou podmínek (geopotenciál / teplota).';sig.innerHTML='<b>'+level+'</b><br>Odchylka geopotenciálu střední Evropy od průměru západu a východu: '+FMT(delta,0)+' m. Teplotní rozdíl: '+FMT(tempDelta,1)+' °C. Platnost 500 hPa: '+data.times[ti]+' UTC. <br><b>Výsledek není pravděpodobnost vpádu.</b>';}
  const stamp=$('pvx5VerticalStamp');if(stamp)stamp.textContent='Stratosféra: '+stratTime+' UTC · cyklus '+(strat.cycle_utc||'neuveden')+' | Troposféra: '+data.times[ti]+' UTC'+(exactMatch?' · shodná platnost':' · nejbližší dostupný stratosférický krok; čas se liší');
  if(status)status.innerHTML='<b class="good">Vertikální přehled sestaven.</b> Tři stratosférické hladiny a jedna troposférická hladina; '+(exactMatch?'časová platnost je sjednocena.':'nejbližší dostupné časy jsou výslovně rozlišeny.')+(data.stale?' Troposférická data jsou z uložené kopie.':' Troposférická data pocházejí ze společného evropského archivu NOAA GFS.');
 }catch(err){if(status)status.innerHTML='<b class="warn">Vertikální diagnostiku nelze dokončit:</b> '+String(err.message||err);}
}
const timeSelect=$('pv500Time');if(timeSelect)timeSelect.addEventListener('change',run);
run();
})();