const CACHE = "aierp-v2";
const PRECACHE = ["/manifest.json", "/icon-192.png", "/icon-512.png"];
const DISABLE_IN_LOCAL_DEV = ["localhost", "127.0.0.1", "0.0.0.0"].includes(self.location.hostname);

self.addEventListener("install", (e) => {
  if (DISABLE_IN_LOCAL_DEV) {
    e.waitUntil(
      caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
        .then(() => self.registration.unregister())
    );
    self.skipWaiting();
    return;
  }

  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  if (DISABLE_IN_LOCAL_DEV) {
    e.waitUntil(self.clients.claim());
    return;
  }

  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  if (DISABLE_IN_LOCAL_DEV) {
    return;
  }

  if (e.request.method !== "GET") {
    return;
  }

  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  // Never cache API and Vite dev assets.
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/@vite/") ||
    url.pathname.startsWith("/@fs/") ||
    url.pathname.startsWith("/src/") ||
    url.pathname.startsWith("/node_modules/")
  ) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Keep HTML navigations fresh; fallback to cache when offline.
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        .then((resp) => {
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE).then((cache) => cache.put(e.request, clone));
          }
          return resp;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // Static assets: cache-first with background refresh.
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const networkPromise = fetch(e.request)
        .then((resp) => {
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE).then((cache) => cache.put(e.request, clone));
          }
          return resp;
        })
        .catch(() => undefined);

      return cached || networkPromise;
    })
  );
});
