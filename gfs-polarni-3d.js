(()=>{'use strict';
const $=id=>document.getElementById(id),levels=[10,30,50],lats=[60,68,76,84,88],lons=[-157.5,-112.5,-67.5,-22.5,22.5,67.5,112.5,157.5];
const points=[];for(const lat of lats)for(const lon of lons)points.push({lat,lon});
const keys=l=>['temperature_'+l+'hPa','geopotential_height_'+l+'hPa','wind_speed_'+l+'hPa','wind_direction_'+l+'hPa'];
let data={},times=[],idx=0,yaw=-.35,pitch=.22,timer=null,busy=false,drag=null;
const status=t=>{if($('p3dStatus'))$('p3dStatus').textContent=t;};
const project=(lat,lon,z,cx,cy,scale)=>{
 const r=(90-lat)/30*scale,a=(lon+yaw*180/Math.PI-90)*Math.PI/180;
 const x=r*Math.cos(a),y=r*Math.sin(a);
 const yp=y*Math.cos(pitch)-z*Math.sin(pitch),zp=y*Math.sin(pitch)+z*Math.cos(pitch);
 const xx=x*Math.cos(yaw*.15)-yp*Math.sin(yaw*.15),yy=x*Math.sin(yaw*.15)+yp*Math.cos(yaw*.15);
 const perspective=1200/(1200-zp);
 return {x:cx+xx*perspective,y:cy-yy*perspective-zp*.66,depth:zp};
};
const palette=t=>{const stops=[[0,[28,77,210]],[.25,[0,183,220]],[.5,[44,190,132]],[.75,[247,199,49]],[1,[225,61,54]]];for(let i=1;i<stops.length;i++)if(t<=stops[i][0]){const a=stops[i-1],b=stops[i],q=(t-a[0])/(b[0]-a[0]);return 'rgb('+a[1].map((v,j)=>Math.round(v+(b[1][j]-v)*q)).join(',')+')';}return 'rgb(225,61,54)';};
function value(level,p,k){const arr=data[level]?.rows?.[p]?.hourly?.[k];return arr?.[idx];}
function levelZonalWind(level){
 const us=points.map((_,p)=>{const sp=value(level,p,keys(level)[2]),dr=value(level,p,keys(level)[3]);return Number.isFinite(sp)&&Number.isFinite(dr)?-sp*Math.sin(dr*Math.PI/180):null;}).filter(Number.isFinite);
 return us.length?us.reduce((a,b)=>a+b,0)/us.length:null;
}
function draw(){
 const c=$('p3dCanvas');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height,cx=w*.5,cy=h*.51,scale=155;
 g.clearRect(0,0,w,h);const bg=g.createLinearGradient(0,0,w,h);bg.addColorStop(0,'#061526');bg.addColorStop(1,'#123653');g.fillStyle=bg;g.fillRect(0,0,w,h);
 // polar reference grid
 g.strokeStyle='rgba(139,190,220,.30)';g.lineWidth=1.2;
 for(const lat of [60,70,80]){g.beginPath();for(let j=0;j<=72;j++){const p=project(lat,j*5, 0,cx,cy,scale);if(j===0)g.moveTo(p.x,p.y);else g.lineTo(p.x,p.y);}g.stroke();}
 const zBy={10:190,30:0,50:-190},faces=[],temps=[];
 const zonal={10:levelZonalWind(10),30:levelZonalWind(30),50:levelZonalWind(50)},twist={};
 for(const lev of levels)twist[lev]=Number.isFinite(zonal[lev])?Math.max(-28,Math.min(28,zonal[lev]*.55)):0;
 for(const lev of levels){for(let p=0;p<points.length;p++){const t=value(lev,p,keys(lev)[0]);if(Number.isFinite(t))temps.push(t);}}
 if(!temps.length){g.fillStyle='#e6f4ff';g.font='22px Arial';g.fillText('Čekám na tři hladiny NOAA GFS…',40,55);return;}
 const min=Math.min(...temps),max=Math.max(...temps);
 // Jemnější síť vzniká interpolací mezi sousedními GFS vzorky.
 // Nejde o nové modelové hodnoty; každý dílek je pouze vizualizace interpolace.
 const subdivisions=5;
 for(const lev of levels){const z=zBy[lev];for(let ri=0;ri<lats.length-1;ri++)for(let li=0;li<lons.length;li++){
  const lj=(li+1)%lons.length,a=ri*8+li,b=ri*8+lj,d=(ri+1)*8+li,e=(ri+1)*8+lj;
  const va=value(lev,a,keys(lev)[0]),vb=value(lev,b,keys(lev)[0]),vd=value(lev,d,keys(lev)[0]),ve=value(lev,e,keys(lev)[0]);
  if(![va,vb,vd,ve].every(Number.isFinite))continue;
  const lon0=lons[li],lon1=li===lons.length-1?lons[0]+360:lons[lj];
  for(let sy=0;sy<subdivisions;sy++)for(let sx=0;sx<subdivisions;sx++){
   const u0=sx/subdivisions,u1=(sx+1)/subdivisions,v0=sy/subdivisions,v1=(sy+1)/subdivisions;
   const sample=(u,v)=>{const top=va*(1-u)+vb*u,bot=vd*(1-u)+ve*u;return top*(1-v)+bot*v;};
   const temp=(u,v)=>sample(u,v),avg=(temp(u0,v0)+temp(u1,v0)+temp(u1,v1)+temp(u0,v1))/4;
   const t=max===min?.5:(avg-min)/(max-min),lat0=lats[ri],lat1=lats[ri+1];
   const pts=[[lat0+(lat1-lat0)*v0,lon0+(lon1-lon0)*u0],[lat0+(lat1-lat0)*v0,lon0+(lon1-lon0)*u1],[lat0+(lat1-lat0)*v1,lon0+(lon1-lon0)*u1],[lat0+(lat1-lat0)*v1,lon0+(lon1-lon0)*u0]].map(([lat,lon])=>project(lat,((lon+twist[lev]+180)%360+360)%360-180,z,cx,cy,scale));
   faces.push({pts,fill:palette(t),depth:pts.reduce((x,p)=>x+p.depth,0)/4,lev});
  }
 }}
 faces.sort((a,b)=>a.depth-b.depth);
 for(const f of faces){g.beginPath();f.pts.forEach((p,i)=>i?g.lineTo(p.x,p.y):g.moveTo(p.x,p.y));g.closePath();g.fillStyle=f.fill;g.globalAlpha=.84;g.fill();g.globalAlpha=1;}
 // Zakřivené spojnice: jejich natočení vychází z průměrné zonální složky
 // větru v každé hladině. Jde o diagnostickou vizualizaci, nikoli simulaci trajektorie.
 for(let p=0;p<points.length;p++){
  const path=[];
  for(let seg=0;seg<2;seg++)for(let step=0;step<=8;step++){
   if(seg===1&&step===0)continue;
   const a=step/8,la=levels[seg],lb=levels[seg+1],z=zBy[la]*(1-a)+zBy[lb]*a,rot=twist[la]*(1-a)+twist[lb]*a;
   path.push(project(points[p].lat,points[p].lon+rot,z,cx,cy,scale));
  }
  g.beginPath();path.forEach((q,i)=>i?g.lineTo(q.x,q.y):g.moveTo(q.x,q.y));g.strokeStyle='rgba(245,250,255,.46)';g.lineWidth=1.35;g.stroke();
 }
 // wind vectors and node dots, upper layers drawn last
 for(const lev of [50,30,10])for(let p=0;p<points.length;p++){
  const q=project(points[p].lat,points[p].lon+twist[lev],zBy[lev],cx,cy,scale),sp=value(lev,p,keys(lev)[2]),dr=value(lev,p,keys(lev)[3]);
  g.beginPath();g.arc(q.x,q.y,3.4,0,Math.PI*2);g.fillStyle='#f7fbff';g.fill();
  if(Number.isFinite(sp)&&Number.isFinite(dr)){const a=(dr+180)*Math.PI/180,L=8+Math.min(15,sp*.08),ex=q.x+Math.sin(a)*L,ey=q.y-Math.cos(a)*L;g.beginPath();g.moveTo(q.x,q.y);g.lineTo(ex,ey);g.strokeStyle='#ffffff';g.lineWidth=1.7;g.stroke();}
 }
 g.fillStyle='#eaf6ff';g.font='bold 22px Arial';g.fillText('3D POLÁRNÍ STRATOSFÉRA · NOAA GFS',28,36);
 g.font='bold 18px Arial';g.fillStyle='#63c9ff';g.fillText('10 hPa',cx+270,cy-145);g.fillStyle='#ffd166';g.fillText('30 hPa',cx+270,cy+5);g.fillStyle='#c6a0ff';g.fillText('50 hPa',cx+270,cy+155);
 g.font='13px Arial';g.fillStyle='#d4e8f6';g.fillText('Interpolovaná teplota · bílé body/šipky = vzorky/vítr · zakřivení = zonální vítr',28,h-42);
 g.fillText('U zonální (m/s): 10 hPa '+(zonal[10]?.toFixed(1)??'—')+' · 30 hPa '+(zonal[30]?.toFixed(1)??'—')+' · 50 hPa '+(zonal[50]?.toFixed(1)??'—')+' · '+(times[idx]||'').replace('T',' ')+' UTC',28,h-20);
 for(const lev of levels){const vals=points.map((_,p)=>value(lev,p,keys(lev)[0])).filter(Number.isFinite),el=$('p3d'+lev);if(el)el.textContent=vals.length?(vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1)+' °C':'—';}
}
async function load(){
 if(busy)return;busy=true;stop();status('Stahuji hodinová pole GFS pro hladiny 10, 30 a 50 hPa…');
 try{
  // Open-Meteo obsluhuje více souřadnic, ale velké dávky mohou být odmítnuty.
  // Menší dávky zkracují URL a umožňují přesně určit problematickou odpověď.
  const batchSize=8;
  const results=await Promise.all(levels.map(async lev=>{
   const batches=[];
   for(let i=0;i<points.length;i+=batchSize)batches.push(points.slice(i,i+batchSize));
   const parts=await Promise.all(batches.map(async batch=>{
    const lat=batch.map(p=>p.lat).join(','),lon=batch.map(p=>p.lon).join(',');
    const url='https://api.open-meteo.com/v1/gfs?latitude='+encodeURIComponent(lat)+'&longitude='+encodeURIComponent(lon)+'&hourly='+encodeURIComponent(keys(lev).join(','))+'&forecast_days=2&timezone=GMT';
    const r=await fetch(url,{cache:'no-store'});
    if(!r.ok){const body=await r.text();let detail=body.slice(0,400);try{const e=JSON.parse(body);detail=e.reason||e.message||JSON.stringify(e);}catch(_){}throw Error('GFS '+lev+' hPa HTTP '+r.status+(detail?' · '+detail:''));}
    const raw=await r.json(),rows=Array.isArray(raw)?raw:[raw];
    if(rows.length!==batch.length||!rows[0]?.hourly?.time)throw Error('Neúplná dávka GFS '+lev+' hPa ('+rows.length+'/'+batch.length+' bodů).');
    return rows;
   }));
   const rows=parts.flat();return {lev,rows,times:rows[0]?.hourly?.time||[]};
  }));
  const base=results[0].times;if(results.some(x=>x.times.length!==base.length||x.times.some((t,i)=>t!==base[i])))throw Error('Časové osy hladin se neshodují; společná animace není bezpečná.');
  data={};results.forEach(x=>data[x.lev]=x);times=base;idx=0;
  const sel=$('p3dTime');sel.innerHTML='';times.forEach((t,i)=>{const o=document.createElement('option');o.value=i;o.textContent=t.replace('T',' ')+' UTC';sel.appendChild(o);});
  status('Načteny všechny tři hladiny · '+points.length+' vzorkovacích bodů na hladinu · '+times.length+' hodinových kroků. '+times[0]+' až '+times[times.length-1]+' UTC.');draw();
 }catch(e){data={};status('3D data nejsou kompletní: '+String(e.message||e)+'. Zobrazení zůstává bez doplněných hodnot.');draw();}
 finally{busy=false;}
}
function stop(){if(timer)clearInterval(timer);timer=null;}
function play(){if(!times.length)return;stop();timer=setInterval(()=>{idx=(idx+1)%times.length;$('p3dTime').value=idx;draw();},Number($('p3dSpeed')?.value||800));}
$('p3dLoad')?.addEventListener('click',load);$('p3dPlay')?.addEventListener('click',play);$('p3dPause')?.addEventListener('click',stop);
$('p3dTime')?.addEventListener('change',e=>{idx=Number(e.target.value)||0;draw();});
$('p3dSpeed')?.addEventListener('change',()=>{if(timer)play();});
const canvas=$('p3dCanvas');if(canvas){canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-drag.x)*.008;pitch=Math.max(-.65,Math.min(.65,pitch+(e.clientY-drag.y)*.006));drag={x:e.clientX,y:e.clientY};draw();});canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);}
draw();load();
})();