(()=>{'use strict';
const $=id=>document.getElementById(id);
const url='./data/polar-vortex/latest.json';
const levels=[10,30,50];
let dataset=null;
const fmt=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const dateFmt=s=>{const d=new Date(s);return Number.isFinite(d.getTime())?d.toLocaleString('cs-CZ',{timeZone:'UTC',dateStyle:'short',timeStyle:'short'})+' UTC':'—';};
function weightedMean(values,points){
 let sum=0,weight=0;
 values.forEach((v,i)=>{if(!Number.isFinite(v))return;const w=Math.cos(points[i].lat*Math.PI/180);sum+=v*w;weight+=w;});
 return weight?sum/weight:null;
}
function analyze(index){
 const points=dataset.points||[],rows=dataset.rows||[],time=dataset.times[index];
 const output=levels.map(level=>{
  const key='temperature_'+level+'hPa',windKey='wind_speed_'+level+'hPa';
  const temps=rows.map(r=>r.hourly?.[key]?.[index]);
  const winds=rows.map(r=>r.hourly?.[windKey]?.[index]);
  let min=Infinity,minIndex=-1;
  temps.forEach((v,i)=>{if(Number.isFinite(v)&&v<min){min=v;minIndex=i;}});
  return {level,mean:weightedMean(temps,points),min:min===Infinity?null:min,minPoint:minIndex>=0?points[minIndex]:null,wind:weightedMean(winds,points)};
 });
 const body=$('vortexCompareBody');
 if(body)body.innerHTML=output.map(x=>'<tr><td><b>'+x.level+' hPa</b></td><td>'+fmt(x.mean,2)+' °C</td><td>'+fmt(x.min,2)+' °C</td><td>'+(x.minPoint?fmt(x.minPoint.lat,0)+'° N, '+fmt(((x.minPoint.lon+360)%360),1)+'° E':'—')+'</td><td>'+fmt(x.wind,1)+' m/s</td></tr>').join('');
 const stamp=$('vortexCompareTime');if(stamp)stamp.textContent=dateFmt(time);
 const note=$('vortexCompareNote');if(note)note.textContent='Výpočet z '+rows.length+' vzorkovacích bodů · '+(dataset.source||'zdroj neuveden')+' · běh '+dateFmt(dataset.cycle_utc)+'. Nejchladnější bod je pouze nejchladnější ze vzorkovaných bodů, nikoli přesný střed víru.';
}
function draw(){
 const c=$('vortexTrendCanvas');if(!c||!dataset)return;
 const g=c.getContext('2d'),w=c.width,h=c.height,p={l:70,r:25,t:38,b:42};
 g.clearRect(0,0,w,h);g.fillStyle='#fff';g.fillRect(0,0,w,h);
 const colors={10:'#087fa5',30:'#a85b12',50:'#6941a5'};
 const series=levels.map(level=>({level,values:dataset.times.map((_,i)=>weightedMean((dataset.rows||[]).map(r=>r.hourly?.['temperature_'+level+'hPa']?.[i]),dataset.points||[]))}));
 const vals=series.flatMap(s=>s.values).filter(Number.isFinite);
 if(!vals.length){g.fillStyle='#52677a';g.fillText('Časová řada není dostupná.',p.l,80);return;}
 let lo=Math.floor(Math.min(...vals)-2),hi=Math.ceil(Math.max(...vals)+2);if(lo===hi){lo-=1;hi+=1;}
 const x=i=>p.l+i*(w-p.l-p.r)/Math.max(1,dataset.times.length-1),y=v=>h-p.b-(v-lo)/(hi-lo)*(h-p.t-p.b);
 g.font='12px Arial';g.textAlign='right';
 for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,yy=y(v);g.strokeStyle='#dce5ed';g.beginPath();g.moveTo(p.l,yy);g.lineTo(w-p.r,yy);g.stroke();g.fillStyle='#52677a';g.fillText(fmt(v,0)+' °C',p.l-8,yy+4);}
 series.forEach(s=>{g.strokeStyle=colors[s.level];g.lineWidth=3;g.beginPath();let started=false;s.values.forEach((v,i)=>{if(!Number.isFinite(v)){started=false;return;}if(!started){g.moveTo(x(i),y(v));started=true;}else g.lineTo(x(i),y(v));});g.stroke();});
 const selected=Number($('vortexCompareTimeSelect')?.value||0);if(Number.isFinite(selected)){g.strokeStyle='#263b4f';g.setLineDash([5,4]);g.beginPath();g.moveTo(x(selected),p.t);g.lineTo(x(selected),h-p.b);g.stroke();g.setLineDash([]);}
 g.textAlign='center';g.fillStyle='#52677a';g.font='11px Arial';
 [0,Math.floor((dataset.times.length-1)/2),dataset.times.length-1].forEach(i=>g.fillText(dateFmt(dataset.times[i]).replace(' UTC',''),x(i),h-14));
 g.textAlign='left';let lx=p.l;levels.forEach(level=>{g.fillStyle=colors[level];g.fillRect(lx,12,14,4);g.fillStyle='#263b4f';g.fillText(level+' hPa',lx+20,18);lx+=105;});
}
async function load(){
 const status=$('vortexCompareStatus');if(status)status.textContent='Načítám číselná data NOAA GFS…';
 try{
  const r=await fetch(url+'?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);
  const d=await r.json();
  if(!Array.isArray(d.points)||!Array.isArray(d.rows)||!Array.isArray(d.times)||!d.times.length)throw Error('Datový archiv nemá očekávanou strukturu.');
  const required=levels.flatMap(l=>['temperature_'+l+'hPa','wind_speed_'+l+'hPa']);
  const valid=d.rows.filter(row=>required.every(k=>Array.isArray(row.hourly?.[k])&&row.hourly[k].length===d.times.length));
  if(valid.length!==d.rows.length||!valid.length)throw Error('Některé datové řady chybí nebo mají odlišnou délku.');
  dataset=d;
  const select=$('vortexCompareTimeSelect');if(select){select.innerHTML='';d.times.forEach((t,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=dateFmt(t);select.appendChild(o);});select.value='0';}
  analyze(0);draw();
  if(status)status.innerHTML='<b class="good">Číselné porovnání načteno.</b> '+valid.length+' bodů, '+d.times.length+' časových kroků. Teplotní průměr je vážen kosinem zeměpisné šířky.';
 }catch(e){if(status)status.innerHTML='<b class="warn">Porovnání se nepodařilo načíst:</b> '+String(e.message||e);}
}
const select=$('vortexCompareTimeSelect');if(select)select.addEventListener('change',()=>{if(dataset){analyze(Number(select.value));draw();}});
const refresh=$('vortexCompareRefresh');if(refresh)refresh.addEventListener('click',load);
load();
})();