# 食品管理アプリ

このアプリは食品の賞味期限を管理するためのアプリです。また、家計簿機能もあり、収支を記録することができます。

## 機能
- 食品の期限管理
- 家計簿（収入・支出の記録）
- Web Push通知（期限切迫の食品の通知）

## セットアップ方法

1. リポジトリをクローンします
    ```bash
    git clone https://github.com/yourusername/your-repository-name.git
    ```

2. 必要なライブラリをインストールします
    ```bash
    pip install -r requirements.txt
    ```

3. SQLiteデータベースを初期化します
    ```bash
    python app.py
    ```

4. Webアプリにアクセスします
    - デフォルトで`http://127.0.0.1:5000`で起動します。

## 使用ライブラリ
- Flask
- SQLite
- APScheduler
- pywebpush
