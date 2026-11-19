(()=>{'use strict';
const $=id=>document.getElementById(id);
const root='/Kosmick-observato-/data/noaa-gfs/';
const files={10:'gfs_t10_nh_f00.png',30:'gfs_t30_nh_f00.png',50:'gfs_t50_nh_f00.png'};
const level=$('gfsLevel'),img=$('gfsArchiveImage'),status=$('gfsMapStatus'),stamp=$('gfsArchiveTime');
if(!level||!img||!status)return;
let request=0;
async function load(){
 const id=++request,l=level.value,file=files[l];
 status.textContent='Ověřuji dostupnost archivované mapy NOAA GFS · '+l+' hPa…';
 img.alt='Originální mapa NOAA GFS pro severní polokouli, tlaková hladina '+l+' hPa';
 img.onerror=()=>{if(id===request)status.innerHTML='<b class="warn">Mapa NOAA se nepodařila načíst.</b> Archivovaný soubor '+file+' není momentálně dostupný.';};
 img.onload=()=>{if(id===request)status.innerHTML='<b class="good">Mapa NOAA GFS je načtena.</b> Hladina '+l+' hPa · severní polokoule · analýza F00. Zobrazen je originální obrazový produkt NOAA.';};
 img.src=root+file+'?v='+Date.now();
 try{
  const r=await fetch(root+'meta.json?v='+Date.now(),{cache:'no-store'});
  if(!r.ok)throw Error('metadata HTTP '+r.status);
  const m=await r.json();
  const item=m.files?.[l];
  if(!item||item.file!==file)throw Error('metadata neodpovídají vybrané hladině');
  if(stamp)stamp.textContent=m.retrieved_utc?new Date(m.retrieved_utc).toLocaleString('cs-CZ',{timeZone:'UTC'})+' UTC':'neuvedeno';
  if(id===request)status.innerHTML='<b class="good">Archiv NOAA GFS je dostupný.</b> '+l+' hPa · '+(m.source||'NOAA CPC')+' · pořízeno '+(m.retrieved_utc||'čas neuveden')+'.';
 }catch(e){if(id===request)status.innerHTML='<b class="warn">Metadata archivu nejsou dostupná.</b> '+String(e.message||e)+'. Obraz mapy se načítá samostatně.';}
}
level.addEventListener('change',load);
const refresh=$('gfsMapRefresh');if(refresh)refresh.addEventListener('click',load);
load();
})();