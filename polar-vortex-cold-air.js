(()=>{'use strict';
const $=id=>document.getElementById(id),LAT=Array.from({length:9},(_,i)=>40+i*5),LON=Array.from({length:15},(_,i)=>-30+i*5),API='https://api.open-meteo.com/v1/gfs';
const fields=['temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
let times=[],grid=[],wind=[],track=[];
const fmt=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:NaN;
function analyse(k){
 const cells=[];for(let i=0;i<LAT.length;i++)for(let j=0;j<LON.length;j++){const t=grid[i][j][k],w=wind[i][j][k];if(Number.isFinite(t))cells.push({lat:LAT[i],lon:LON[j],t,w});}
 const cold=cells.filter(x=>x.t<-10),weights=cold.map(x=>Math.max(0,-10-x.t)),sum=weights.reduce((a,b)=>a+b,0);
 const center=sum?{lat:cold.reduce((s,x,i)=>s+x.lat*weights[i],0)/sum,lon:cold.reduce((s,x,i)=>s+x.lon*weights[i],0)/sum}:null;
 return {min:Math.min(...cells.map(x=>x.t)),max:Math.max(...cells.map(x=>x.t)),n:cells.length,a5:100*cells.filter(x=>x.t< -5).length/cells.length,a10:100*cold.length/cells.length,a15:100*cells.filter(x=>x.t< -15).length/cells.length,center,wind:mean(cold.map(x=>x.w).filter(Number.isFinite))};
}
function render(){
 if(!times.length)return;const idx=Math.max(0,Math.min(times.length-1,Number($('pv850mapTime')?.value||$('pv500Time')?.value||0)));
 const d=analyse(idx);$('pvx5ColdMin').textContent=fmt(d.min)+' °C';$('pvx5ColdMax').textContent=fmt(d.max)+' °C';
 $('pvx5ColdArea5').textContent=fmt(d.a5,0)+' %';$('pvx5ColdArea10').textContent=fmt(d.a10,0)+' %';$('pvx5ColdArea15').textContent=fmt(d.a15,0)+' %';
 $('pvx5ColdStamp').textContent='Platnost '+times[idx]+' UTC · '+d.n+' platných bodů z '+LAT.length*LON.length;
 const center=$('pvx5ColdCenter');
 if(center){if(d.center)center.textContent='Těžiště: '+fmt(d.center.lat,1)+'° s. š., '+fmt(d.center.lon,1)+'° '+(d.center.lon<0?'z. d.':'v. d.')+'. Průměrná rychlost větru v bodech pod −10 °C: '+fmt(d.wind,1)+' km/h.';else center.textContent='V této časové platnosti není v síti žádný bod pod −10 °C.';}
 draw(idx);
}
function draw(idx){
 const c=$('pvx5ColdTrack');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height,p={l:58,r:24,t:22,b:42};g.clearRect(0,0,w,h);g.fillStyle='#f4f8fc';g.fillRect(0,0,w,h);
 const valid=track.map((d,i)=>({...d,i})).filter(x=>x.center);if(!valid.length){g.fillStyle='#263b4f';g.fillText('V předpovědi není oblast pod −10 °C.',p.l,45);return;}
 const x=i=>p.l+i*(w-p.l-p.r)/Math.max(1,times.length-1),y=lat=>h-p.b-(lat-40)/40*(h-p.t-p.b);
 g.strokeStyle='#d8e3ed';g.fillStyle='#52677a';g.font='13px Arial';for(let lat=40;lat<=80;lat+=10){g.beginPath();g.moveTo(p.l,y(lat));g.lineTo(w-p.r,y(lat));g.stroke();g.fillText(lat+'°N',8,y(lat)+4);}
 g.strokeStyle='#087fa5';g.lineWidth=3;g.beginPath();valid.forEach((d,i)=>{const xx=x(d.i),yy=y(d.center.lat);i?g.lineTo(xx,yy):g.moveTo(xx,yy);});g.stroke();
 valid.forEach(d=>{g.fillStyle='#087fa5';g.beginPath();g.arc(x(d.i),y(d.center.lat),4,0,Math.PI*2);g.fill();});
 const current=valid.find(d=>d.i===idx);if(current){g.fillStyle='#b42318';g.beginPath();g.arc(x(idx),y(current.center.lat),7,0,Math.PI*2);g.fill();}
 g.fillStyle='#263b4f';g.fillText('Zeměpisná šířka těžiště studené oblasti (< −10 °C)',p.l,15);g.fillText('Čas →',w-75,h-12);
}
async function load(){
 const status=$('pvx5ColdStatus');if(status)status.textContent='Načítám hodinová pole teploty a větru 850 hPa pro 135 bodů…';
 try{
  const coords=LAT.flatMap(lat=>LON.map(lon=>({lat,lon}))),res=[];
  for(let i=0;i<coords.length;i+=45){const q=new URLSearchParams({latitude:coords.slice(i,i+45).map(p=>p.lat).join(','),longitude:coords.slice(i,i+45).map(p=>p.lon).join(','),hourly:fields.join(','),forecast_days:'3',timezone:'GMT',wind_speed_unit:'kmh'});const r=await fetch(API+'?'+q,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const a=await r.json();res.push(...(Array.isArray(a)?a:[a]));}
  times=res[0]?.hourly?.time;if(!Array.isArray(times)||!times.length||res.length!==coords.length)throw Error('Neúplná odpověď GFS.');
  for(const r of res)for(const f of fields)if(!Array.isArray(r.hourly?.[f])||r.hourly[f].length!==times.length)throw Error('Chybí pole '+f);
  grid=LAT.map((_,i)=>LON.map((_,j)=>res[i*LON.length+j].hourly.temperature_850hPa));
  wind=LAT.map((_,i)=>LON.map((_,j)=>res[i*LON.length+j].hourly.wind_speed_850hPa));
  track=times.map((_,k)=>analyse(k));
  if(status)status.innerHTML='<b class="good">Diagnostika studeného vzduchu načtena.</b> 135 bodů · '+times.length+' hodinových kroků · GFS 850 hPa.';
  render();
 }catch(e){if(status)status.innerHTML='<b class="warn">Diagnostiku se nepodařilo načíst:</b> '+String(e.message||e);}
}
const sel=$('pv850mapTime'),tab=$('pv500Time'),refresh=$('pv850mapRefresh');
if(sel)sel.addEventListener('change',render);if(tab)tab.addEventListener('change',render);if(refresh)refresh.addEventListener('click',load);load();
})();