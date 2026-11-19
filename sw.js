/* Kosmická observatoř X-5 – PWA service worker */
const CACHE_NAME="x5-pwa-shell-v2";
const SHELL=["./","./index.html","./offline.html","./manifest.webmanifest","./icon.svg"];
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
   if(response&&response.ok){const copy=response.clone();caches.open(CACHE_NAME).then(cache=>cache.put("./index.html",copy));}
   return response;
  }).catch(async()=>{
   const cached=await caches.match("./index.html")||await caches.match("./");
   return cached||await caches.match("./offline.html");
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
