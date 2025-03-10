const CACHE_NAME = "membership-site-cache-v1";
const urlsToCache = [
  "/",
  "/index.html",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Opened cache");
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
