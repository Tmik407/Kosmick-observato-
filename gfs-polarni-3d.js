(()=>{'use strict';
const $=id=>document.getElementById(id),levels=[10,30,50],lats=[60,68,76,84,88],lons=[-157.5,-112.5,-67.5,-22.5,22.5,67.5,112.5,157.5];
const points=[];for(const lat of lats)for(const lon of lons)points.push({lat,lon});
const keys=l=>['temperature_'+l+'hPa','geopotential_height_'+l+'hPa','wind_speed_'+l+'hPa','wind_direction_'+l+'hPa'];
let data={},times=[],idx=0,yaw=-.35,pitch=.22,timer=null,busy=false,drag=null,shapeCache={},windCache={},loadError='';
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
function levelWind(level){
 const u=[],v=[],z=[];
 points.forEach((_,p)=>{
  const sp=value(level,p,keys(level)[2]),dr=value(level,p,keys(level)[3]),gh=value(level,p,keys(level)[1]);
  if(Number.isFinite(sp)&&Number.isFinite(dr)){
   const rad=dr*Math.PI/180;u.push(-sp*Math.sin(rad));v.push(-sp*Math.cos(rad));
  }
  if(Number.isFinite(gh))z.push(gh);
 });
 const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
 return {u:mean(u),v:mean(v),height:mean(z),heights:z};
}
function interpolatedWind(level,lat,lon){
 const candidates=points.map((p,i)=>{
  const dlat=p.lat-lat,dlon=((((p.lon-lon)+540)%360)-180)*Math.max(.2,Math.cos(lat*Math.PI/180));
  return {i,d:dlat*dlat+dlon*dlon};
 }).sort((a,b)=>a.d-b.d).slice(0,4);
 let u=0,v=0,total=0,speed=0;
 for(const c of candidates){
  const sp=value(level,c.i,keys(level)[2]),dr=value(level,c.i,keys(level)[3]);
  if(!Number.isFinite(sp)||!Number.isFinite(dr))continue;
  const w=1/Math.max(.0001,c.d),a=dr*Math.PI/180;
  u+=(-sp*Math.sin(a))*w;v+=(-sp*Math.cos(a))*w;speed+=sp*w;total+=w;
 }
 return total?{u:u/total,v:v/total,speed:speed/total}:null;
}
function shapeAt(lat,lon,level){
 const cacheKey=level+':'+lat.toFixed(3)+':'+lon.toFixed(3);if(shapeCache[cacheKey])return shapeCache[cacheKey];
 const p=points.reduce((best,q,i)=>Math.abs(q.lat-lat)+Math.abs((((q.lon-lon)+540)%360)-180)<best.d?{i,d:Math.abs(q.lat-lat)+Math.abs((((q.lon-lon)+540)%360)-180)}:best,{i:0,d:Infinity}).i;
 const wind=windCache[level]||(windCache[level]=levelWind(level)),local=interpolatedWind(level,lat,lon);
 const gh=value(level,p,keys(level)[1]),heights=wind.heights,meanH=wind.height;
 const heightAnomaly=Number.isFinite(gh)&&Number.isFinite(meanH)?Math.max(-1,Math.min(1,(gh-meanH)/Math.max(1500,...heights.map(x=>Math.abs(x-meanH))))):0;
 const localSpeed=local?Math.min(1,local.speed/70):0;
 const direction=local?Math.atan2(-local.u,-local.v):0;
 const flowShape=localSpeed*Math.cos(2*(lon*Math.PI/180-direction));
 const ellipse=Math.max(.82,Math.min(1.18,1+flowShape*.09+heightAnomaly*.065));
 const localTurn=local?Math.max(-14,Math.min(14,(local.speed/70)*Math.sin(direction-lon*Math.PI/180)*11)):0;
 const spiral=(Number.isFinite(wind.u)?Math.max(-18,Math.min(18,wind.u*.22)):0)+localTurn;
 return shapeCache[cacheKey]={ellipse,spiral};
}
function levelDiagnostics(level){
 const gh=points.map((_,p)=>value(level,p,keys(level)[1])).filter(Number.isFinite);
 const sp=points.map((_,p)=>value(level,p,keys(level)[2])).filter(Number.isFinite);
 const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
 const avg=mean(gh),spread=gh.length?Math.sqrt(mean(gh.map(x=>(x-avg)**2))):null;
 const min=gh.length?Math.min(...gh):null,max=gh.length?Math.max(...gh):null;
 return {heightMean:avg,heightSpread:spread,heightRange:min!==null?max-min:null,windMean:mean(sp)};
}
function drawStreamlines(g,level,cx,cy,scale,twist){
 // Proudnice integrují prostorově interpolované GFS větry metodou RK2.
 // Jde o diagnostickou vizualizaci proudění, nikoli o sledování částic.
 const seeds=[[-165,63],[-145,72],[-125,82],[-95,67],[-75,78],[-45,85],[-15,65],[15,75],[45,84],[75,66],[105,77],[135,85],[165,70]];
 const color=speed=>speed<15?'#8bd7ff':speed<30?'#4ee0c0':speed<45?'#ffd166':'#ff916e';
 g.save();g.lineWidth=2.8;g.lineCap='round';g.shadowBlur=5;g.shadowColor='rgba(110,220,255,.45)';
 for(const seed of seeds){
  let lon=seed[0],lat=seed[1],prev=null;
  for(let step=0;step<30;step++){
   if(lat<60||lat>89)break;
   const w1=interpolatedWind(level,lat,lon);if(!w1)break;
   const dt=1100,cos=Math.max(.2,Math.cos(lat*Math.PI/180));
   const midLat=lat+w1.v*dt/(2*111000),midLon=lon+w1.u*dt/(2*111000*cos);
   const w2=interpolatedWind(level,midLat,midLon)||w1;
   const nextLat=lat+w2.v*dt/111000,nextLon=lon+w2.u*dt/(111000*Math.max(.2,Math.cos(midLat*Math.PI/180)));
   const p=shapedProject(lat,lon+twist,level,cx,cy,scale);
   if(prev){g.strokeStyle=color(w1.speed);g.beginPath();g.moveTo(prev.x,prev.y);g.lineTo(p.x,p.y);g.stroke();}
   prev=p;lat=nextLat;lon=nextLon;
  }
 }
 g.restore();
}
function shapedProject(lat,lon,level,cx,cy,scale){
 const sh=shapeAt(lat,lon,level),a=lon+sh.spiral;
 const p=project(lat, a, level===10?190:level===30?0:-190,cx,cy,scale);
 const dx=p.x-cx,dy=p.y-cy;
 return {...p,x:cx+dx*sh.ellipse,y:cy+dy*sh.ellipse};
}
function historyValue(level,key,i){
 const a=points.map((_,p)=>data[level]?.rows?.[p]?.hourly?.[key]?.[i]).filter(Number.isFinite);
 if(!a.length)return null;const m=a.reduce((x,y)=>x+y,0)/a.length;
 return Math.sqrt(a.reduce((x,y)=>x+(y-m)**2,0)/a.length);
}
function historyShear(a,b,i){
 const mean=level=>{const u=[],v=[];points.forEach((_,p)=>{const row=data[level]?.rows?.[p]?.hourly,sp=row?.[keys(level)[2]]?.[i],dr=row?.[keys(level)[3]]?.[i];if(Number.isFinite(sp)&&Number.isFinite(dr)){const r=dr*Math.PI/180;u.push(-sp*Math.sin(r));v.push(-sp*Math.cos(r));}});return u.length?[u.reduce((x,y)=>x+y,0)/u.length,v.reduce((x,y)=>x+y,0)/v.length]:null;};
 const x=mean(a),y=mean(b);return x&&y?Math.hypot(x[0]-y[0],x[1]-y[1]):null;
}
function drawHistoryCharts(){
 const configs=[
  ['p3dGeoChart','Geopotenciální asymetrie σ (m)',[
   ['10 hPa','#39b8f0',i=>historyValue(10,keys(10)[1],i)],['30 hPa','#f4c45e',i=>historyValue(30,keys(30)[1],i)],['50 hPa','#b99aff',i=>historyValue(50,keys(50)[1],i)]]],
  ['p3dShearChart','Vertikální střih větru (m/s)',[
   ['10–30 hPa','#43c6a5',i=>historyShear(10,30,i)],['30–50 hPa','#ff9b70',i=>historyShear(30,50,i)]]]
 ];
 for(const [id,title,series] of configs){const c=$(id);if(!c)continue;const g=c.getContext('2d'),w=c.width,h=c.height,L=48,R=16,T=30,B=32;g.clearRect(0,0,w,h);g.fillStyle='#0b2033';g.fillRect(0,0,w,h);g.font='bold 14px Arial';g.fillStyle='#e4f1fa';g.fillText(title,L,19);if(!times.length){g.font='15px Arial';g.fillStyle='#a9c7dc';g.fillText(loadError?'Graf čeká na obnovení dat NOAA GFS.':'Graf se zobrazí po načtení časové řady.',L,75);continue;}
  
  const vals=series.flatMap(a=>times.map((_,i)=>a[2](i))).filter(Number.isFinite);if(!vals.length)continue;
  const lo=Math.min(0,...vals),hi=Math.max(1,...vals),x=i=>L+i/Math.max(1,times.length-1)*(w-L-R),y=v=>h-B-(v-lo)/(hi-lo)*(h-T-B);
  g.strokeStyle='rgba(220,240,255,.18)';g.fillStyle='#c5d7e6';g.font='11px Arial';
  for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,yy=y(v);g.beginPath();g.moveTo(L,yy);g.lineTo(w-R,yy);g.stroke();g.fillText(v.toFixed(0),6,yy+4);}
  series.forEach(([label,color,fn],j)=>{g.strokeStyle=color;g.lineWidth=2.5;g.beginPath();let started=false;times.forEach((_,i)=>{const v=fn(i);if(!Number.isFinite(v)){started=false;return;}if(!started){g.moveTo(x(i),y(v));started=true;}else g.lineTo(x(i),y(v));});g.stroke();g.fillStyle=color;g.fillText(label,L+8+j*135,T-8);});
  g.strokeStyle='#fff';g.setLineDash([4,4]);g.beginPath();g.moveTo(x(idx),T);g.lineTo(x(idx),h-B);g.stroke();g.setLineDash([]);
  g.fillStyle='#c5d7e6';g.fillText(times[0].slice(5,13).replace('T',' ')+' UTC',L,h-9);g.fillText(times[times.length-1].slice(5,13).replace('T',' ')+' UTC',w-145,h-9);
 }
}
function draw(){
 shapeCache={};windCache={};
 const c=$('p3dCanvas');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height,cx=w*.5,cy=h*.51,scale=155;
 g.clearRect(0,0,w,h);const bg=g.createLinearGradient(0,0,w,h);bg.addColorStop(0,'#061526');bg.addColorStop(1,'#123653');g.fillStyle=bg;g.fillRect(0,0,w,h);
 // polar reference grid
 g.strokeStyle='rgba(139,190,220,.30)';g.lineWidth=1.2;
 for(const lat of [60,70,80]){g.beginPath();for(let j=0;j<=72;j++){const p=project(lat,j*5, 0,cx,cy,scale);if(j===0)g.moveTo(p.x,p.y);else g.lineTo(p.x,p.y);}g.stroke();}
 const zBy={10:190,30:0,50:-190},faces=[],temps=[];
 const winds={10:levelWind(10),30:levelWind(30),50:levelWind(50)},zonal={10:winds[10].u,30:winds[30].u,50:winds[50].u},twist={};
 for(const lev of levels)twist[lev]=Number.isFinite(zonal[lev])?Math.max(-28,Math.min(28,zonal[lev]*.55)):0;
 for(const lev of levels){for(let p=0;p<points.length;p++){const t=value(lev,p,keys(lev)[0]);if(Number.isFinite(t))temps.push(t);}}
 if(!temps.length){g.fillStyle='#e6f4ff';g.font='bold 22px Arial';g.fillText(loadError?'DATA NOAA GFS NYNÍ NEJSOU DOSTUPNÁ':'Čekám na tři hladiny NOAA GFS…',40,55);g.font='16px Arial';g.fillStyle='#a9c7dc';const msg=loadError?loadError.slice(0,105):'Model se zobrazí po načtení všech tří tlakových hladin.';g.fillText(msg,40,88);g.font='14px Arial';g.fillText('Žádné náhradní ani odhadované hodnoty nejsou vykresleny.',40,116);return;}
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
   const pts=[[lat0+(lat1-lat0)*v0,lon0+(lon1-lon0)*u0],[lat0+(lat1-lat0)*v0,lon0+(lon1-lon0)*u1],[lat0+(lat1-lat0)*v1,lon0+(lon1-lon0)*u1],[lat0+(lat1-lat0)*v1,lon0+(lon1-lon0)*u0]].map(([lat,lon])=>shapedProject(lat,((lon+twist[lev]+180)%360+360)%360-180,lev,cx,cy,scale));
   faces.push({pts,fill:palette(t),depth:pts.reduce((x,p)=>x+p.depth,0)/4,lev});
  }
 }}
 // Svislé plochy propojují 10, 30 a 50 hPa do jednoho souvislého
 // prostorového tělesa. Jde o interpolaci mezi hladinami, ne o další GFS vzorky.
 const bridgeFaces=[];
 for(let seg=0;seg<2;seg++){
  const upper=levels[seg],lower=levels[seg+1];
  for(let ri=0;ri<lats.length-1;ri++)for(let li=0;li<lons.length;li++){
   const lj=(li+1)%lons.length,ids=[ri*8+li,ri*8+lj,(ri+1)*8+lj,(ri+1)*8+li];
   const vals=ids.flatMap(p=>[value(upper,p,keys(upper)[0]),value(lower,p,keys(lower)[0])]);
   if(!vals.every(Number.isFinite))continue;
   const lonA=lons[li],lonB=li===lons.length-1?lons[0]+360:lons[lj];
   const coords=[
    [lats[ri],lonA,upper],[lats[ri],lonB,upper],
    [lats[ri+1],lonB,upper],[lats[ri+1],lonA,upper],
    [lats[ri],lonA,lower],[lats[ri],lonB,lower],
    [lats[ri+1],lonB,lower],[lats[ri+1],lonA,lower]
   ];
   const temp=vals.reduce((a,b)=>a+b,0)/vals.length;
   const t=max===min?.5:(temp-min)/(max-min);
   const make=(a,b)=>shapedProject(a[0],((a[1]+twist[a[2]]+180)%360+360)%360-180,a[2],cx,cy,scale);
   // Čtyři stěny každé interpolované buňky vytvářejí souvislou boční strukturu.
   for(const faceIds of [[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]){
    const pts=faceIds.map(i=>make(coords[i]));
    bridgeFaces.push({pts,fill:palette(t),depth:pts.reduce((v,p)=>v+p.depth,0)/4});
   }
  }
 }
 bridgeFaces.sort((a,b)=>a.depth-b.depth);
 for(const f of bridgeFaces){
  g.beginPath();f.pts.forEach((p,i)=>i?g.lineTo(p.x,p.y):g.moveTo(p.x,p.y));g.closePath();
  g.fillStyle=f.fill;g.globalAlpha=.20;g.fill();g.globalAlpha=1;
  g.strokeStyle='rgba(230,246,255,.16)';g.lineWidth=.55;g.stroke();
 }
 faces.sort((a,b)=>a.depth-b.depth);
 for(const f of faces){g.beginPath();f.pts.forEach((p,i)=>i?g.lineTo(p.x,p.y):g.moveTo(p.x,p.y));g.closePath();g.fillStyle=f.fill;g.globalAlpha=.68;g.fill();g.globalAlpha=1;}
 // Zakřivené spojnice: jejich natočení vychází z průměrné zonální složky
 // větru v každé hladině. Jde o diagnostickou vizualizaci, nikoli simulaci trajektorie.
 for(let p=0;p<points.length;p++){
  const path=[];
  for(let seg=0;seg<2;seg++)for(let step=0;step<=8;step++){
   if(seg===1&&step===0)continue;
   const a=step/8,la=levels[seg],lb=levels[seg+1],z=zBy[la]*(1-a)+zBy[lb]*a,rot=twist[la]*(1-a)+twist[lb]*a;
   path.push(shapedProject(points[p].lat,points[p].lon+rot,la===lb?la:(a<.5?la:lb),cx,cy,scale));
  }
  g.beginPath();path.forEach((q,i)=>i?g.lineTo(q.x,q.y):g.moveTo(q.x,q.y));g.strokeStyle='rgba(245,250,255,.46)';g.lineWidth=1.35;g.stroke();
 }
 // Proudnice jsou vykresleny pod vzorkovacími body.
 for(const lev of levels)drawStreamlines(g,lev,cx,cy,scale,twist[lev]);
 // wind vectors and node dots, upper layers drawn last
 for(const lev of [50,30,10])for(let p=0;p<points.length;p++){
  const q=shapedProject(points[p].lat,points[p].lon+twist[lev],lev,cx,cy,scale),sp=value(lev,p,keys(lev)[2]),dr=value(lev,p,keys(lev)[3]);
  g.beginPath();g.arc(q.x,q.y,3.4,0,Math.PI*2);g.fillStyle='#f7fbff';g.fill();
  if(Number.isFinite(sp)&&Number.isFinite(dr)){const a=(dr+180)*Math.PI/180,L=8+Math.min(15,sp*.08),ex=q.x+Math.sin(a)*L,ey=q.y-Math.cos(a)*L;g.beginPath();g.moveTo(q.x,q.y);g.lineTo(ex,ey);g.strokeStyle='#ffffff';g.lineWidth=1.7;g.stroke();}
 }
 g.fillStyle='#eaf6ff';g.font='bold 22px Arial';g.fillText('3D POLÁRNÍ STRATOSFÉRA · NOAA GFS',28,36);
 g.font='bold 18px Arial';g.fillStyle='#63c9ff';g.fillText('10 hPa',cx+270,cy-145);g.fillStyle='#ffd166';g.fillText('30 hPa',cx+270,cy+5);g.fillStyle='#c6a0ff';g.fillText('50 hPa',cx+270,cy+155);
 g.font='13px Arial';g.fillStyle='#d4e8f6';g.fillText('Dynamická spirála a eliptická deformace · barva = teplota · šipky = vítr',28,h-42);
 const d10=levelDiagnostics(10),d30=levelDiagnostics(30),d50=levelDiagnostics(50);
 const shear10_30=Math.hypot(winds[10].u-winds[30].u,winds[10].v-winds[30].v),shear30_50=Math.hypot(winds[30].u-winds[50].u,winds[30].v-winds[50].v);
 g.font='11px Arial';
 g.fillText('Geopotenciální asymetrie σ (m): 10 '+(d10.heightSpread?.toFixed(0)??'—')+' · 30 '+(d30.heightSpread?.toFixed(0)??'—')+' · 50 '+(d50.heightSpread?.toFixed(0)??'—')+' | Vertikální střih (m/s): 10–30 '+(Number.isFinite(shear10_30)?shear10_30.toFixed(1):'—')+' · 30–50 '+(Number.isFinite(shear30_50)?shear30_50.toFixed(1):'—')+' | '+(times[idx]||'').replace('T',' ')+' UTC',28,h-20);
 for(const lev of levels){const vals=points.map((_,p)=>value(lev,p,keys(lev)[0])).filter(Number.isFinite),el=$('p3d'+lev);if(el)el.textContent=vals.length?(vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1)+' °C':'—';}
 drawHistoryCharts();
}
const CACHE_KEY='x5-gfs-polar-v15-cache';
const NOAA_BACKUP_URL='./data/polar-vortex/latest.json';
function applyRows(rows,base,stale=false){
 data={};levels.forEach(lev=>data[lev]={lev,rows,times:base});
 times=base;idx=Math.min(idx,Math.max(0,times.length-1));
 const sel=$('p3dTime');if(sel){sel.innerHTML='';times.forEach((t,i)=>{const o=document.createElement('option');o.value=i;o.textContent=t.replace('T',' ')+' UTC';sel.appendChild(o);});sel.value=idx;}
 status((stale?'Použita místní kopie posledních úspěšných dat · ':'Načteny všechny tři hladiny · ')+points.length+' vzorkovacích bodů na hladinu · '+times.length+' časových kroků. '+times[0]+' až '+times[times.length-1]+' UTC.'+(stale?' Data mohou být starší.':''));
 draw();
}
function readCache(){
 try{const c=JSON.parse(localStorage.getItem(CACHE_KEY)||'null');if(c&&Array.isArray(c.rows)&&Array.isArray(c.times)&&c.rows.length===points.length&&c.times.length)return c;}catch(_){}
 return null;
}
async function loadNoaaBackup(primaryError){
 const r=await fetch(NOAA_BACKUP_URL,{cache:'no-store'});
 if(!r.ok)throw Error('NOAA záloha HTTP '+r.status);
 const payload=await r.json();
 if(!payload||payload.source!=='NOAA NOMADS GFS 0.25° GRIB2'||!Array.isArray(payload.rows)||payload.rows.length!==points.length||!Array.isArray(payload.times)||!payload.times.length)throw Error('NOAA záložní soubor má neplatný formát.');
 const expected=levels.flatMap(lev=>keys(lev));
 for(const row of payload.rows)for(const key of expected)if(!Array.isArray(row.hourly?.[key])||row.hourly[key].length!==payload.times.length)throw Error('NOAA záloha neobsahuje úplnou časovou řadu '+key+'.');
 loadError='';applyRows(payload.rows,payload.times,true);
 const generated=payload.generated_utc||'čas neznámý';
 status('ZÁLOŽNÍ ZDROJ NOAA NOMADS GFS · '+payload.times.length+' časových kroků · cyklus '+(payload.cycle_utc||'neuveden')+' · vytvořeno '+generated+'. Primární Open-Meteo selhalo: '+String(primaryError.message||primaryError));
 try{localStorage.setItem(CACHE_KEY,JSON.stringify({rows:payload.rows,times:payload.times,savedAt:Date.now(),source:payload.source}));}catch(_){}
}
async function load(){
 if(busy)return;busy=true;stop();
 const cachedAtStart=readCache();
 if(cachedAtStart){applyRows(cachedAtStart.rows,cachedAtStart.times,true);status('Zobrazuji uloženou kopii dat; ověřuji dostupnost nových dat GFS…');}
 else{status('Stahuji společná hodinová pole GFS pro tři hladiny…');}
 try{
  // Všech 40 souřadnic a 12 proměnných posíláme v jediném požadavku.
  // Open-Meteo podporuje vícelokační odpověď; tím se minimalizuje spotřeba kvóty.
  const batchSize=points.length,allKeys=levels.flatMap(lev=>keys(lev));
  const batches=[];for(let i=0;i<points.length;i+=batchSize)batches.push(points.slice(i,i+batchSize));
  const parts=await Promise.all(batches.map(async batch=>{
   const lat=batch.map(p=>p.lat).join(','),lon=batch.map(p=>p.lon).join(',');
   const url='https://api.open-meteo.com/v1/gfs?latitude='+encodeURIComponent(lat)+'&longitude='+encodeURIComponent(lon)+'&hourly='+encodeURIComponent(allKeys.join(','))+'&forecast_days=2&timezone=GMT';
   const r=await fetch(url,{cache:'default'});
   if(!r.ok){const body=await r.text();let detail=body.slice(0,400);try{const e=JSON.parse(body);detail=e.reason||e.message||JSON.stringify(e);}catch(_){}throw Error('GFS HTTP '+r.status+(detail?' · '+detail:''));}
   const raw=await r.json(),rows=Array.isArray(raw)?raw:[raw];
   if(rows.length!==batch.length||!rows[0]?.hourly?.time)throw Error('Neúplná dávka GFS ('+rows.length+'/'+batch.length+' bodů).');
   return rows;
  }));
  const rows=parts.flat(),base=rows[0]?.hourly?.time||[];
  if(rows.length!==points.length||!base.length||rows.some(r=>!r.hourly?.time||r.hourly.time.length!==base.length||r.hourly.time.some((t,i)=>t!==base[i])))throw Error('Neúplná nebo nesouhlasná časová osa GFS.');
  loadError='';applyRows(rows,base,false);
  try{localStorage.setItem(CACHE_KEY,JSON.stringify({rows,times:base,savedAt:Date.now()}));}catch(_){status('Data načtena; místní mezipaměť se nepodařilo uložit.');}
 }catch(e){
  loadError=String(e.message||e);
  try{await loadNoaaBackup(e);}
  catch(noaaError){
   const cached=readCache();
   if(cached){applyRows(cached.rows,cached.times,true);const age=Math.max(0,Math.round((Date.now()-(cached.savedAt||0))/3600000));status('Open-Meteo selhalo: '+String(e.message||e)+'. NOAA záloha není dostupná: '+String(noaaError.message||noaaError)+'. Zobrazuji místní kopii (přibližné stáří '+age+' h).');}
   else{data={};times=[];status('Open-Meteo selhalo: '+String(e.message||e)+'. NOAA záloha zatím nebyla vytvořena nebo není dostupná: '+String(noaaError.message||noaaError)+'.');draw();}
  }
 }finally{busy=false;}
}

function stop(){if(timer)clearInterval(timer);timer=null;}
function play(){if(!times.length)return;stop();timer=setInterval(()=>{idx=(idx+1)%times.length;$('p3dTime').value=idx;draw();},Number($('p3dSpeed')?.value||800));}
$('p3dLoad')?.addEventListener('click',load);$('p3dPlay')?.addEventListener('click',play);$('p3dPause')?.addEventListener('click',stop);
$('p3dTime')?.addEventListener('change',e=>{idx=Number(e.target.value)||0;draw();});
$('p3dSpeed')?.addEventListener('change',()=>{if(timer)play();});
const canvas=$('p3dCanvas');if(canvas){canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-drag.x)*.008;pitch=Math.max(-.65,Math.min(.65,pitch+(e.clientY-drag.y)*.006));drag={x:e.clientX,y:e.clientY};draw();});canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);}
draw();load();
})();