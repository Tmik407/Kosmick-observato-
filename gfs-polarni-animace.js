(()=>{'use strict';
const $=id=>document.getElementById(id);
const levels=[60,65,70,75,80,85,88,90],lons=Array.from({length:12},(_,i)=>i*30);
const points=[];for(const lat of levels)for(const lon of lons)points.push({lat,lon});
let payload=[],times=[],timer=null,loadedLevel=null,loading=false;
const fieldName=(field,level)=>field==='temperature'?'temperature_'+level+'hPa':field==='geopotential'?'geopotential_height_'+level+'hPa':'wind_speed_'+level+'hPa';
const project=(lat,lon,cx,cy,R)=>{const r=(90-lat)/30*R,a=(lon-90)*Math.PI/180;return{x:cx+r*Math.cos(a),y:cy+r*Math.sin(a)};};
function color(v,min,max){const t=max===min?.5:(v-min)/(max-min);return 'hsl('+(240-240*Math.max(0,Math.min(1,t)))+',88%,52%)';}
function draw(){
 const c=$('gfsGridMap');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height,cx=w/2,cy=h/2+8,R=Math.min(330,h*.405,w*.39);
 g.clearRect(0,0,w,h);g.fillStyle='#f5f9fd';g.fillRect(0,0,w,h);
 const bg=g.createRadialGradient(cx,cy,8,cx,cy,R);bg.addColorStop(0,'#dff3ff');bg.addColorStop(1,'#b5d6e9');g.fillStyle=bg;g.beginPath();g.arc(cx,cy,R,0,Math.PI*2);g.fill();
 for(const lat of [60,65,70,75,80,85]){const r=(90-lat)/30*R;g.beginPath();g.arc(cx,cy,r,0,Math.PI*2);g.strokeStyle='#789bb4';g.lineWidth=lat===60?2:1;g.stroke();}
 for(let lon=0;lon<360;lon+=30){const p=project(60,lon,cx,cy,R);g.beginPath();g.moveTo(cx,cy);g.lineTo(p.x,p.y);g.strokeStyle='#91aec2';g.lineWidth=1;g.stroke();}
 g.textAlign='center';g.fillStyle='#21445e';g.font='bold 18px Arial';g.fillText('SEVERNÍ PÓL',cx,cy-10);
 if(!payload.length){g.textAlign='left';g.fillStyle='#536d80';g.font='16px Arial';g.fillText('Čekám na meteorologická data NOAA GFS…',28,36);return;}
 const level=$('gfsLevel').value,field=$('gfsField').value,idx=Number($('gfsTime').value)||0,key=fieldName(field,level);
 const rows=payload.map(x=>({x,v:x.hourly?.[key]?.[idx],speed:x.hourly?.['wind_speed_'+level+'hPa']?.[idx],dir:x.hourly?.['wind_direction_'+level+'hPa']?.[idx]})).filter(z=>Number.isFinite(z.v));
 if(!rows.length){$('gfsMapStatus').textContent='Pro tento čas a hladinu nejsou platné hodnoty.';return;}
 const vals=rows.map(x=>x.v),min=Math.min(...vals),max=Math.max(...vals);
 for(const z of rows){const p=project(z.x.latitude,z.x.longitude,cx,cy,R),rad=field==='geopotential'?18:21;g.beginPath();g.arc(p.x,p.y,rad,0,Math.PI*2);g.fillStyle=color(z.v,min,max);g.globalAlpha=.92;g.fill();g.globalAlpha=1;g.strokeStyle='#fff';g.lineWidth=1.5;g.stroke();
 if(Number.isFinite(z.speed)&&Number.isFinite(z.dir)){const a=(z.dir+180)*Math.PI/180,L=Math.min(28,8+z.speed*.18),ex=p.x+Math.sin(a)*L,ey=p.y-Math.cos(a)*L;g.strokeStyle='#163e5a';g.lineWidth=2;g.beginPath();g.moveTo(p.x,p.y);g.lineTo(ex,ey);g.stroke();}}
 const unit=field==='temperature'?'°C':field==='geopotential'?'m':'km/h';
 g.textAlign='left';g.fillStyle='#173c59';g.font='bold 17px Arial';g.fillText((field==='temperature'?'TEPLOTA':field==='geopotential'?'GEOPOTENCIÁLNÍ VÝŠKA':'RYCHLOST VĚTRU')+' · '+level+' hPa',25,30);
 g.font='14px Arial';g.fillText('Rozsah '+min.toFixed(1)+' až '+max.toFixed(1)+' '+unit+' · '+rows.length+' bodů',25,h-28);
 const t=times[idx]||'';if($('gfsAnimState'))$('gfsAnimState').textContent='Platnost: '+t.replace('T',' ')+' UTC';
}
async function load(){
 if(loading)return;loading=true;const level=$('gfsLevel').value,status=$('gfsMapStatus');status.textContent='Načítám hodinová pole GFS · hladina '+level+' hPa…';
 try{
  const batches=[];for(let i=0;i<points.length;i+=12)batches.push(points.slice(i,i+12));
  const results=await Promise.all(batches.map(async batch=>{
   const lat=batch.map(p=>p.lat).join(','),lon=batch.map(p=>p.lon).join(',');
   const vars=['temperature_'+level+'hPa','geopotential_height_'+level+'hPa','wind_speed_'+level+'hPa','wind_direction_'+level+'hPa'].join(',');
   const url='https://api.open-meteo.com/v1/gfs?latitude='+lat+'&longitude='+lon+'&hourly='+vars+'&forecast_days=2&timezone=GMT';
   const res=await fetch(url,{cache:'no-store'});if(!res.ok)throw Error('GFS API HTTP '+res.status);
   const data=await res.json();return Array.isArray(data)?data:[data];
  }));
  payload=results.flat();if(!payload.length||!payload[0].hourly)throw Error('Odpověď GFS neobsahuje hodinová data.');
  times=payload[0].hourly.time||[];if(!times.length)throw Error('GFS nevrátil časové kroky.');
  const sel=$('gfsTime'),old=sel.value;sel.innerHTML='';times.forEach((t,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=t.replace('T',' ')+' UTC';sel.appendChild(o);});sel.value=String(Math.min(Number(old)||0,times.length-1));
  loadedLevel=level;
  const range=(key,unit)=>{const a=payload.flatMap(x=>x.hourly?.[key]||[]).filter(Number.isFinite);return a.length?Math.min(...a).toFixed(1)+' – '+Math.max(...a).toFixed(1)+' '+unit:'—';};
  $('gfsTempRange').textContent=range('temperature_'+level+'hPa','°C');$('gfsZRange').textContent=range('geopotential_height_'+level+'hPa','m');$('gfsWindRange').textContent=range('wind_speed_'+level+'hPa','km/h');$('gfsPointCount').textContent=payload.filter(x=>x.hourly).length+' / '+points.length;
  status.innerHTML='<b class="good">Modelová síť načtena.</b> NOAA GFS přes Open-Meteo · '+level+' hPa · '+payload.length+' vzorkovaných bodů · '+times.length+' časových kroků.';
  draw();
 }catch(e){status.innerHTML='<b class="warn">Načtení GFS se nezdařilo:</b> '+String(e.message||e)+'. Záložní archivované mapy NOAA zůstávají dostupné.';draw();}
 finally{loading=false;}
}
function stop(){if(timer){clearInterval(timer);timer=null;}$('gfsAnimPlay').textContent='▶ Přehrát předpověď';}
function play(){stop();const s=$('gfsTime');if(!times.length||s.options.length<2){$('gfsAnimState').textContent='Nejdříve čekám na načtení časových kroků GFS.';return;}let i=Number(s.value)||0;timer=setInterval(()=>{i=(i+1)%times.length;s.value=String(i);s.dispatchEvent(new Event('change',{bubbles:true}));},Number($('gfsAnimSpeed').value)||800);$('gfsAnimPlay').textContent='Ⅱ Animace běží';}
$('gfsLevel').addEventListener('change',()=>{stop();payload=[];times=[];load();});
$('gfsField').addEventListener('change',draw);$('gfsTime').addEventListener('change',draw);
$('gfsAnimPlay').addEventListener('click',()=>timer?stop():play());$('gfsAnimStop').addEventListener('click',stop);
$('gfsAnimSpeed').addEventListener('change',()=>{if(timer)play();});
draw();load();
})();