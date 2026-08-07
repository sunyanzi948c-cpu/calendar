const CACHE_NAME = 'todo-pwa-v2';
const urlsToCache = [
  './',
  './index.html',
  './manifest.json'
];

// 安裝 Service Worker 並快取基本檔案
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// 攔截網路請求，若有快取則優先使用快取
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response; // 找到快取，直接回傳
        }
        return fetch(event.request); // 沒有快取，則透過網路抓取
      })
  );
});