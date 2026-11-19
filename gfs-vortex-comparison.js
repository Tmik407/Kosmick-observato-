(()=>{'use strict';
const $=id=>document.getElementById(id),url='./data/polar-vortex/latest.json',levels=[10,30,50];
let data=null;
const colors={10:'#087fa5',30:'#a85b12',50:'#6941a5'};
const fmt=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const dateFmt=s=>{const d=new Date(/[Zz]$|[+-]\\d{2}:?\\d{2}$/.test(s)?s:s+'Z');return Number.isFinite(d.getTime())?d.toLocaleString('cs-CZ',{timeZone:'UTC',dateStyle:'short',timeStyle:'short'})+' UTC':'—';};
const val=(row,key,i)=>row?.hourly?.[key]?.[i];
function weightedMean(values,points){let s=0,w=0;values.forEach((v,i)=>{if(Number.isFinite(v)){const q=Math.cos(points[i].lat*Math.PI/180);s+=v*q;w+=q;}});return w?s/w:null;}
function drawTemperatureTrend(){
 const c=$('vortexTrendCanvas'),g=c?.getContext('2d');if(!c||!g||!data)return;
 const w=c.width,h=c.height,p={l:70,r:25,t:38,b:42};
 g.clearRect(0,0,w,h);g.fillStyle='#fff';g.fillRect(0,0,w,h);
 const series=levels.map(level=>({level,values:data.times.map((_,i)=>weightedMean(data.rows.map(r=>val(r,'temperature_'+level+'hPa',i)),data.points))}));
 const nums=series.flatMap(x=>x.values).filter(Number.isFinite);
 if(!nums.length){g.fillStyle='#52677a';g.fillText('Teplotní řada není dostupná.',p.l,80);return;}
 let lo=Math.floor(Math.min(...nums)-2),hi=Math.ceil(Math.max(...nums)+2);if(lo===hi){lo-=1;hi+=1;}
 const x=i=>p.l+i*(w-p.l-p.r)/Math.max(1,data.times.length-1),y=v=>h-p.b-(v-lo)/(hi-lo)*(h-p.t-p.b);
 g.font='12px Arial';g.textAlign='right';
 for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,yy=y(v);g.strokeStyle='#dce5ed';g.beginPath();g.moveTo(p.l,yy);g.lineTo(w-p.r,yy);g.stroke();g.fillStyle='#52677a';g.fillText(fmt(v,0)+' °C',p.l-8,yy+4);}
 series.forEach(a=>{g.strokeStyle=colors[a.level];g.lineWidth=3;g.beginPath();let started=false;a.values.forEach((v,i)=>{if(!Number.isFinite(v)){started=false;return;}if(!started){g.moveTo(x(i),y(v));started=true;}else g.lineTo(x(i),y(v));});g.stroke();});
 const selected=Number($('vortexCompareTimeSelect')?.value||0);g.strokeStyle='#263b4f';g.setLineDash([5,4]);g.beginPath();g.moveTo(x(selected),p.t);g.lineTo(x(selected),h-p.b);g.stroke();g.setLineDash([]);
 g.textAlign='center';g.fillStyle='#52677a';g.font='11px Arial';[0,Math.floor((data.times.length-1)/2),data.times.length-1].forEach(i=>g.fillText(dateFmt(data.times[i]).replace(' UTC',''),x(i),h-14));
 g.textAlign='left';let lx=p.l;levels.forEach(l=>{g.fillStyle=colors[l];g.fillRect(lx,12,14,4);g.fillStyle='#263b4f';g.fillText(l+' hPa',lx+20,18);lx+=105;});
}
function updateTemperatureComparison(index){
 const output=levels.map(level=>{
  const temps=data.rows.map(r=>val(r,'temperature_'+level+'hPa',index));
  const winds=data.rows.map(r=>val(r,'wind_speed_'+level+'hPa',index));
  let min=Infinity,at=-1;temps.forEach((v,i)=>{if(Number.isFinite(v)&&v<min){min=v;at=i;}});
  const p=at>=0?data.points[at]:null;
  return {level,mean:weightedMean(temps,data.points),min:min===Infinity?null:min,point:p,wind:weightedMean(winds,data.points)};
 });
 const body=$('vortexCompareBody');
 if(body)body.innerHTML=output.map(x=>'<tr><td><b>'+x.level+' hPa</b></td><td>'+fmt(x.mean,2)+' °C</td><td>'+fmt(x.min,2)+' °C</td><td>'+(x.point?fmt(x.point.lat,0)+'° N, '+fmt((x.point.lon+360)%360,1)+'° E':'—')+'</td><td>'+fmt(x.wind,1)+' m/s</td></tr>').join('');
 const stamp=$('vortexCompareTime');if(stamp)stamp.textContent=dateFmt(data.times[index]);
 const status=$('vortexCompareStatus');if(status)status.innerHTML='<b class="good">Číselné porovnání načteno.</b> '+data.rows.length+' bodů, '+data.times.length+' časových kroků. Teplotní průměr je vážen kosinem zeměpisné šířky.';
 drawTemperatureTrend();
}
function analyzeCenter(level,index){
 const key='geopotential_height_'+level+'hPa',rows=data.rows,points=data.points;
 const ringMeans=new Map();
 points.forEach((p,i)=>{const v=val(rows[i],key,index);if(!Number.isFinite(v))return;const a=ringMeans.get(p.lat)||[];a.push(v);ringMeans.set(p.lat,a);});
 for(const [lat,a] of ringMeans)ringMeans.set(lat,a.reduce((s,v)=>s+v,0)/a.length);
 let sx=0,sy=0,sz=0,total=0,min=Infinity,minPoint=null,anoms=[];
 points.forEach((p,i)=>{
  const z=val(rows[i],key,index),mean=ringMeans.get(p.lat);if(!Number.isFinite(z)||!Number.isFinite(mean))return;
  const anomaly=z-mean;anoms.push({anomaly,lat:p.lat,lon:p.lon});
  if(z<min){min=z;minPoint=p;}
  const w=Math.max(0,-anomaly)*Math.cos(p.lat*Math.PI/180);
  if(w<=0)return;
  const lat=p.lat*Math.PI/180,lon=p.lon*Math.PI/180;
  sx+=w*Math.cos(lat)*Math.cos(lon);sy+=w*Math.cos(lat)*Math.sin(lon);sz+=w*Math.sin(lat);total+=w;
 });
 let lat,lon,method;
 if(total>0){lat=Math.atan2(sz,Math.hypot(sx,sy))*180/Math.PI;lon=Math.atan2(sy,sx)*180/Math.PI;method='těžiště záporné geopotenciální anomálie';}
 else if(minPoint){lat=minPoint.lat;lon=minPoint.lon;method='nejnižší vzorkovaný geopotenciál – náhradní odhad';}
 else return null;
 const meanA=anoms.length?anoms.reduce((s,a)=>s+a.anomaly,0)/anoms.length:0;
 const std=Math.sqrt(anoms.reduce((s,a)=>s+(a.anomaly-meanA)**2,0)/Math.max(1,anoms.length));
 return {level,lat,lon:(lon+360)%360,displacement:(90-lat)*111.2,minHeight:min,minPoint,asymmetry:std,method,anoms};
}
function drawPolar(index,centers){
 const c=$('vortexGeoCanvas');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height;
 g.clearRect(0,0,w,h);g.fillStyle='#fff';g.fillRect(0,0,w,h);
 const panelW=w/3;
 levels.forEach((level,k)=>{
  const cx=panelW*k+panelW/2,cy=220,R=150,center=centers[k],key='geopotential_height_'+level+'hPa';
  g.fillStyle='#f7fbff';g.beginPath();g.arc(cx,cy,R,0,Math.PI*2);g.fill();g.strokeStyle='#9eb5c8';g.lineWidth=1.5;g.stroke();
  [60,70,80].forEach(lat=>{const r=R*Math.cos(lat*Math.PI/180)/Math.cos(60*Math.PI/180);g.beginPath();g.arc(cx,cy,r,0,Math.PI*2);g.strokeStyle='#d8e3ec';g.stroke();g.fillStyle='#64798b';g.font='10px Arial';g.fillText(lat+'°',cx+3,cy-r+12);});
  for(let lon=0;lon<360;lon+=45){const a=lon*Math.PI/180;g.beginPath();g.moveTo(cx,cy);g.lineTo(cx+R*Math.sin(a),cy-R*Math.cos(a));g.strokeStyle='#e2eaf1';g.stroke();}
  const vals=data.rows.map((r,i)=>val(r,key,index)).filter(Number.isFinite),lo=Math.min(...vals),hi=Math.max(...vals);
  data.points.forEach((p,i)=>{
   const z=val(data.rows[i],key,index);if(!Number.isFinite(z))return;
   const a=p.lon*Math.PI/180,rr=R*Math.cos(p.lat*Math.PI/180)/Math.cos(60*Math.PI/180);
   const x=cx+rr*Math.sin(a),y=cy-rr*Math.cos(a),t=hi===lo?.5:(z-lo)/(hi-lo);
   const hue=220-220*t;g.beginPath();g.arc(x,y,6,0,Math.PI*2);g.fillStyle='hsl('+hue+',78%,48%)';g.fill();g.strokeStyle='#fff';g.lineWidth=1;g.stroke();
  });
  if(center){
   const a=center.lon*Math.PI/180,rr=R*Math.cos(center.lat*Math.PI/180)/Math.cos(60*Math.PI/180),x=cx+rr*Math.sin(a),y=cy-rr*Math.cos(a);
   g.strokeStyle='#111827';g.lineWidth=3;g.beginPath();g.arc(x,y,12,0,Math.PI*2);g.stroke();
   g.beginPath();g.moveTo(x-17,y);g.lineTo(x+17,y);g.moveTo(x,y-17);g.lineTo(x,y+17);g.stroke();
  }
  g.fillStyle='#20364a';g.font='bold 16px Arial';g.textAlign='center';g.fillText(level+' hPa',cx,25);
  g.font='11px Arial';g.fillStyle='#52677a';g.fillText('Severní polární stereografická projekce',cx,42);
 });
 g.textAlign='left';g.font='11px Arial';g.fillStyle='#52677a';g.fillText('Barva bodu: relativní geopotenciální výška v rámci hladiny · kroužek: odhad anomálního centra',12,h-12);
}
function drawDisplacement(){
 const c=$('vortexGeoTrend'),g=c?.getContext('2d');if(!c||!g)return;
 const w=c.width,h=c.height,p={l:65,r:22,t:28,b:42};g.clearRect(0,0,w,h);g.fillStyle='#fff';g.fillRect(0,0,w,h);
 const all=levels.map(l=>({level:l,values:data.times.map((_,i)=>analyzeCenter(l,i)?.displacement)}));
 const nums=all.flatMap(s=>s.values).filter(Number.isFinite);if(!nums.length)return;
 const lo=0,hi=Math.max(100,Math.ceil(Math.max(...nums)/100)*100),x=i=>p.l+i*(w-p.l-p.r)/Math.max(1,data.times.length-1),y=v=>h-p.b-(v-lo)/(hi-lo)*(h-p.t-p.b);
 g.font='12px Arial';g.textAlign='right';
 for(let k=0;k<=4;k++){const v=hi*k/4,yy=y(v);g.strokeStyle='#dce5ed';g.beginPath();g.moveTo(p.l,yy);g.lineTo(w-p.r,yy);g.stroke();g.fillStyle='#52677a';g.fillText(fmt(v,0)+' km',p.l-8,yy+4);}
 all.forEach(s=>{g.strokeStyle=colors[s.level];g.lineWidth=2.8;g.beginPath();let started=false;s.values.forEach((v,i)=>{if(!Number.isFinite(v)){started=false;return;}if(!started){g.moveTo(x(i),y(v));started=true;}else g.lineTo(x(i),y(v));});g.stroke();});
 g.textAlign='center';g.fillStyle='#52677a';g.font='11px Arial';[0,Math.floor((data.times.length-1)/2),data.times.length-1].forEach(i=>g.fillText(dateFmt(data.times[i]).replace(' UTC',''),x(i),h-13));
 g.textAlign='left';let lx=p.l;levels.forEach(l=>{g.fillStyle=colors[l];g.fillRect(lx,9,14,4);g.fillStyle='#263b4f';g.fillText(l+' hPa',lx+20,15);lx+=100;});
}
function update(index){
 const centers=levels.map(l=>analyzeCenter(l,index));
 const body=$('vortexGeoBody');
 if(body)body.innerHTML=centers.map(c=>c?'<tr><td><b>'+c.level+' hPa</b></td><td>'+fmt(c.lat,2)+'° N</td><td>'+fmt(c.lon,2)+'° E</td><td>'+fmt(c.displacement,0)+' km</td><td>'+fmt(c.minHeight,0)+' m²/s²</td><td>'+fmt(c.asymmetry,0)+' m²/s²</td></tr>':'<tr><td colspan="6">Data nejsou dostupná</td></tr>').join('');
 const methods=$('vortexGeoMethod');if(methods)methods.textContent=centers.map(c=>c?c.level+' hPa: '+c.method:'').filter(Boolean).join(' · ');
 const stamp=$('vortexGeoTime');if(stamp)stamp.textContent=dateFmt(data.times[index])+' · běh '+dateFmt(data.cycle_utc);
 updateTemperatureComparison(index);\n drawPolar(index,centers);drawDisplacement();
}
async function load(){
 const status=$('vortexGeoStatus');if(status)status.textContent='Načítám geopotenciální pole NOAA GFS…';const compareStatus=$('vortexCompareStatus');if(compareStatus)compareStatus.textContent='Načítám číselná data NOAA GFS…';
 try{
  const r=await fetch(url+'?geo='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);
  const d=await r.json();if(!Array.isArray(d.points)||!Array.isArray(d.rows)||!Array.isArray(d.times)||!d.times.length)throw Error('Neplatná struktura archivu.');
  const required=levels.map(l=>'geopotential_height_'+l+'hPa');
  const valid=d.rows.every(row=>required.every(k=>Array.isArray(row.hourly?.[k])&&row.hourly[k].length===d.times.length));
  if(!valid)throw Error('Chybí geopotenciální výška na jedné nebo více hladinách.');
  data=d;
  const select=$('vortexCompareTimeSelect');if(select&&select.options.length!==d.times.length){select.innerHTML='';d.times.forEach((t,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=dateFmt(t);select.appendChild(o);});}
  const index=Math.min(Number(select?.value||0),d.times.length-1);update(index);
  if(status)status.innerHTML='<b class="good">Geopotenciální diagnostika načtena.</b> '+d.rows.length+' bodů · '+d.times.length+' časových kroků · 3 hladiny.';
 }catch(e){if(status)status.innerHTML='<b class="warn">Geopotenciální diagnostika se nepodařila načíst:</b> '+String(e.message||e);const cs=$('vortexCompareStatus');if(cs)cs.innerHTML='<b class="warn">Číselné porovnání se nepodařilo načíst:</b> '+String(e.message||e);}
}
const select=$('vortexCompareTimeSelect');if(select)select.addEventListener('change',()=>{if(data)update(Number(select.value));});
const refresh=$('vortexGeoRefresh');if(refresh)refresh.addEventListener('click',load);const compareRefresh=$('vortexCompareRefresh');if(compareRefresh)compareRefresh.addEventListener('click',load);
load();
})();