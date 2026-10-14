// Matchd service worker: makes the site installable and usable offline.
// Pages and job data: network first (always fresh when online), cached copy when offline.
// Fonts and icons: cache first. The AI server is never cached.
const VERSION = "__BUILD__";
const SHELL = "jobbsvep-shell-" + VERSION;
const DATA = "jobbsvep-data";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(["./", "./en/", "./manifest.webmanifest", "./icons/icon-192.png"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("jobbsvep-shell-") && k !== SHELL).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    if (request.mode === "navigate") return (await caches.open(SHELL)).match("./");
    throw error;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(SHELL);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;
  if (request.mode === "navigate") return event.respondWith(networkFirst(request, SHELL));
  if (sameOrigin && (url.pathname.includes("/data/") || url.pathname.endsWith("pois.json"))) return event.respondWith(networkFirst(request, DATA));
  if (sameOrigin && url.pathname.includes("/icons/")) return event.respondWith(cacheFirst(request));
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") return event.respondWith(cacheFirst(request));
  // everything else, including the AI server, goes straight to the network
});
