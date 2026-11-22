(()=>{'use strict';
const $=id=>document.getElementById(id),LAT=Array.from({length:9},(_,i)=>40+i*5),LON=Array.from({length:15},(_,i)=>-30+i*5),FIELD='temperature_850hPa',API='https://api.open-meteo.com/v1/gfs';
let times=[],grid=[],playing=false,timer=null,coast=null;
const fmt=v=>Math.round(v).toString();
const box={l:76,r:34,t:48,b:72};
function color(v,min,max){
 const t=Math.max(0,Math.min(1,(v-min)/(max-min||1))),stops=[[0,[42,91,170]],[.25,[104,166,210]],[.5,[239,244,247]],[.75,[246,174,112]],[1,[185,54,48]]];
 let k=1;while(k<stops.length-1&&t>stops[k][0])k++;
 const a=stops[k-1],b=stops[k],u=(t-a[0])/(b[0]-a[0]);
 return a[1].map((x,i)=>Math.round(x+(b[1][i]-x)*u));
}
function interpolate(a,b,t){return a+(b-a)*t;}
function sample(i,j,vals){const y=Math.min(LAT.length-1,Math.max(0,i)),x=Math.min(LON.length-1,Math.max(0,j)),i0=Math.floor(y),j0=Math.floor(x),i1=Math.min(i0+1,LAT.length-1),j1=Math.min(j0+1,LON.length-1),fy=y-i0,fx=x-j0;
 const q=[vals[i0][j0],vals[i0][j1],vals[i1][j1],vals[i1][j0]];if(q.some(v=>!Number.isFinite(v)))return NaN;
 return interpolate(interpolate(q[0],q[1],fx),interpolate(q[3],q[2],fx),fy);
}
function mapXY(lon,lat,w,h){const p={w:w-box.l-box.r,h:h-box.t-box.b};return [box.l+(lon+30)/70*p.w,box.t+(80-lat)/40*p.h];}
function drawCountries(g,w,h){
 if(!coast)return;
 g.save();g.beginPath();g.rect(box.l,box.t,w-box.l-box.r,h-box.t-box.b);g.clip();
 const drawRing=ring=>{for(let k=0;k<ring.length;k++){const [lon,lat]=ring[k];const p=mapXY(lon,lat,w,h);if(k===0)g.moveTo(...p);else g.lineTo(...p);}g.closePath();};
 g.strokeStyle='rgba(20,45,66,.72)';g.lineWidth=1.5;
 for(const f of coast.features||[]){const geo=f.geometry;if(!geo)continue;g.beginPath();if(geo.type==='Polygon')geo.coordinates.forEach(drawRing);else if(geo.type==='MultiPolygon')geo.coordinates.forEach(poly=>poly.forEach(drawRing));g.stroke();}
 g.restore();
}
function draw(){
 const c=$('pv850mapCanvas');if(!c||!grid.length)return;
 const g=c.getContext('2d'),w=c.width,h=c.height,idx=Number($('pv850mapTime')?.value||0),vals=grid.map(row=>row[idx]),all=vals.flat().filter(Number.isFinite);
 if(!all.length)return;
 const lo=-40,hi=20; // pevná meteorologicky čitelná stupnice °C; extrémy se barevně oříznou
 const nx=(LON.length-1)*6+1,ny=(LAT.length-1)*6+1,scale=6;
 const dense=Array.from({length:ny},(_,i)=>Array.from({length:nx},(_,j)=>sample(i/scale,j/scale,vals)));
 g.clearRect(0,0,w,h);g.fillStyle='#f4f8fc';g.fillRect(0,0,w,h);
 const pw=w-box.l-box.r,ph=h-box.t-box.b,cellW=pw/(nx-1),cellH=ph/(ny-1);
 // High-resolution bilinear color raster
 const raster=document.createElement('canvas');raster.width=nx;raster.height=ny;
 const rg=raster.getContext('2d'),im=rg.createImageData(nx,ny);
 for(let i=0;i<ny;i++)for(let j=0;j<nx;j++){const v=dense[i][j],rgb=color(v,lo,hi),p=(i*nx+j)*4;im.data[p]=rgb[0];im.data[p+1]=rgb[1];im.data[p+2]=rgb[2];im.data[p+3]=255;}
 rg.putImageData(im,0,0);g.imageSmoothingEnabled=true;g.drawImage(raster,box.l,box.t,pw,ph);
 // Graticule
 g.strokeStyle='rgba(255,255,255,.7)';g.lineWidth=1;g.font='14px Arial';g.fillStyle='#263b4f';
 for(let lon=-30;lon<=40;lon+=10){const x=mapXY(lon,40,w,h)[0];g.beginPath();g.moveTo(x,box.t);g.lineTo(x,h-box.b);g.stroke();g.textAlign='center';g.fillText(lon===0?'0°':Math.abs(lon)+'°'+(lon<0?'Z':'V'),x,h-box.b+25);}
 for(let lat=40;lat<=80;lat+=10){const y=mapXY(-30,lat,w,h)[1];g.beginPath();g.moveTo(box.l,y);g.lineTo(w-box.r,y);g.stroke();g.textAlign='right';g.fillText(lat+'°N',box.l-10,y+5);}
 // Country/coast outlines on top of raster
 drawCountries(g,w,h);
 // Smooth contour lines from dense interpolated field
 const step=5,levels=[];for(let z=lo+step;z<hi;z+=step)levels.push(z);
 const labelBoxes=[];
 levels.forEach(level=>{
  g.beginPath();let labelPoint=null;
  for(let i=0;i<ny-1;i++)for(let j=0;j<nx-1;j++){
   const v=[dense[i][j],dense[i][j+1],dense[i+1][j+1],dense[i+1][j]],p=[[box.l+j*cellW,box.t+i*cellH],[box.l+(j+1)*cellW,box.t+i*cellH],[box.l+(j+1)*cellW,box.t+(i+1)*cellH],[box.l+j*cellW,box.t+(i+1)*cellH]],hits=[];
   if(v.some(q=>!Number.isFinite(q)))continue;
   for(let k=0;k<4;k++){const n=(k+1)%4;if((v[k]<level&&v[n]>=level)||(v[k]>=level&&v[n]<level)){const t=(level-v[k])/(v[n]-v[k]);hits.push([p[k][0]+t*(p[n][0]-p[k][0]),p[k][1]+t*(p[n][1]-p[k][1])]);}}
   if(hits.length>=2){for(let k=0;k+1<hits.length;k+=2){g.moveTo(...hits[k]);g.lineTo(...hits[k+1]);if(!labelPoint)labelPoint=hits[k];}}
  }
  g.strokeStyle='rgba(20,42,59,.88)';g.lineWidth=1.7;g.stroke();
  if(labelPoint){const [lx,ly]=labelPoint;if(lx>box.l+18&&lx<w-box.r-30&&ly>box.t+12&&ly<h-box.b-12&&!labelBoxes.some(p=>Math.abs(p[0]-lx)<55&&Math.abs(p[1]-ly)<22)){labelBoxes.push([lx,ly]);g.font='bold 12px Arial';g.textAlign='center';g.lineWidth=3;g.strokeStyle='rgba(245,249,252,.95)';g.strokeText(fmt(level),lx,ly-4);g.fillStyle='#172f45';g.fillText(fmt(level),lx,ly-4);}}
 });
 // Header and scale
 g.textAlign='left';g.font='bold 18px Arial';g.fillStyle='#18324b';g.fillText('Teplota vzduchu 850 hPa · °C',box.l,27);
 const lx=box.l,ly=h-14,lw=pw,grad=g.createLinearGradient(lx,0,lx+lw,0);for(let k=0;k<=20;k++){const rgb=color(lo+(hi-lo)*k/20,lo,hi);grad.addColorStop(k/20,'rgb('+rgb.join(',')+')');}
 g.fillStyle=grad;g.fillRect(lx,ly-13,lw,11);g.fillStyle='#263b4f';g.font='12px Arial';g.textAlign='left';g.fillText(fmt(lo)+' °C',lx,ly+5);g.textAlign='right';g.fillText(fmt(hi)+' °C',lx+lw,ly+5);
}
async function load(){
 stop();const s=$('pv850mapStatus');if(s)s.textContent='Načítám společná evropská data GFS…';
 try{
  const data=await window.X5GFS.get();times=data.times;
  const index=new Map(data.points.map((p,i)=>[p.lat+','+p.lon,i]));
  grid=LAT.map(lat=>LON.map(lon=>data.arr[index.get(lat+','+lon)].hourly[FIELD]));
  const sel=$('pv850mapTime'),range=$('pv850mapRange');if(sel){sel.innerHTML='';times.forEach((v,i)=>{const o=document.createElement('option');o.value=i;o.textContent=v.replace('T',' ')+' UTC';sel.appendChild(o);});sel.value='0';}
  if(range){range.max=String(times.length-1);range.value='0';}
  draw();if(s)s.innerHTML='<b class="good">Teplotní pole načteno.</b> 135 bodů · '+times.length+' hodinových kroků · '+(data.stale?'uložená data ('+data.cacheAgeHours+' h)':'společná data GFS');
  const stamp=$('pv850mapStamp');if(stamp)stamp.textContent='Model NCEP GFS · '+times[0]+' UTC až '+times[times.length-1]+' UTC'+(data.stale?' · záložní kopie':'');
  try{if(!coast){const cr=await fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson',{cache:'force-cache'});if(cr.ok){coast=await cr.json();draw();}}}catch(_){}
 }catch(e){if(s)s.innerHTML='<b class="warn">Mapu se nepodařilo načíst:</b> '+String(e.message||e);}
}
function setTime(v){const n=Math.max(0,Math.min(times.length-1,Number(v)||0));const sel=$('pv850mapTime'),range=$('pv850mapRange'),tab=$('pv500Time'),map500=$('pvmapTime'),range500=$('pvmapRange');if(sel)sel.value=String(n);if(range)range.value=String(n);if(map500&&map500.value!==String(n)){map500.value=String(n);if(range500)range500.value=String(n);map500.dispatchEvent(new Event('change'));}if(tab&&tab.value!==String(n)){tab.value=String(n);tab.dispatchEvent(new Event('change'));}draw();const stamp=$('pv850mapStamp');if(stamp&&times[n])stamp.textContent='Model NCEP GFS · platnost '+times[n]+' UTC';}
function stop(){playing=false;if(timer)clearInterval(timer);timer=null;const b=$('pv850mapPlay');if(b)b.textContent='▶ Přehrát vývoj';}
function play(){if(!times.length)return;if(playing){stop();return;}playing=true;const b=$('pv850mapPlay');if(b)b.textContent='Ⅱ Pozastavit';timer=setInterval(()=>{let n=Number($('pv850mapTime')?.value||0)+1;if(n>=times.length)n=0;setTime(n);},700);}
const b=$('pv850mapRefresh'),sel=$('pv850mapTime'),range=$('pv850mapRange'),p=$('pv850mapPlay'),tab=$('pv500Time');if(b)b.addEventListener('click',load);if(sel)sel.addEventListener('change',()=>setTime(sel.value));if(tab)tab.addEventListener('change',()=>{if(tab.value!==$('pv850mapTime')?.value)setTime(tab.value);});if(range)range.addEventListener('input',()=>setTime(range.value));if(p)p.addEventListener('click',play);load();
})();