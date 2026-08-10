// ==========================================
// 🔔 第一部分：Firebase 雲端推播 (FCM) 背景攔截邏輯
// ==========================================

// 1. 匯入 Firebase 函式庫 (Service Worker 專用相容版)
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js');

// 2. 初始化 Firebase (這裡的設定檔與你 index.html 中的一模一樣)
firebase.initializeApp({
  apiKey: "AIzaSyDSFt_TgniiOuv3_y-A62hSZ_q-cxGx90U",
  authDomain: "calendar-400ce.firebaseapp.com",
  projectId: "calendar-400ce",
  storageBucket: "calendar-400ce.firebasestorage.app",
  messagingSenderId: "965942149317",
  appId: "1:965942149317:web:ccef715420c0f5a12e70ac"
});

const messaging = firebase.messaging();

// 3. 攔截背景推播訊息並顯示成原生通知
messaging.onBackgroundMessage((payload) => {
  console.log('📥 收到背景推播訊號:', payload);
  
  const notificationTitle = payload.notification.title || '⏰ 任務提醒';
  const notificationOptions = {
    body: payload.notification.body,
    icon: 'icon-192.png', // 顯示 APP 的圖示
    badge: 'icon-192.png',
    data: payload.data // 預留：未來可夾帶額外資料
  };

  // 呼叫系統底層，彈出通知卡片
  self.registration.showNotification(notificationTitle, notificationOptions);
});

// 4. 處理使用者「點擊」通知卡片的行為 (點擊後自動打開 APP)
self.addEventListener('notificationclick', (event) => {
  event.notification.close(); // 先把通知卡片收起來
  
  // 👇 針對您的 GitHub Pages 專案目錄進行設定
  const targetUrl = '/calendar/'; 

  // 尋找是否已經有打開的 APP 視窗，有的話直接切換過去，沒有的話開新視窗
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((windowClients) => {
      for (let i = 0; i < windowClients.length; i++) {
        let client = windowClients[i];
        // 💡 修正 1：用 includes 判斷目前的網址是否包含您的專案路徑
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      // 💡 修正 2：如果沒有開啟的視窗，強制開啟子目錄路徑
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// ==========================================
// 📦 第二部分：原本的 PWA 離線快取守衛 (保持不變，僅升級版號)
// ==========================================

// 👇 注意：版號升級到 v3，強制手機更新最新的 sw.js
const CACHE_NAME = 'todo-pwa-v7'; 
const urlsToCache = [
  './',
  './index.html',
  './manifest.json'
];

self.addEventListener('install', event => {
  self.skipWaiting(); 
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('🧹 清除舊快取:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) return response;
        return fetch(event.request);
      })
  );
});