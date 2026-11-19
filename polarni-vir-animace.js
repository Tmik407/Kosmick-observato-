(()=>{'use strict';
const $=id=>document.getElementById(id),levels=[10,30,50],colors={10:'#087fa5',30:'#c07820',50:'#7652ad'};
const parse=async p=>{const r=await fetch(p+'?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(p+' HTTP '+r.status);return (await r.text()).trim().split(/\r?\n/).slice(1).map(s=>{const [date,value,fh]=s.split(',');return {date,v:Number(value),fh:Number(fh)};}).filter(x=>x.date&&Number.isFinite(x.v)&&Number.isFinite(x.fh)&&x.v!==-9999&&x.v!==-9999.0);};
const dateAdd=(d,n)=>{const x=new Date(d+'T00:00:00Z');x.setUTCDate(x.getUTCDate()+n);return x.toISOString().slice(0,10);};
let frames=[],idx=0,timer=null;
function draw(){const c=$('pvAnimCanvas');if(!c||!frames.length)return;const g=c.getContext('2d'),w=c.width,h=c.height,f=frames[idx];g.clearRect(0,0,w,h);g.fillStyle='#f7fbff';g.fillRect(0,0,w,h);
const cx=w*.36,cy=h*.52,R=Math.min(h*.39,w*.27);g.strokeStyle='#d6e2ec';g.lineWidth=1;for(let k=1;k<=4;k++){g.beginPath();g.arc(cx,cy,R*k/4,0,Math.PI*2);g.stroke();}
g.strokeStyle='#a9bfce';g.setLineDash([5,5]);g.beginPath();g.moveTo(cx-R,cy);g.lineTo(cx+R,cy);g.moveTo(cx,cy-R);g.lineTo(cx,cy+R);g.stroke();g.setLineDash([]);
const vals=f.levels,wind=vals.find(x=>x.l===10)?.u??0,temp=vals.find(x=>x.l===10)?.t??null;
const strength=Math.max(.25,Math.min(1.25,Math.abs(wind)/35)),shift=Math.max(-.22,Math.min(.22,wind/90));
g.save();g.translate(cx+shift*R,cy);g.rotate(idx*.08);g.strokeStyle='#087fa5';g.lineWidth=4;g.globalAlpha=.82;g.beginPath();for(let a=0;a<Math.PI*5;a+=.035){const rr=R*.08+R*.78*(a/(Math.PI*5))*strength;const x=rr*Math.cos(a),y=rr*Math.sin(a);if(a===0)g.moveTo(x,y);else g.lineTo(x,y);}g.stroke();g.restore();
g.fillStyle='#172b3f';g.font='bold 22px Arial';g.textAlign='center';g.fillText('SEVERNÍ POLÁRNÍ VÍR',cx,30);g.font='13px Arial';g.fillStyle='#5b6d7e';g.fillText('schematická animace · nikoli skutečná mapa',cx,h-14);
const bx=w*.68,by=70;g.textAlign='left';g.fillStyle='#172b3f';g.font='bold 20px Arial';g.fillText(f.date,bx,by);g.font='14px Arial';g.fillStyle='#9a5700';g.fillText(f.forecast?'PŘEDPOVĚĎ · NASA GEOS FP':'ANALÝZA',bx,by+25);
vals.forEach((v,i)=>{const y=by+75+i*76;g.fillStyle=colors[v.l];g.font='bold 17px Arial';g.fillText(v.l+' hPa',bx,y);g.fillStyle='#172b3f';g.font='15px Arial';g.fillText('U60 '+v.u.toFixed(2)+' m/s',bx+85,y);g.fillText('T '+(v.t===null?'—':v.t.toFixed(1)+' °C'),bx+85,y+24);});
g.fillStyle='#5b6d7e';g.font='13px Arial';g.fillText('Vítr 10 hPa: '+wind.toFixed(2)+' m/s',bx,by+315);g.fillText('Teplota 10 hPa: '+(temp===null?'—':temp.toFixed(1)+' °C'),bx,by+338);
$('pvAnimDate').textContent=f.date+' · '+(f.forecast?'předpovědní krok':'analýza');$('pvAnimStep').textContent=(idx+1)+' / '+frames.length;$('pvAnimSlider').value=idx;
}
function render(){const slider=$('pvAnimSlider');slider.max=frames.length-1;slider.value=0;idx=0;draw();$('pvAnimStatus').innerHTML='<b class="good">Animace připravena.</b> '+frames.length+' společných časových kroků; poslední krok '+frames[frames.length-1].date+'.';}
async function init(){try{$('pvAnimStatus').textContent='Načítám NASA Ozone Watch: vítr a teplotu na 10/30/50 hPa…';
const all=await Promise.all(levels.map(async l=>{const [u,t]=await Promise.all([parse('./data/nasa-gsfc/u60_'+l+'hpa_60n_ozonewatch.csv'),parse('./data/nasa-gsfc/tcap_'+l+'hpa_60_90n_ozonewatch.csv')]);return {l,u,t};}));
const byDate=new Map();for(const q of all){const tm=new Map(q.t.map(x=>[x.date,x]));for(const u of q.u){const t=tm.get(u.date);if(!t||u.fh!==t.fh)continue;const a=byDate.get(u.date)||{date:u.date,levels:[],forecast:u.fh>0};a.levels.push({l:q.l,u:u.v,t:t.v-273.15,fh:u.fh});a.forecast=a.forecast||u.fh>0;byDate.set(u.date,a);}}
frames=[...byDate.values()].filter(f=>f.levels.length===3).sort((a,b)=>a.date.localeCompare(b.date));
if(!frames.length)throw Error('Nenalezeny společné platné záznamy pro všechny tři hladiny.');
const forecast=frames.filter(f=>f.forecast);const analysis=frames.filter(f=>!f.forecast);frames=[...analysis.slice(-7),...forecast].filter((f,i,a)=>i===0||f.date!==a[i-1].date);
if(!forecast.length)$('pvAnimStatus').textContent='NASA Ozone Watch zatím neposkytuje společné předpovědní kroky; zobrazuji posledních 7 analýz.';
render();$('pvAnimForecastInfo').textContent=forecast.length?'Předpověď: '+forecast[0].date+' až '+forecast[forecast.length-1].date+' · '+forecast.length+' kroků.':'Předpovědní data nejsou aktuálně k dispozici.';
}catch(e){$('pvAnimStatus').innerHTML='<b class="warn">Animaci nelze načíst:</b> '+e.message;}}
$('pvAnimPlay').addEventListener('click',()=>{if(timer){clearInterval(timer);timer=null;$('pvAnimPlay').textContent='▶ Přehrát';return;}if(idx>=frames.length-1)idx=0;$('pvAnimPlay').textContent='Ⅱ Pozastavit';timer=setInterval(()=>{idx++;if(idx>=frames.length){clearInterval(timer);timer=null;$('pvAnimPlay').textContent='▶ Přehrát';idx=frames.length-1;}draw();},850);});
$('pvAnimSlider').addEventListener('input',e=>{idx=Number(e.target.value);draw();});
$('pvAnimReset').addEventListener('click',()=>{if(timer){clearInterval(timer);timer=null;}$('pvAnimPlay').textContent='▶ Přehrát';idx=0;draw();});
init();
})();