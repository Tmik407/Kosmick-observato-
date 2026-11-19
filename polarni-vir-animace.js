(()=>{'use strict';
const $=id=>document.getElementById(id),levels=[10,30,50],colors={10:'#0878e8',30:'#e58a12',50:'#8b4bd6'};
const parse=async p=>{const r=await fetch(p+'?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(p+' HTTP '+r.status);return (await r.text()).trim().split(/\r?\n/).slice(1).map(s=>{const [date,value,fh]=s.split(',');return {date,v:Number(value),fh:Number(fh)};}).filter(x=>x.date&&Number.isFinite(x.v)&&Number.isFinite(x.fh)&&x.v!==-9999&&x.v!==-9999.0);};
const dateAdd=(d,n)=>{const x=new Date(d+'T00:00:00Z');x.setUTCDate(x.getUTCDate()+n);return x.toISOString().slice(0,10);};
let frames=[],idx=0,timer=null;
function draw(){const c=$('pvAnimCanvas');if(!c||!frames.length)return;const g=c.getContext('2d'),w=c.width,h=c.height,f=frames[idx],vals=f.levels;
g.clearRect(0,0,w,h);const bg=g.createLinearGradient(0,0,w,h);bg.addColorStop(0,'#f2f8ff');bg.addColorStop(.55,'#e5f1ff');bg.addColorStop(1,'#d8e7f5');g.fillStyle=bg;g.fillRect(0,0,w,h);
const cx=w*.34,cy=h*.52,R=Math.min(h*.39,w*.27),wind=vals.find(x=>x.l===10)?.u??0,temp=vals.find(x=>x.l===10)?.t??null;
g.save();g.beginPath();g.arc(cx,cy,R,0,Math.PI*2);g.clip();const ocean=g.createRadialGradient(cx,cy,5,cx,cy,R);ocean.addColorStop(0,'#d9f4ff');ocean.addColorStop(.55,'#a9d9f1');ocean.addColorStop(1,'#6eacd4');g.fillStyle=ocean;g.fillRect(cx-R,cy-R,R*2,R*2);
for(let k=1;k<=5;k++){g.beginPath();g.arc(cx,cy,R*k/5,0,Math.PI*2);g.strokeStyle='rgba(56,103,132,.24)';g.lineWidth=1.2;g.stroke();}
g.strokeStyle='rgba(56,103,132,.22)';g.setLineDash([5,7]);g.beginPath();g.moveTo(cx-R,cy);g.lineTo(cx+R,cy);g.moveTo(cx,cy-R);g.lineTo(cx,cy+R);g.stroke();g.setLineDash([]);
const heat=g.createRadialGradient(cx-R*.12,cy-R*.08,4,cx-R*.12,cy-R*.08,R*.92);heat.addColorStop(0,'rgba(38,115,230,.78)');heat.addColorStop(.28,'rgba(20,190,210,.58)');heat.addColorStop(.55,'rgba(255,205,55,.42)');heat.addColorStop(.78,'rgba(244,105,65,.28)');heat.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=heat;g.fillRect(cx-R,cy-R,R*2,R*2);
const strength=Math.max(.28,Math.min(1.15,Math.abs(wind)/28)),phase=idx*.055,asym=Math.max(-.28,Math.min(.28,wind/55));
for(let ring=0;ring<4;ring++){g.beginPath();for(let a=0;a<=Math.PI*2+.03;a+=.025){const wave=Math.sin(3*a+phase+ring*.4)*.10+Math.cos(2*a-phase)*asym*.22;const rr=R*(.25+ring*.16)*strength*(1+wave);const x=cx+rr*Math.cos(a),y=cy+rr*Math.sin(a);if(a===0)g.moveTo(x,y);else g.lineTo(x,y);}g.closePath();g.strokeStyle=['#075bd8','#00a6c7','#f0a21a','#a044d5'][ring];g.globalAlpha=.9-ring*.12;g.lineWidth=ring===0?3.5:2.2;g.stroke();}
g.globalAlpha=1;
for(let k=0;k<9;k++){const a=k*Math.PI*2/9+phase*.7,rr=R*(.55+(k%3)*.09),x=cx+rr*Math.cos(a),y=cy+rr*Math.sin(a),tx=-Math.sin(a),ty=Math.cos(a);g.strokeStyle='#174b85';g.lineWidth=2;g.beginPath();g.moveTo(x-tx*8,y-ty*8);g.lineTo(x+tx*8,y+ty*8);g.lineTo(x+tx*3-ty*6,y+ty*3+tx*6);g.moveTo(x+tx*8,y+ty*8);g.lineTo(x+tx*3+ty*6,y+ty*3-tx*6);g.stroke();}
g.restore();g.strokeStyle='#315f91';g.lineWidth=2;g.beginPath();g.arc(cx,cy,R,0,Math.PI*2);g.stroke();
g.textAlign='center';g.fillStyle='#18364b';g.font='bold 23px Arial';g.fillText('POLÁRNÍ PROJEKCE · SEVERNÍ PÓL',cx,30);g.fillStyle='#526b7d';g.font='13px Arial';g.fillText('Schematická struktura odvozená z časových řad · ne prostorová analýza',cx,h-15);
const bx=w*.66,by=52,pw=w*.30,ph=h-100;g.fillStyle='#fafdff';g.strokeStyle='#9dbbd4';g.lineWidth=1;g.beginPath();g.roundRect(bx,by,pw,ph,18);g.fill();g.stroke();
g.textAlign='left';g.fillStyle='#123b67';g.font='bold 22px Arial';g.fillText('STAV ATMOSFÉRY',bx+24,by+36);g.fillStyle=f.forecast?'#a65d13':'#147c58';g.font='bold 13px Arial';g.fillText(f.forecast?'PŘEDPOVĚĎ · GEOS FP':'ANALÝZA · NASA OZONE WATCH',bx+24,by+62);
g.fillStyle='#526b7d';g.font='13px Arial';g.fillText('Platnost UTC',bx+24,by+91);g.fillStyle='#17364c';g.font='bold 20px Arial';g.fillText(f.date,bx+24,by+117);
vals.forEach((v,i)=>{const y=by+160+i*82;g.fillStyle=colors[v.l];g.beginPath();g.roundRect(bx+20,y-24,pw-40,68,11);g.fill();g.fillStyle='#fff';g.font='bold 17px Arial';g.fillText(v.l+' hPa',bx+34,y+1);g.font='14px Arial';g.fillText('U60  '+v.u.toFixed(2)+' m/s',bx+126,y+1);g.fillText('Teplota  '+(v.t===null?'—':v.t.toFixed(1)+' °C'),bx+126,y+23);});
const yb=by+ph-35;g.fillStyle='#315b7c';g.font='12px Arial';g.fillText('Barevné vrstvy: 10 / 30 / 50 hPa · U60 a teplota',bx+24,yb);
g.fillStyle='#17364c';g.font='bold 15px Arial';g.fillText('Časový krok  '+(idx+1)+' / '+frames.length,bx+24,yb-30);
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