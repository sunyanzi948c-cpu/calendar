// 👇 注意這裡：把 v1 改成了 v2！未來如果有大更新，就改成 v3、v4...
const CACHE_NAME = 'todo-pwa-v2'; 
const urlsToCache = [
  './',
  './index.html',
  './manifest.json'
];

// 安裝並強制立刻接管
self.addEventListener('install', event => {
  self.skipWaiting(); 
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// 👇 新增這段：啟動時，自動把舊版本 (v1) 的快取當垃圾清掉
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('清除舊快取:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// 攔截請求
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});