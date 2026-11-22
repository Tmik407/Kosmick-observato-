(()=>{'use strict';
const $=id=>document.getElementById(id),LAT=Array.from({length:13},(_,i)=>30+i*5),LON=Array.from({length:25},(_,i)=>-60+i*5),API='https://api.open-meteo.com/v1/gfs';
const fields=['temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
let times=[],cells=[],track=[];
async function x5QueuedFetch(url,init){
 const run=async()=>{let last;for(let attempt=0;attempt<4;attempt++){try{const response=await fetch(url,init);if(response.status===429){last=new Error('HTTP 429 – veřejné API omezuje četnost požadavků');if(attempt<3){await new Promise(r=>setTimeout(r,[3000,7000,15000][attempt]));continue;}}return response;}catch(e){last=e;if(attempt<3)await new Promise(r=>setTimeout(r,[1500,4000,9000][attempt]));}}throw last||new Error('Požadavek se nezdařil.');};
 const previous=window.__x5OpenMeteoQueue||Promise.resolve();
 const task=previous.then(run,run);
 window.__x5OpenMeteoQueue=task.then(()=>new Promise(r=>setTimeout(r,8000)),()=>new Promise(r=>setTimeout(r,8000)));
 return task;
}
const fmt=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:NaN;
const coord=p=>fmt(p.lat,1)+'° s. š., '+fmt(Math.abs(p.lon),1)+'° '+(p.lon<0?'z. d.':'v. d.');
function analyse(k){
 const valid=cells.map(p=>({...p,t:p.temp[k],w:p.speed[k],dir:p.direction[k],areaWeight:Math.max(.0001,Math.cos(p.lat*Math.PI/180))})).filter(p=>Number.isFinite(p.t));
 const cold=valid.filter(p=>p.t< -10),weights=cold.map(p=>Math.max(0,-10-p.t)*p.areaWeight),sum=weights.reduce((a,b)=>a+b,0);
 const center=sum?{lat:cold.reduce((s,p,i)=>s+p.lat*weights[i],0)/sum,lon:cold.reduce((s,p,i)=>s+p.lon*weights[i],0)/sum}:null;
 const min=valid.reduce((a,p)=>p.t<a.t?p:a,valid[0]||{t:NaN,lat:NaN,lon:NaN});
 const windPts=cold.filter(p=>Number.isFinite(p.w)&&Number.isFinite(p.dir));
 const u=mean(windPts.map(p=>-p.w*Math.sin(p.dir*Math.PI/180))),v=mean(windPts.map(p=>-p.w*Math.cos(p.dir*Math.PI/180)));
 const weightedPct=threshold=>100*valid.filter(p=>p.t<threshold).reduce((s,p)=>s+p.areaWeight,0)/valid.reduce((s,p)=>s+p.areaWeight,0);
 const edge=cold.filter(p=>p.lat===LAT[0]||p.lat===LAT[LAT.length-1]||p.lon===LON[0]||p.lon===LON[LON.length-1]);
 return {min:min.t,max:Math.max(...valid.map(p=>p.t)),coldest:min,n:valid.length,a5:weightedPct(-5),a10:weightedPct(-10),a15:weightedPct(-15),center,wind:mean(windPts.map(p=>p.w)),windDir:(Math.atan2(u,v)*180/Math.PI+360)%360,valid,edgeCount:edge.length,edgeLat:edge.some(p=>p.lat===LAT[0]||p.lat===LAT[LAT.length-1]),edgeLon:edge.some(p=>p.lon===LON[0]||p.lon===LON[LON.length-1])};
}
function render(){
 if(!times.length)return;const idx=Math.max(0,Math.min(times.length-1,Number($('pv850mapTime')?.value||$('pv500Time')?.value||0))),d=analyse(idx);
 $('pvx5ColdMin').textContent=fmt(d.min)+' °C';$('pvx5ColdMax').textContent=fmt(d.max)+' °C';
 $('pvx5ColdArea5').textContent=fmt(d.a5,1)+' %';$('pvx5ColdArea10').textContent=fmt(d.a10,1)+' %';$('pvx5ColdArea15').textContent=fmt(d.a15,1)+' %';
 $('pvx5ColdStamp').textContent='Platnost '+times[idx]+' UTC · '+d.n+' platných bodů z '+LAT.length*LON.length+' · síť 30–90° s. š., 60° z. d. až 60° v. d.';
 const center=$('pvx5ColdCenter');if(center){
  const loc=d.center?'Plošně vážené teplotní těžiště pod −10 °C: '+coord(d.center)+'.':'V této platnosti není bod pod −10 °C.';
  const wdir=Number.isFinite(d.windDir)?' Průměrný vítr v chladných bodech: '+fmt(d.wind,1)+' km/h, směr '+fmt(d.windDir,0)+'° (kam proudí).':'';
  center.textContent=loc+wdir+' Nejchladnější bod: '+coord(d.coldest)+' ('+fmt(d.min,1)+' °C).';
 }
 const edge=$('pvx5ColdEdge');if(edge)edge.textContent=d.edgeCount?'Pozor: '+d.edgeCount+' studených bodů leží na okraji rozšířené sítě'+(d.edgeLat?' (severní/jižní okraj)':'')+(d.edgeLon?' (západní/východní okraj)':'')+'. Studená oblast může pokračovat mimo mapu.':'V této platnosti nebyla studená oblast pod −10 °C zjištěna na okraji rozšířené sítě.';
 drawMap(d);drawTrack(idx);
}
function drawMap(d){
 const c=$('pvx5ColdMap');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height;g.clearRect(0,0,w,h);g.fillStyle='#f4f8fc';g.fillRect(0,0,w,h);
 const x=lon=>48+(lon+60)/120*(w-78),y=lat=>22+(90-lat)/60*(h-52);
 g.strokeStyle='#d6e1eb';g.fillStyle='#536779';g.font='13px Arial';
 for(let lon=-60;lon<=60;lon+=20){g.beginPath();g.moveTo(x(lon),18);g.lineTo(x(lon),h-30);g.stroke();g.fillText(Math.abs(lon)+'°'+(lon<0?'Z':lon>0?'V':''),x(lon)-12,h-10);}
 for(let lat=30;lat<=90;lat+=10){g.beginPath();g.moveTo(48,y(lat));g.lineTo(w-30,y(lat));g.stroke();g.fillText(lat+'°N',5,y(lat)+4);}
 d.valid.forEach(p=>{const px=x(p.lon),py=y(p.lat),r=p.t< -15?7:p.t< -10?6:p.t< -5?5:3;g.beginPath();g.arc(px,py,r,0,Math.PI*2);g.fillStyle=p.t< -15?'#244f9b':p.t< -10?'#3488c5':p.t< -5?'#83bddb':'#e6a36d';g.fill();g.strokeStyle='#31495d';g.lineWidth=.7;g.stroke();
  if(Number.isFinite(p.w)&&Number.isFinite(p.dir)&&p.w>=10){const toward=(p.dir+180)*Math.PI/180,len=Math.min(17,5+p.w/12),ex=px+Math.sin(toward)*len,ey=py-Math.cos(toward)*len;g.strokeStyle='#263b4f';g.lineWidth=1.3;g.beginPath();g.moveTo(px,py);g.lineTo(ex,ey);g.stroke();g.beginPath();g.moveTo(ex,ey);g.lineTo(ex-4*Math.cos(toward-.5),ey-4*Math.sin(toward-.5));g.moveTo(ex,ey);g.lineTo(ex-4*Math.cos(toward+.5),ey-4*Math.sin(toward+.5));g.stroke();}
 });
 if(d.center){g.beginPath();g.arc(x(d.center.lon),y(d.center.lat),10,0,Math.PI*2);g.strokeStyle='#b42318';g.lineWidth=3;g.stroke();}
 if(d.edgeCount){g.strokeStyle='#b42318';g.lineWidth=2;g.strokeRect(49,23,w-80,h-54);}
 g.fillStyle='#20364a';g.font='bold 15px Arial';g.fillText('Studené body a směr proudění · 850 hPa',48,15);
}
function drawTrack(idx){
 const c=$('pvx5ColdTrack');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height,p={l:58,r:24,t:22,b:42};g.clearRect(0,0,w,h);g.fillStyle='#f4f8fc';g.fillRect(0,0,w,h);
 const valid=track.map((d,i)=>({...d,i})).filter(x=>x.center);if(!valid.length){g.fillStyle='#263b4f';g.fillText('V předpovědi není oblast pod −10 °C.',p.l,45);return;}
 const x=i=>p.l+i*(w-p.l-p.r)/Math.max(1,times.length-1),y=lat=>h-p.b-(lat-30)/60*(h-p.t-p.b);
 g.strokeStyle='#d8e3ed';g.fillStyle='#52677a';g.font='13px Arial';for(let lat=30;lat<=90;lat+=10){g.beginPath();g.moveTo(p.l,y(lat));g.lineTo(w-p.r,y(lat));g.stroke();g.fillText(lat+'°N',8,y(lat)+4);}
 g.strokeStyle='#087fa5';g.lineWidth=3;g.beginPath();valid.forEach((d,i)=>{const xx=x(d.i),yy=y(d.center.lat);i?g.lineTo(xx,yy):g.moveTo(xx,yy);});g.stroke();
 valid.forEach(d=>{g.fillStyle='#087fa5';g.beginPath();g.arc(x(d.i),y(d.center.lat),4,0,Math.PI*2);g.fill();});
 const current=valid.find(d=>d.i===idx);if(current){g.fillStyle='#b42318';g.beginPath();g.arc(x(idx),y(current.center.lat),7,0,Math.PI*2);g.fill();}
 g.fillStyle='#263b4f';g.fillText('Zeměpisná šířka těžiště studené oblasti (< −10 °C)',p.l,15);g.fillText('Čas →',w-75,h-12);
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