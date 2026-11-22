(()=>{'use strict';
const $=id=>document.getElementById(id),LAT=Array.from({length:9},(_,i)=>40+i*5),LON=Array.from({length:15},(_,i)=>-30+i*5),FIELDS='geopotential_height_500hPa',API='https://api.open-meteo.com/v1/gfs';
let times=[],grid=[];
const fmt=v=>Math.round(v).toString();
async function fetchBatch(coords){
 const q=new URLSearchParams({latitude:coords.map(p=>p.lat).join(','),longitude:coords.map(p=>p.lon).join(','),hourly:FIELDS,forecast_days:'3',timezone:'GMT'});
 const r=await fetch(API+'?'+q,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);
 const raw=await r.json(),arr=Array.isArray(raw)?raw:[raw];
 if(arr.length!==coords.length)throw Error('API vrátilo jiný počet bodů.');
 return arr;
}
function color(v,min,max){
 const t=Math.max(0,Math.min(1,(v-min)/(max-min||1)));
 const stops=[[0,[35,83,155]],[.25,[76,145,190]],[.5,[224,231,194]],[.75,[242,169,93]],[1,[174,61,56]]];
 let k=1;while(k<stops.length-1&&t>stops[k][0])k++;
 const a=stops[k-1],b=stops[k],u=(t-a[0])/(b[0]-a[0]);
 return 'rgb('+a[1].map((x,i)=>Math.round(x+(b[1][i]-x)*u)).join(',')+')';
}
function draw(){
 const c=$('pvmapCanvas');if(!c||!grid.length)return;
 const g=c.getContext('2d'),w=c.width,h=c.height,box={l:75,r:35,t:40,b:65},pw=w-box.l-box.r,ph=h-box.t-box.b;
 const nx=LON.length,ny=LAT.length,vals=grid.map(row=>row[Number($('pvmapTime')?.value||0)]),all=vals.flat().filter(Number.isFinite);
 if(!all.length)return;
 const lo=Math.floor(Math.min(...all)/60)*60,hi=Math.ceil(Math.max(...all)/60)*60||lo+60;
 const x=j=>box.l+j*pw/(nx-1),y=i=>box.t+(ny-1-i)*ph/(ny-1);
 g.clearRect(0,0,w,h);g.fillStyle='#f4f8fc';g.fillRect(0,0,w,h);
 // Interpolated colored cells
 for(let i=0;i<ny-1;i++)for(let j=0;j<nx-1;j++){
  const v=(vals[i][j]+vals[i][j+1]+vals[i+1][j]+vals[i+1][j+1])/4;
  g.fillStyle=color(v,lo,hi);g.fillRect(x(j),y(i+1),pw/(nx-1)+1,ph/(ny-1)+1);
 }
 // Coastline-like graticule and labels
 g.strokeStyle='rgba(255,255,255,.75)';g.lineWidth=1;
 for(let j=0;j<nx;j+=2){g.beginPath();g.moveTo(x(j),box.t);g.lineTo(x(j),box.t+ph);g.stroke();g.fillStyle='#263b4f';g.font='14px Arial';g.textAlign='center';g.fillText(LON[j]===0?'0°':Math.abs(LON[j])+'°'+(LON[j]<0?'W':'E'),x(j),h-30);}
 for(let i=0;i<ny;i+=2){g.beginPath();g.moveTo(box.l,y(i));g.lineTo(box.l+pw,y(i));g.stroke();g.textAlign='right';g.fillStyle='#263b4f';g.fillText(LAT[i]+'°N',box.l-10,y(i)+5);}
 // Marching squares contours
 const step=60,levels=[];for(let z=Math.ceil(lo/step)*step;z<=hi;z+=step)levels.push(z);
 g.lineWidth=2;g.strokeStyle='#152b43';g.font='bold 13px Arial';
 levels.forEach(level=>{
  g.beginPath();
  for(let i=0;i<ny-1;i++)for(let j=0;j<nx-1;j++){
   const v=[vals[i][j],vals[i][j+1],vals[i+1][j+1],vals[i+1][j]],p=[[x(j),y(i)],[x(j+1),y(i)],[x(j+1),y(i+1)],[x(j),y(i+1)]],hits=[];
   for(let k=0;k<4;k++){const n=(k+1)%4;if((v[k]<level&&v[n]>=level)||(v[k]>=level&&v[n]<level)){const t=(level-v[k])/(v[n]-v[k]);hits.push([p[k][0]+t*(p[n][0]-p[k][0]),p[k][1]+t*(p[n][1]-p[k][1])]);}}
   for(let k=0;k+1<hits.length;k+=2){g.moveTo(...hits[k]);g.lineTo(...hits[k+1]);}
  }
  g.stroke();
 });
 // Legend
 const lx=box.l,ly=h-12,lw=pw,grad=g.createLinearGradient(lx,0,lx+lw,0);
 for(let k=0;k<=10;k++)grad.addColorStop(k/10,color(lo+(hi-lo)*k/10,lo,hi));
 g.fillStyle=grad;g.fillRect(lx,ly-14,lw,12);g.fillStyle='#263b4f';g.textAlign='left';g.fillText(fmt(lo)+' m',lx,ly+5);g.textAlign='right';g.fillText(fmt(hi)+' m',lx+lw,ly+5);
 g.textAlign='left';g.font='bold 18px Arial';g.fillStyle='#18324b';g.fillText('Geopotenciální výška 500 hPa · m',box.l,25);
}
async function load(){
 const s=$('pvmapStatus');if(s)s.textContent='Stahuji evropské pole v dílčích dávkách…';
 try{
  const coords=LAT.flatMap(lat=>LON.map(lon=>({lat,lon}))),results=[];
  for(let i=0;i<coords.length;i+=45)results.push(...await fetchBatch(coords.slice(i,i+45)));
  const t=results[0]?.hourly?.time;if(!Array.isArray(t)||!t.length)throw Error('Chybí časová řada.');
  if(results.some(r=>!Array.isArray(r.hourly?.[FIELDS])||r.hourly[FIELDS].length!==t.length))throw Error('V některých bodech chybí geopotenciál.');
  times=t;grid=LAT.map((_,i)=>LON.map((_,j)=>results[i*LON.length+j].hourly[FIELDS]));
  const sel=$('pvmapTime');if(sel){sel.innerHTML='';t.forEach((v,i)=>{const o=document.createElement('option');o.value=i;o.textContent=v.replace('T',' ')+' UTC';sel.appendChild(o);});sel.value='0';}
  draw();if(s)s.innerHTML='<b class="good">Evropské pole načteno.</b> '+coords.length+' bodů · '+t.length+' hodinových kroků · síť 5°.';
  const stamp=$('pvmapStamp');if(stamp)stamp.textContent='Model NCEP GFS přes Open-Meteo · '+t[0]+' UTC až '+t[t.length-1]+' UTC';
 }catch(e){if(s)s.innerHTML='<b class="warn">Mapu se nepodařilo načíst:</b> '+String(e.message||e)+'. Zkontrolujte připojení a dostupnost API.';}
}
const b=$('pvmapRefresh'),s=$('pvmapTime');if(b)b.addEventListener('click',load);if(s)s.addEventListener('change',draw);load();
})();