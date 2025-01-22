// サブスクライブボタンのクリックイベントリスナーを設定
document.getElementById('subscribe-button').addEventListener('click', function() {
    // 通知とサービスワーカーのサポート確認
    if ('Notification' in window && 'serviceWorker' in navigator) {
        // サービスワーカーの登録
        navigator.serviceWorker.register('/service-worker.js')
            .then(function(registration) {
                console.log('Service Workerが正常に登録されました:', registration);

                // VAPID公開鍵のBase64url形式をUint8Arrayに変換
                const applicationServerKey = convertBase64ToUint8Array(
                    'BKX3d2SLf6e93syXaeuVHdCO82WnzHczZZVm4_pJziQVJPTY8XlBKzDyDLyUnsVpPd5J1DnpLxxurHr04O5MyA8'
                );

                // Push通知の購読
                return registration.pushManager.subscribe({
                    userVisibleOnly: true, // ユーザーが通知を表示できるようにする
                    applicationServerKey: applicationServerKey // VAPID公開鍵を指定
                });
            })
            .then(function(subscription) {
                console.log('Push通知の購読が作成されました:', subscription);

                // サーバーに購読情報を送信
                return fetch('/subscribe', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(subscription) // 購読情報をJSON形式で送信
                });
            })
            .then(function(response) {
                // 購読成功時の処理
                if (response.ok) {
                    alert('通知の購読が完了しました！');
                } else {
                    console.error('サーバーエラー:', response.statusText);
                    alert('通知の購読に失敗しました。');
                }
            })
            .catch(function(error) {
                // エラー処理
                console.error('通知購読中にエラーが発生しました:', error);
                alert('通知購読中にエラーが発生しました。');
            });
    } else {
        // サポートしていない場合のエラーメッセージ
        alert('このブラウザは通知やサービスワーカーをサポートしていません。');
    }
});

/**
 * Base64urlエンコードされた公開鍵をUint8Arrayに変換する関数
 * @param {string} base64urlString - Base64url形式の公開鍵
 * @returns {Uint8Array} - Uint8Array形式に変換されたデータ
 */
function convertBase64ToUint8Array(base64urlString) {
    // Base64url -> Base64に変換
    const base64String = base64urlString
        .replace(/-/g, '+')  // Base64urlの`-`を`+`に置換
        .replace(/_/g, '/')  // Base64urlの`_`を`/`に置換
        .padEnd(base64urlString.length + (4 - base64urlString.length % 4) % 4, '='); // パディングを追加

    try {
        // Base64 -> Uint8Arrayに変換
        const rawData = atob(base64String);  // Base64文字列をデコード
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);  // 各文字をUint8Arrayに変換
        }

        return outputArray;
    } catch (error) {
        console.error('Base64デコードに失敗しました:', error);
        throw new Error('Base64デコードエラー');
    }
}
