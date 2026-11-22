(()=>{'use strict';
const URL='./data/polar-vortex/latest.json', LEVELS=[10,30,50], $=id=>document.getElementById(id);
const fmt=(v,d=2)=>Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
const colors={10:'#087fa5',30:'#a85b12',50:'#6941a5'};
function ringMeans(points,values){const bins=new Map();points.forEach((p,i)=>{if(!Number.isFinite(values[i]))return;const k=p.lat;const a=bins.get(k)||[];a.push(values[i]);bins.set(k,a);});for(const [k,a] of bins)bins.set(k,a.reduce((s,v)=>s+v,0)/a.length);return bins;}
function geometry(data,level,step){
 const key='geopotential_height_'+level+'hPa', vals=data.rows.map(r=>r.hourly?.[key]?.[step]), means=ringMeans(data.points,vals);
 const pts=[];data.points.forEach((p,i)=>{const z=vals[i],m=means.get(p.lat);if(!Number.isFinite(z)||!Number.isFinite(m))return;const an=m-z,w=Math.max(0,an)*Math.cos(p.lat*Math.PI/180);if(w>0){const lon=p.lon*Math.PI/180,lat=p.lat*Math.PI/180;pts.push({x:Math.cos(lat)*Math.sin(lon),y:-Math.cos(lat)*Math.cos(lon),w,lat:p.lat,lon:p.lon,an});}});
 const total=pts.reduce((s,p)=>s+p.w,0);if(!total)return null;
 const mx=pts.reduce((s,p)=>s+p.w*p.x,0)/total,my=pts.reduce((s,p)=>s+p.w*p.y,0)/total;
 let xx=0,yy=0,xy=0;pts.forEach(p=>{const x=p.x-mx,y=p.y-my;xx+=p.w*x*x;yy+=p.w*y*y;xy+=p.w*x*y;});xx/=total;yy/=total;xy/=total;
 const tr=xx+yy,disc=Math.sqrt(Math.max(0,(xx-yy)**2+4*xy*xy)),l1=(tr+disc)/2,l2=(tr-disc)/2;
 const ratio=l2>0?Math.sqrt(l1/l2):null;
 const angle=.5*Math.atan2(2*xy,xx-yy)*180/Math.PI;
 const centerLat=Math.atan2(-my,Math.hypot(mx,my))*180/Math.PI,centerLon=(Math.atan2(mx,-my)*180/Math.PI+360)%360;
 return {ratio,angle,centerLat,centerLon,energy:total/pts.length,points:pts.length};
}
function render(data){
 const n=data.times.length,idx=n-1,body=$('pvx5AdvancedBody');let rows=[];
 LEVELS.forEach(level=>{const g=geometry(data,level,idx);rows.push({level,g});});
 if(body)body.innerHTML=rows.map(({level,g})=>'<tr><td><b>'+level+' hPa</b></td><td>'+(g?fmt(g.ratio,2):'—')+'</td><td>'+(g?fmt(g.centerLat,1)+'° N / '+fmt(g.centerLon,1)+'° E':'—')+'</td><td>'+(g?fmt(g.angle,0)+'°':'—')+'</td><td>'+(g?g.points+'/40':'—')+'</td></tr>').join('');
 const time=$('pvx5AdvancedTime');if(time)time.textContent='Platnost posledního kroku: '+data.times[idx]+' UTC · cyklus '+(data.cycle_utc||'neuveden');
 const trends=LEVELS.map(level=>{const a=geometry(data,level,0),b=geometry(data,level,Math.floor((n-1)/2)),c=geometry(data,level,idx);return {level,a,b,c};});
 const trendBody=$('pvx5TrendBody');if(trendBody)trendBody.innerHTML=trends.map(x=>'<tr><td>'+x.level+' hPa</td><td>'+fmt(x.a?.ratio,2)+'</td><td>'+fmt(x.b?.ratio,2)+'</td><td>'+fmt(x.c?.ratio,2)+'</td><td>'+(x.a&&x.c&&x.c.ratio>x.a.ratio?'protažení roste':x.a&&x.c?'protažení klesá / stabilní':'nedostatek dat')+'</td></tr>').join('');
 const signal=$('pvx5Signal');if(signal){const valid=rows.filter(x=>x.g);const high=valid.some(x=>x.g.ratio>=2);signal.innerHTML='<b>Geometrický indikátor:</b> '+(high?'výrazná eliptická deformace v hrubém vzorkování':'bez průkazu výrazné eliptické deformace v hrubém vzorkování')+'. Poměr os je diagnostika rozložení vzorkovaných záporných geopotenciálních anomálií, nikoli oficiální klasifikace rozdělení víru.';}
 const down=$('pvx5Downward');if(down){const g10=trends.find(x=>x.level===10),g30=trends.find(x=>x.level===30),g50=trends.find(x=>x.level===50);down.innerHTML='<b>Vertikální souběh:</b> '+(g10?.a&&g10?.c&&g30?.a&&g30?.c&&g50?.a&&g50?.c?'Srovnání geometrie je dostupné na všech třech hladinách. Z pouhých 17 kroků do 24. 11. nelze potvrdit sestupnou propagaci; sledujeme pouze souběžnou změnu.':'Nedostatečná společná data na všech hladinách.')+'<br><b>Riziko pro Evropu:</b> nelze z těchto stratosférických dat převést na pravděpodobnost mrazu či sněžení. K tomu je nutná návazná předpověď troposféry (zejména 500 hPa, tlak u země a ansámbl).';}
 const status=$('pvx5AdvancedStatus');if(status)status.innerHTML='<b class="good">Pokročilá diagnostika dokončena.</b> '+data.points.length+' prostorových bodů · '+n+' časových kroků. Nízké prostorové rozlišení je výslovně zohledněno.';
}
async function load(){const s=$('pvx5AdvancedStatus');if(s)s.textContent='Načítám společný archiv NOAA GFS…';try{const r=await fetch(URL+'?advanced='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();if(!Array.isArray(d.points)||!Array.isArray(d.rows)||!Array.isArray(d.times)||d.points.length!==40)throw Error('Neplatná struktura nebo počet bodů archivu.');for(const l of LEVELS)if(!d.rows.every(x=>Array.isArray(x.hourly?.['geopotential_height_'+l+'hPa'])&&x.hourly['geopotential_height_'+l+'hPa'].length===d.times.length))throw Error('Chybí geopotenciál na '+l+' hPa.');render(d);}catch(e){if(s)s.innerHTML='<b class="warn">Pokročilou diagnostiku nelze vypočítat:</b> '+e.message;}}
const b=$('pvx5AdvancedRefresh');if(b)b.addEventListener('click',load);load();
})();