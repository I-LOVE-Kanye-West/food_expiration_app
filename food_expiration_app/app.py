import os
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pywebpush import webpush, WebPushException
import hashlib

# Flaskアプリの設定
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key_here')

# VAPIDキーの設定
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "BKX3d2SLf6e93syXaeuVHdCO82WnzHczZZVm4_pJziQVJPTY8XlBKzDyDLyUnsVpPd5J1DnpLxxurHr04O5MyA8")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "_XZx_MhN6ZD2z2eE-clW0q1UUfZwSwQ5pRLK9fU4aAg")
VAPID_CLAIMS = {"sub": "mailto:moryosa@boxfi.uk"}

# データベースおよびサブスクリプション設定
DATABASE_FILE = os.path.join(os.getcwd(), 'food_database.db')
SUBSCRIPTIONS_FILE = os.path.join(os.getcwd(), 'subscriptions.json')

# データベース初期化
def init_db():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                expiration_date TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS kakeibo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                income_expense TEXT NOT NULL,  -- 収支
                details TEXT NOT NULL,         -- 詳細
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )''')

        # income_expense カラムを追加
        add_income_expense_column()

        conn.commit()

# 家計簿テーブルのカラム追加
def add_income_expense_column():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # income_expense カラムが存在しない場合のみ追加
        cursor.execute('PRAGMA table_info(kakeibo);')
        columns = [column[1] for column in cursor.fetchall()]
        if 'income_expense' not in columns:
            cursor.execute('ALTER TABLE kakeibo ADD COLUMN income_expense TEXT NOT NULL DEFAULT "支出"')
        if 'details' not in columns:
            cursor.execute('ALTER TABLE kakeibo ADD COLUMN details TEXT NOT NULL DEFAULT ""')
        conn.commit()

# 取引の絞り込み処理
def filter_transactions(user_id, time_filter=None):
    # 現在の日付
    current_date = datetime.now()
    # 時間範囲の設定
    if time_filter == '1_month':
        start_date = current_date - timedelta(days=30)
    elif time_filter == '3_months':
        start_date = current_date - timedelta(days=90)
    elif time_filter == '1_year':
        start_date = current_date - timedelta(days=365)
    elif time_filter == '3_years':
        start_date = current_date - timedelta(days=1095)
    else:
        start_date = None  # デフォルトでは制限なし

    # 取引の取得
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        if start_date:
            cursor.execute(
                'SELECT * FROM kakeibo WHERE user_id = ? AND date >= ? ORDER BY date DESC',
                (user_id, start_date.strftime('%Y-%m-%d'))
            )
        else:
            cursor.execute('SELECT * FROM kakeibo WHERE user_id = ? ORDER BY date DESC', (user_id,))
        transactions = cursor.fetchall()

    # デバッグ用: 取引データを確認
    print("Transactions:", transactions)

    # 収支の合計金額を計算
    total_income = 0
    total_expense = 0
    for transaction in transactions:
        print(f"Transaction: {transaction}")  # 各取引を確認
        income_expense = transaction[4].strip()  # 収支を取得して余分な空白を削除
        if income_expense == '収入':  # 収入
            total_income += transaction[1]
        elif income_expense == '支出':  # 支出
            total_expense += transaction[1]

    total_amount = total_income - total_expense

    # デバッグ用の出力
    print(f"Total Income: {total_income}, Total Expense: {total_expense}, Total Amount: {total_amount}")

    return transactions, total_amount

# 金額フォーマット関数
def format_currency(amount):
    if amount is not None:
        return f"{int(amount):,}"  # 円マークとカンマ区切りを適用
    return "¥0"

# Flask テンプレートで使用するフィルタを登録
app.jinja_env.filters['format_currency'] = format_currency

# サブスクリプションファイルの初期化
def ensure_subscriptions_file():
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

# 食品の状態を判定
def get_food_status(expiration_date):
    current_date = datetime.now().date()
    expiration = datetime.strptime(expiration_date, '%Y-%m-%d').date()
    if expiration < current_date:
        return "期限切れ"
    elif expiration <= current_date + timedelta(days=7):
        return "期限切迫"
    return "OK"

# 食品の取得
def get_foods(user_id, status_filter=None):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM foods WHERE user_id = ?', (user_id,))
        foods = cursor.fetchall()
    return [
        (food[0], food[1], food[2], get_food_status(food[2]))
        for food in foods if status_filter is None or get_food_status(food[2]) == status_filter
    ]

# Web Push通知送信
def send_notification(subscription, message):
    try:
        webpush(
            subscription_info=subscription,
            data=message,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
    except WebPushException as ex:
        print(f"通知の送信に失敗しました: {repr(ex)}")

# 期限切迫食品の通知送信
def check_and_notify():
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        return
    with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
        subscriptions = json.load(f)

    user_id = 1  # 実際のアプリではセッションから取得
    foods = get_foods(user_id, status_filter="期限切迫")
    if not foods:
        return

    message = json.dumps({
        "title": "食品管理通知",
        "body": "期限切迫の食品があります！アプリをご確認ください。"
    })
    for subscription in subscriptions:
        send_notification(subscription, message)

# パスワードのハッシュ化
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ユーザーログイン状態の確認
def is_logged_in():
    return 'user_id' in session

# ルート
@app.route('/')
def index():
    # ユーザーがログインしているか確認
    if not is_logged_in():
        return redirect(url_for('login'))
    
    # 現在のユーザーのIDを取得
    user_id = session.get('user_id')
    
    # フィルター条件を取得
    status_filter = request.args.get('status', '')  # デフォルトは空文字（すべて）
    
    # フィルターに基づいて食品データを取得
    if status_filter and status_filter != 'すべて':
        foods = get_foods(user_id, status_filter)
    else:
        foods = get_foods(user_id)  # フィルターなしで取得
    
    # テンプレートをレンダリング
    return render_template('index.html', foods=foods, status_filter=status_filter)

@app.route('/logout')
def logout():
    # セッションからユーザー情報を削除
    session.pop('user_id', None)
    return redirect(url_for('login'))  # ログインページにリダイレクト



@app.route('/add', methods=['GET', 'POST'])
def add_food():
    if not is_logged_in():
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form.get('name')
        expiration_date = request.form.get('expiration_date')
        if not name or not expiration_date:
            return render_template('add_food.html', error="すべてのフィールドを入力してください"), 400
        user_id = session['user_id']
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.execute('INSERT INTO foods (name, expiration_date, user_id) VALUES (?, ?, ?)', (name, expiration_date, user_id))
            conn.commit()
        return redirect(url_for('index'))
    return render_template('add_food.html')

@app.route('/delete/<int:food_id>')
def delete_food(food_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute('DELETE FROM foods WHERE id = ?', (food_id,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/kakeibo', methods=['GET', 'POST'])
def kakeibo():
    if not is_logged_in():
        return redirect(url_for('login'))

    # セッションから user_id を取得
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))  # user_id がセッションに無い場合はログイン画面へ

    # POSTリクエスト時の処理（新しい取引の追加）
    if request.method == 'POST':
        # フォームデータの取得
        amount = request.form.get('amount')
        category = request.form.get('category')
        date = request.form.get('date')
        income_expense = request.form.get('income_expense')  # 収支
        details = request.form.get('details')  # 詳細

        # 必須フィールドのチェック
        if not amount or not category or not date or not income_expense or not details:
            return render_template(
                'kakeibo.html',
                error="すべてのフィールドを入力してください"
            ), 400

        # データベースに新しい取引を挿入
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.execute(
                '''
                INSERT INTO kakeibo (amount, category, date, income_expense, details, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (amount, category, date, income_expense, details, user_id)
            )
            conn.commit()
        return redirect(url_for('kakeibo'))

    # 期間の絞り込み処理
    time_filter = request.args.get('time_filter', '1_month')  # デフォルトは過去1ヶ月
    transactions, total_amount = filter_transactions(user_id, time_filter)

    # 収入合計と支出合計を計算
    total_income = sum(float(row[1]) for row in transactions if row[4] == '収入')
    total_expense = sum(float(row[1]) for row in transactions if row[4] == '支出')

    # テンプレートをレンダリング
    return render_template(
        'kakeibo.html',
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        total_amount=total_amount
    )




@app.template_filter('format_currency')
def format_currency(value):
    return "¥{:,.0f}".format(value)

# 取引の削除処理
@app.route('/delete_transaction/<int:transaction_id>')
def delete_transaction(transaction_id):
    if not is_logged_in():
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute('DELETE FROM kakeibo WHERE id = ? AND user_id = ?', (transaction_id, user_id))
        conn.commit()

    return redirect(url_for('kakeibo'))

# 通知登録画面
@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/subscribe', methods=['POST'])
def subscribe():
    subscription = request.json
    with open(SUBSCRIPTIONS_FILE, 'r+', encoding='utf-8') as f:
        subscriptions = json.load(f)
        if subscription not in subscriptions:
            subscriptions.append(subscription)
            f.seek(0)
            json.dump(subscriptions, f)
    return jsonify({"success": True}), 200

@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']

        # パスワードのハッシュ化
        hashed_password = hash_password(password)

        # データベース接続
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()

            # user_id が既に存在しているかチェック
            cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            if cursor.fetchone() is not None:
                # ユーザーIDが既に存在している場合
                error = "このユーザーIDは既に登録されています。他のIDをお試しください。"
                return render_template('register_user.html', error=error)

            # 新規ユーザーの登録
            conn.execute('INSERT INTO users (user_id, password) VALUES (?, ?)', (user_id, hashed_password))
            conn.commit()

        # 登録成功時、ログインページにリダイレクト
        return redirect(url_for('login'))

    return render_template('register_user.html')


# ログイン画面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        hashed_password = hash_password(password)

        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ? AND password = ?', (user_id, hashed_password))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user[0]  # user_idをセッションに保存
                return redirect(url_for('index'))

        return render_template('login.html', error="ログインに失敗しました。")

    return render_template('login.html')

# アプリケーション起動時にDB初期化
if __name__ == "__main__":
    init_db()
    ensure_subscriptions_file()

    # スケジューラーの設定
    scheduler = BackgroundScheduler()
    cron_trigger = CronTrigger(hour=9, minute=0)  # 毎日午前9時に実行
    scheduler.add_job(func=check_and_notify, trigger=cron_trigger)
    scheduler.start()

    app.run(debug=True)
