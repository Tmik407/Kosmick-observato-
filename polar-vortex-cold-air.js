(()=>{'use strict';
const $=id=>document.getElementById(id),LAT=Array.from({length:9},(_,i)=>40+i*5),LON=Array.from({length:15},(_,i)=>-30+i*5),API='https://api.open-meteo.com/v1/gfs';
const fields=['temperature_850hPa','wind_speed_850hPa','wind_direction_850hPa'];
let times=[],cells=[],track=[];
const fmt=(v,d=1)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:NaN;
function analyse(k){
 const valid=cells.map(p=>({...p,t:p.temp[k],w:p.speed[k],dir:p.direction[k]})).filter(p=>Number.isFinite(p.t));
 const cold=valid.filter(p=>p.t< -10),weights=cold.map(p=>Math.max(0,-10-p.t)),sum=weights.reduce((a,b)=>a+b,0);
 const center=sum?{lat:cold.reduce((s,p,i)=>s+p.lat*weights[i],0)/sum,lon:cold.reduce((s,p,i)=>s+p.lon*weights[i],0)/sum}:null;
 const min=valid.reduce((a,p)=>p.t<a.t?p:a,valid[0]||{t:NaN});
 const windPts=cold.filter(p=>Number.isFinite(p.w)&&Number.isFinite(p.dir));
 const u=mean(windPts.map(p=>-p.w*Math.sin(p.dir*Math.PI/180))),v=mean(windPts.map(p=>-p.w*Math.cos(p.dir*Math.PI/180)));
 return {min:min.t,max:Math.max(...valid.map(p=>p.t)),coldest:min,n:valid.length,a5:100*valid.filter(p=>p.t< -5).length/valid.length,a10:100*cold.length/valid.length,a15:100*valid.filter(p=>p.t< -15).length/valid.length,center,wind:mean(windPts.map(p=>p.w)),windDir:(Math.atan2(-u,-v)*180/Math.PI+360)%360,valid};
}
function render(){
 if(!times.length)return;const idx=Math.max(0,Math.min(times.length-1,Number($('pv850mapTime')?.value||$('pv500Time')?.value||0))),d=analyse(idx);
 $('pvx5ColdMin').textContent=fmt(d.min)+' °C';$('pvx5ColdMax').textContent=fmt(d.max)+' °C';
 $('pvx5ColdArea5').textContent=fmt(d.a5,0)+' %';$('pvx5ColdArea10').textContent=fmt(d.a10,0)+' %';$('pvx5ColdArea15').textContent=fmt(d.a15,0)+' %';
 $('pvx5ColdStamp').textContent='Platnost '+times[idx]+' UTC · '+d.n+' platných bodů z '+LAT.length*LON.length;
 const center=$('pvx5ColdCenter');if(center){
  const loc=d.center?'Těžiště pod −10 °C: '+fmt(d.center.lat,1)+'° s. š., '+fmt(Math.abs(d.center.lon),1)+'° '+(d.center.lon<0?'z. d.':'v. d.')+'.':'V této platnosti není bod pod −10 °C.';
  const wdir=Number.isFinite(d.windDir)?' Průměrný vítr v chladných bodech: '+fmt(d.wind,1)+' km/h, směr '+fmt(d.windDir,0)+'° (kam proudí).':'';
  center.textContent=loc+wdir+' Nejchladnější bod: '+fmt(d.coldest.lat,1)+'° s. š., '+fmt(Math.abs(d.coldest.lon),1)+'° '+(d.coldest.lon<0?'z. d.':'v. d.')+' ('+fmt(d.min,1)+' °C).';
 }
 drawMap(d);drawTrack(idx);
}
function drawMap(d){
 const c=$('pvx5ColdMap');if(!c)return;const g=c.getContext('2d'),w=c.width,h=c.height;g.clearRect(0,0,w,h);g.fillStyle='#f4f8fc';g.fillRect(0,0,w,h);
 const x=lon=>48+(lon+30)/70*(w-78),y=lat=>22+(80-lat)/40*(h-52);
 g.strokeStyle='#d6e1eb';g.fillStyle='#536779';g.font='13px Arial';
 for(let lon=-30;lon<=40;lon+=10){g.beginPath();g.moveTo(x(lon),18);g.lineTo(x(lon),h-30);g.stroke();g.fillText(lon+'°',x(lon)-10,h-10);}
 for(let lat=40;lat<=80;lat+=10){g.beginPath();g.moveTo(48,y(lat));g.lineTo(w-30,y(lat));g.stroke();g.fillText(lat+'°N',5,y(lat)+4);}
 d.valid.forEach(p=>{const px=x(p.lon),py=y(p.lat),r=p.t< -15?7:p.t< -10?6:p.t< -5?5:3;g.beginPath();g.arc(px,py,r,0,Math.PI*2);g.fillStyle=p.t< -15?'#244f9b':p.t< -10?'#3488c5':p.t< -5?'#83bddb':'#e6a36d';g.fill();g.strokeStyle='#31495d';g.lineWidth=.7;g.stroke();
  if(Number.isFinite(p.w)&&Number.isFinite(p.dir)&&p.w>=10){const toward=(p.dir+180)*Math.PI/180,len=Math.min(17,5+p.w/12),ex=px+Math.sin(toward)*len,ey=py-Math.cos(toward)*len;g.strokeStyle='#263b4f';g.lineWidth=1.3;g.beginPath();g.moveTo(px,py);g.lineTo(ex,ey);g.stroke();g.beginPath();g.moveTo(ex,ey);g.lineTo(ex-4*Math.cos(toward-.5),ey-4*Math.sin(toward-.5));g.moveTo(ex,ey);g.lineTo(ex-4*Math.cos(toward+.5),ey-4*Math.sin(toward+.5));g.stroke();}
 });
 if(d.center){g.beginPath();g.arc(x(d.center.lon),y(d.center.lat),10,0,Math.PI*2);g.strokeStyle='#b42318';g.lineWidth=3;g.stroke();}
 g.fillStyle='#20364a';g.font='bold 15px Arial';g.fillText('Studené body a směr proudění · 850 hPa',48,15);
}
function drawTrack(idx){
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
 const status=$('pvx5ColdStatus');if(status)status.textContent='Načítám teplotu a vítr 850 hPa pro 135 bodů…';
 try{
  const coords=LAT.flatMap(lat=>LON.map(lon=>({lat,lon}))),res=[];
  for(let i=0;i<coords.length;i+=45){const q=new URLSearchParams({latitude:coords.slice(i,i+45).map(p=>p.lat).join(','),longitude:coords.slice(i,i+45).map(p=>p.lon).join(','),hourly:fields.join(','),forecast_days:'3',timezone:'GMT',wind_speed_unit:'kmh'});const r=await fetch(API+'?'+q,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const a=await r.json();res.push(...(Array.isArray(a)?a:[a]));}
  times=res[0]?.hourly?.time;if(!Array.isArray(times)||!times.length||res.length!==coords.length)throw Error('Neúplná odpověď GFS.');
  for(const r of res)for(const f of fields)if(!Array.isArray(r.hourly?.[f])||r.hourly[f].length!==times.length)throw Error('Chybí pole '+f);
  cells=coords.map((p,i)=>({lat:p.lat,lon:p.lon,temp:res[i].hourly.temperature_850hPa,speed:res[i].hourly.wind_speed_850hPa,direction:res[i].hourly.wind_direction_850hPa}));
  track=times.map((_,k)=>analyse(k));
  if(status)status.innerHTML='<b class="good">Diagnostika studeného vzduchu načtena.</b> 135 bodů · '+times.length+' hodinových kroků · GFS 850 hPa.';
  render();
 }catch(e){if(status)status.innerHTML='<b class="warn">Diagnostiku se nepodařilo načíst:</b> '+String(e.message||e);}
}
const sel=$('pv850mapTime'),tab=$('pv500Time'),refresh=$('pv850mapRefresh');
if(sel)sel.addEventListener('change',render);if(tab)tab.addEventListener('change',render);if(refresh)refresh.addEventListener('click',load);load();
})();