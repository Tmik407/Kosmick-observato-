/* Kosmická observatoř X-5 – PWA service worker */
const CACHE_NAME="x5-pwa-shell-v60";
const SHELL=["./","./index.html","./polar-vortex-3d.html","./polarni-vir.html","./offline.html","./manifest.webmanifest","./polarni-vir.webmanifest","./icon.svg","./polarni-vir-animace.js","./gfs-polarni-animace.js","./gfs-vortex-comparison.js","./gfs-polarni-3d.js","./data/polar-vortex/latest.json","./data/polar-vortex-10hpa.json","./data/polar-vortex-history.json","./data/noaa-gfs/meta.json","./polar-vortex-shared-data.js","./polar-vortex-troposphere.js","./polar-vortex-vertical.js","./polar-vortex-advanced.js","./polar-vortex-troposphere.js","./polar-vortex-map500.js","./polar-vortex-map850.js","./polar-vortex-cold-air.js","./polar-vortex-vertical.js"];
self.addEventListener("install",event=>{
 event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener("activate",event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith("x5-pwa-")&&key!==CACHE_NAME).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener("fetch",event=>{
 const request=event.request;
 if(request.method!=="GET")return;
 const url=new URL(request.url);
 if(url.origin!==self.location.origin)return; // živá NOAA/ACE/GIRO data vždy jdou přímo do sítě
 if(request.mode==="navigate"){
  event.respondWith(fetch(request).then(response=>{
   if(response&&response.ok){const copy=response.clone();caches.open(CACHE_NAME).then(cache=>cache.put(request,copy));}
   return response;
  }).catch(async()=>{
   const cached=await caches.match(request);
   if(cached)return cached;
   if(url.pathname.endsWith("/polarni-vir.html"))return await caches.match("./polarni-vir.html")||await caches.match("./offline.html");
   return await caches.match("./index.html")||await caches.match("./")||await caches.match("./offline.html");
  }));
  return;
 }
 if(url.pathname.endsWith("/data/polar-vortex-10hpa.json")||url.pathname.endsWith("/data/polar-vortex-history.json")){
  event.respondWith(caches.open(CACHE_NAME).then(async cache=>{
   const key=new Request(url.origin+url.pathname);
   const cached=await cache.match(key);
   const refresh=fetch(request).then(response=>{
    if(response&&response.ok)cache.put(key,response.clone());
    return response;
   });
   if(cached){event.waitUntil(refresh.catch(()=>{}));return cached;}
   return refresh;
  }));
  return;
 }
 if(url.pathname.endsWith("/data/polar-vortex/latest.json")){
  event.respondWith(caches.open(CACHE_NAME).then(async cache=>{
   const cached=await cache.match(request);
   const refresh=fetch(request).then(response=>{
    if(response&&response.ok)cache.put(request,response.clone());
    return response;
   });
   if(cached){event.waitUntil(refresh.catch(()=>{}));return cached;}
   return refresh;
  }));
  return;
 }
 if(SHELL.some(path=>new URL(path,self.registration.scope).pathname===url.pathname)){
  event.respondWith(caches.match(request).then(cached=>cached||fetch(request).then(response=>{
   if(response&&response.ok){const copy=response.clone();caches.open(CACHE_NAME).then(cache=>cache.put(request,copy));}
   return response;
  })));
 }
});
