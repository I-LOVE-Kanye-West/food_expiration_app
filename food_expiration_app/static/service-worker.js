// Service Workerのインストールイベント
self.addEventListener('install', (event) => {
    console.log('Service Worker インストール中');
    
    // 即座にアクティブ化して、古いバージョンがすぐに適用されるようにする
    self.skipWaiting();
});

// Service Workerのアクティベートイベント
self.addEventListener('activate', (event) => {
    console.log('Service Worker アクティブ化中');
    
    // 新しいクライアントに即座に適用するため、既存のクライアントに対して管理を行う
    event.waitUntil(clients.claim());
});

// Push通知を受信した際のイベント
self.addEventListener('push', (event) => {
    console.log('Push通知を受信しました:', event);

    // 通知のデフォルト内容を設定
    let notificationData = {
        title: "通知",
        body: "詳細を確認してください。",
        icon: '/static/images/notification-icon.png',
        badge: '/static/images/notification-badge.png',
        url: '/' // 通知クリック時に遷移するURL
    };

    // Push通知データをJSON形式で上書き
    try {
        if (event.data) {
            notificationData = event.data.json(); // データがある場合はJSONとして解析
        }
    } catch (error) {
        console.error('Push通知のデータ解析に失敗しました:', error);
    }

    // 通知オプションの設定
    const options = {
        body: notificationData.body,
        icon: notificationData.icon,
        badge: notificationData.badge,
        data: notificationData.url // 通知クリック時の遷移先URL
    };

    // 通知を表示
    event.waitUntil(
        self.registration.showNotification(notificationData.title, options)
    );
});

// 通知がクリックされた際のイベント
self.addEventListener('notificationclick', (event) => {
    console.log('通知がクリックされました:', event);

    // 通知を閉じる
    event.notification.close();

    // 通知に設定されたURL、もしくはデフォルトURL ('/')
    const urlToOpen = event.notification.data || '/';

    // 既存のウィンドウでURLが一致するものにフォーカスを当てる
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus(); // 一致するウィンドウにフォーカス
                }
            }
            // 一致するウィンドウがない場合、新しいウィンドウを開く
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});
