(()=>{'use strict';
const $=id=>document.getElementById(id);
const root='/Kosmick-observato-/data/noaa-gfs/';
const files={10:'gfs_t10_nh_f00.png',30:'gfs_t30_nh_f00.png',50:'gfs_t50_nh_f00.png'};
const level=$('gfsLevel'),img=$('gfsArchiveImage'),status=$('gfsMapStatus'),stamp=$('gfsArchiveTime');
if(!level||!img||!status)return;
let request=0;
async function load(){
 const id=++request,l=level.value,file=files[l];
 let imageState='loading',metadataState='loading',metadata=null;
 const renderStatus=()=>{
  if(id!==request)return;
  if(imageState==='error'){
   status.innerHTML='<b class="warn">Mapa NOAA se nepodařila načíst.</b> Archivovaný soubor '+file+' není momentálně dostupný.';
  }else if(metadataState==='error'){
   status.innerHTML=imageState==='loaded'
    ?'<b class="warn">Obraz mapy je načten, ale metadata archivu nejsou dostupná.</b> Nelze ověřit čas a původ poslední aktualizace.'
    :'<b class="warn">Metadata archivu nejsou dostupná.</b> Obraz mapy se načítá samostatně.';
  }else if(imageState==='loaded'&&metadataState==='loaded'){
   status.innerHTML='<b class="good">Mapa NOAA GFS je načtena a ověřena.</b> '+l+' hPa · '+(metadata.source||'NOAA CPC')+' · analýza F00.';
  }else{
   status.textContent='Ověřuji archivovanou mapu NOAA GFS · '+l+' hPa…';
  }
 };
 status.textContent='Načítám archivovanou mapu NOAA GFS · '+l+' hPa…';
 img.alt='Originální mapa NOAA GFS pro severní polokouli, tlaková hladina '+l+' hPa';
 img.onload=()=>{if(id===request){imageState='loaded';renderStatus();}};
 img.onerror=()=>{if(id===request){imageState='error';renderStatus();}};
 img.src=root+file+'?v='+Date.now();
 try{
  const r=await fetch(root+'meta.json?v='+Date.now(),{cache:'no-store'});
  if(!r.ok)throw Error('metadata HTTP '+r.status);
  const m=await r.json(),item=m.files?.[l];
  if(!item||item.file!==file)throw Error('metadata neodpovídají vybrané hladině');
  metadata=m;metadataState='loaded';
  if(stamp)stamp.textContent=m.retrieved_utc?new Date(m.retrieved_utc).toLocaleString('cs-CZ',{timeZone:'UTC'})+' UTC':'neuvedeno';
 }catch(e){metadataState='error';}
 renderStatus();
}
level.addEventListener('change',load);
const refresh=$('gfsMapRefresh');if(refresh)refresh.addEventListener('click',load);
load();
})();