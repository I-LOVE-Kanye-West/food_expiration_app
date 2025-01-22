const publicKey = '": "BKX3d2SLf6e93syXaeuVHdCO82WnzHczZZVm4_pJziQVJPTY8XlBKzDyDLyUnsVpPd5J1DnpLxxurHr04O5MyA8';

document.addEventListener('DOMContentLoaded', () => {
    // Push通知機能とハンバーガーメニューを初期化
    setupPushNotifications();
    setupHamburgerMenu();
});

/**
 * Push通知のセットアップ
 */
async function setupPushNotifications() {
    const subscribeButton = document.getElementById('subscribeButton');
    if (!subscribeButton) return; // ボタンが存在しない場合は何もしない

    subscribeButton.addEventListener('click', async () => {
        try {
            // サービスワーカーのサポートを確認
            if (!('serviceWorker' in navigator)) {
                alert('このブラウザはサービスワーカーに対応していません。');
                return;
            }

            // サービスワーカーが準備完了するのを待機
            const registration = await navigator.serviceWorker.ready;
            console.log('Service Worker is ready:', registration);

            // Push通知の購読
            const subscription = await subscribeToPushNotifications(registration);

            // サーバーに購読情報を送信
            const response = await sendSubscriptionToServer(subscription);

            if (response.ok) {
                alert('通知が正常に登録されました！');
            } else {
                const errorMessage = await response.text();
                console.error('Failed to register subscription:', errorMessage);
                alert('通知登録に失敗しました。サーバーを確認してください。');
            }
        } catch (error) {
            console.error('Error during notification subscription:', error);
            alert('通知登録中にエラーが発生しました。');
        }
    });
}

/**
 * Push通知の購読
 * @param {ServiceWorkerRegistration} registration - サービスワーカーの登録情報
 * @returns {Promise<PushSubscription>} - Push通知の購読情報
 */
async function subscribeToPushNotifications(registration) {
    return registration.pushManager.subscribe({
        userVisibleOnly: true, // ユーザーが通知を確認できるようにする
        applicationServerKey: convertBase64ToUint8Array(publicKey), // VAPID公開鍵
    });
}

/**
 * サーバーに購読情報を送信
 * @param {PushSubscription} subscription - Push通知の購読情報
 * @returns {Promise<Response>} - サーバーからのレスポンス
 */
async function sendSubscriptionToServer(subscription) {
    return fetch('/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription),
    });
}

/**
 * ハンバーガーメニューのセットアップ
 */
function setupHamburgerMenu() {
    const menuToggle = document.querySelector('.menu-toggle');
    const nav = document.querySelector('nav');
    if (!menuToggle || !nav) return; // メニューが存在しない場合は何もしない

    menuToggle.addEventListener('click', () => {
        nav.classList.toggle('active'); // ナビゲーションメニューの表示/非表示を切り替え
    });
}

/**
 * Base64エンコードされた文字列をUint8Arrayに変換
 * @param {string} base64String - Base64エンコードされた文字列
 * @returns {Uint8Array} - Uint8Array形式のデータ
 */
function convertBase64ToUint8Array(base64String) {
    // Base64のパディング処理と変換
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
}
