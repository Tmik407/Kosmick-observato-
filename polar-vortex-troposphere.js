(()=>{'use strict';
const $=id=>document.getElementById(id);
const points=[
 {name:'Severní Atlantik',lat:60,lon:-20},{name:'Arktida / sever Skandinávie',lat:70,lon:20},
 {name:'Západní Evropa',lat:50,lon:-10},{name:'Střední Evropa',lat:50,lon:15},{name:'Východní Evropa',lat:50,lon:35}
];
const fields=['geopotential_height_500hPa','temperature_500hPa','wind_speed_500hPa','wind_direction_500hPa','geopotential_height_850hPa','temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
let dataset=null;
const fmt=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
function render(forcedIndex){
 const sel=$('pv500Time');if(!dataset)return;
 const selected=forcedIndex===undefined?Number(sel?.value||0):Number(forcedIndex);
 const i=Math.max(0,Math.min(dataset.times.length-1,selected)),rows=dataset.locations.map(p=>({p,z:p.hourly.geopotential_height_500hPa[i],t:p.hourly.temperature_500hPa[i],w:p.hourly.wind_speed_500hPa[i],d:p.hourly.wind_direction_500hPa[i],z850:p.hourly.geopotential_height_850hPa[i],t850:p.hourly.temperature_850hPa[i],w850:p.hourly.wind_speed_850hPa[i],d850:p.hourly.wind_direction_850hPa[i]}));
 const body=$('pv500Body');if(body)body.innerHTML=rows.map(x=>'<tr><td>'+x.p.name+'</td><td>'+fmt(x.z,0)+' m</td><td>'+fmt(x.t,1)+' °C</td><td>'+fmt(x.w,1)+' km/h</td><td>'+fmt(x.d,0)+'°</td><td>'+fmt(x.z850,0)+' m</td><td>'+fmt(x.t850,1)+' °C</td><td>'+fmt(x.w850,1)+' km/h</td></tr>').join('');
 const central=rows.find(x=>x.p.name==='Střední Evropa'),north=rows.find(x=>x.p.name==='Arktida / sever Skandinávie'),west=rows.find(x=>x.p.name==='Západní Evropa'),east=rows.find(x=>x.p.name==='Východní Evropa'),atl=rows.find(x=>x.p.name==='Severní Atlantik');
 const delta=central&&west&&east?(central.z-(west.z+east.z)/2):null;
 const northDiff=central&&north?central.z-north.z:null;
 const signal=$('pv500Interpretation');
 if(signal){
  let text='Zatím není dost hodnot pro orientační porovnání.';
  if(Number.isFinite(delta)&&Number.isFinite(northDiff)){
   const trough=delta<=-60,low=central.z<5400;
   text=(trough?'Střední Evropa má nižší 500hPa geopotenciál než západní a východní srovnávací body – lokální žlab je možný. ':'Z dostupných bodů není patrný výrazný relativní geopotenciální žlab nad střední Evropou. ')+(low?'Geopotenciál ve střední Evropě je pod 5400 m. ':'Geopotenciál ve střední Evropě není pod orientační hranicí 5400 m. ')+'Rozdíl střední Evropa minus průměr západu a východu: '+fmt(delta,0)+' m. Rozdíl severní Skandinávie minus střední Evropa: '+fmt(northDiff,0)+' m.';
  }
  signal.textContent=text+' Jde pouze o řídké bodové srovnání, nikoli o mapovou analýzu nebo pravděpodobnost vpádu.';
 }
 const stamp=$('pv500Stamp');if(stamp)stamp.textContent='Platnost: '+dataset.times[i]+' UTC · model NCEP GFS přes Open-Meteo';
 draw();
}
function draw(){
 const c=$('pv500Chart');if(!c||!dataset)return;const g=c.getContext('2d'),w=c.width,h=c.height,p={l:72,r:25,t:30,b:48};g.clearRect(0,0,w,h);g.fillStyle='#fff';g.fillRect(0,0,w,h);
 const series=dataset.locations.map(x=>({name:x.name,vals:x.hourly.geopotential_height_500hPa})),nums=series.flatMap(x=>x.vals).filter(Number.isFinite);if(!nums.length)return;
 let lo=Math.floor((Math.min(...nums)-20)/20)*20,hi=Math.ceil((Math.max(...nums)+20)/20)*20;if(lo===hi)hi=lo+100;
 const x=i=>p.l+i*(w-p.l-p.r)/Math.max(1,dataset.times.length-1),y=v=>h-p.b-(v-lo)/(hi-lo)*(h-p.t-p.b),cols=['#087fa5','#6941a5','#a85b12','#16834b','#b42318'];
 g.font='12px Arial';g.textAlign='right';for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,yy=y(v);g.strokeStyle='#dce5ed';g.beginPath();g.moveTo(p.l,yy);g.lineTo(w-p.r,yy);g.stroke();g.fillStyle='#52677a';g.fillText(fmt(v,0)+' m',p.l-8,yy+4);}
 series.forEach((s,j)=>{g.strokeStyle=cols[j];g.lineWidth=2.5;g.beginPath();s.vals.forEach((v,i)=>{if(!Number.isFinite(v))return;i?g.lineTo(x(i),y(v)):g.moveTo(x(i),y(v));});g.stroke();});
 g.textAlign='center';g.fillStyle='#52677a';g.font='11px Arial';[0,Math.floor((dataset.times.length-1)/2),dataset.times.length-1].forEach(i=>g.fillText(dataset.times[i].replace('T',' '),x(i),h-15));
 g.textAlign='left';let lx=p.l;series.forEach((s,j)=>{g.fillStyle=cols[j];g.fillRect(lx,8,12,4);g.fillStyle='#263b4f';g.fillText(s.name,lx+17,16);lx+=Math.min(205,Math.max(125,s.name.length*7));});
}
async function load(){
 const status=$('pv500Status');if(status)status.textContent='Načítám společná data GFS pro evropské srovnávací body…';
 try{
  if(!window.X5GFS||typeof window.X5GFS.get!=='function')throw Error('Společný datový modul X5GFS není načten. Obnovte stránku bez staré mezipaměti.');
  const data=await window.X5GFS.get();
  const index=new Map(data.points.map((p,i)=>[p.lat+','+p.lon,i]));
  const locations=points.map(p=>{const i=index.get(p.lat+','+p.lon);if(i===undefined)throw Error('Chybí bod '+p.name+' ve společném poli GFS');return {...p,hourly:data.arr[i].hourly};});
  dataset={times:data.times,locations};
  const select=$('pv500Time');if(select){select.innerHTML='';dataset.times.forEach((t,i)=>{const o=document.createElement('option');o.value=i;o.textContent=t.replace('T',' ')+' UTC';select.appendChild(o);});select.value='0';}
  render();if(status)status.innerHTML='<b class="good">Data GFS na 500 hPa načtena.</b> 5 lokalit · '+data.times.length+' hodinových kroků · '+(data.stale?'uložená data':'společná data GFS').'.';
 }catch(e){if(status)status.innerHTML='<b class="warn">Data 500 hPa se nepodařilo načíst:</b> '+String(e.message||e);}
}
const s=$('pv500Time');if(s)s.addEventListener('change',()=>render());window.addEventListener('x5-map-time',e=>render(e.detail?.index));const b=$('pv500Refresh');if(b)b.addEventListener('click',load);load();
})();