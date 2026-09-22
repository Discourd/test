from flask import Flask, render_template, request, jsonify, make_response, redirect, session
import sqlite3
import uuid
import urllib.request
import json
from datetime import datetime

app = Flask(__name__)
# セッション暗号化用の秘密鍵
app.secret_key = 'your_secret_admin_key_here'

# ★ 管理者ログイン用のパスワード（好きな文字に変更してください）
ADMIN_PASSWORD = 'admin'

# データベースの初期化
def init_db():
    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sim_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            username TEXT,
            target_followers INTEGER,
            created_at TEXT NOT NULL,
            ip_address TEXT,
            location TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# IPアドレスから都道府県・市区町村を取得する関数
def get_location_from_ip(ip):
    # ローカル環境（127.0.0.1）などの例外処理
    if not ip or ip in ['127.0.0.1', 'localhost', '::1']:
        return "ローカル環境"
    
    try:
        # ip-api.com を利用して日本語で地域情報を取得
        url = f"http://ip-api.com/json/{ip}?lang=ja&fields=status,regionName,city"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            if data.get('status') == 'success':
                region = data.get('regionName', '') # 県名（例: 東京都）
                city = data.get('city', '')         # 市区町村（例: 渋谷区）
                return f"{region} {city}".strip()
    except Exception as e:
        print(f"GeoIP Error: {e}")
    
    return "解析不能"

@app.route('/')
def index():
    # ユーザーアクセスのたびにUIDを発行・保持
    user_id = request.cookies.get('user_uid')
    if not user_id:
        user_id = f"UID_{uuid.uuid4().hex[:8]}"
    
    resp = make_response(render_template('index.html', uid=user_id))
    resp.set_cookie('user_uid', user_id, max_age=60*60*24*365)
    return resp

# シミュレーション実行時のログ記録API
@app.route('/api/log_simulation', methods=['POST'])
def log_simulation():
    data = request.json
    uid = request.cookies.get('user_uid', 'UNKNOWN')
    username = data.get('username', 'demo_user')
    target = data.get('target', 0)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # ユーザーのIPアドレスを取得（Render環境対応）
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    # IPから県・市を取得
    location = get_location_from_ip(ip_address)

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    
    # 古いデータベースへのカラム自動追加対応
    try:
        cursor.execute('ALTER TABLE sim_logs ADD COLUMN ip_address TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE sim_logs ADD COLUMN location TEXT')
    except:
        pass

    cursor.execute(
        'INSERT INTO sim_logs (uid, username, target_followers, created_at, ip_address, location) VALUES (?, ?, ?, ?, ?, ?)',
        (uid, username, target, now_str, ip_address, location)
    )
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# 管理者ログイン画面
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin/logs')
        else:
            error = 'パスワードが違います'

    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>管理者認証</title></head>
    <body style="font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; background:#f4f4f9;">
        <form method="POST" style="background:white; padding:30px; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.1); text-align:center;">
            <h3>🔐 管理者ログイン</h3>
            {'<p style="color:red; font-size:12px;">' + error + '</p>' if error else ''}
            <input type="password" name="password" placeholder="パスワードを入力" required style="padding:10px; margin-bottom:10px; width:100%; box-sizing:border-box;"><br>
            <button type="submit" style="padding:10px 20px; background:#dc2743; color:white; border:none; border-radius:5px; cursor:pointer;">ログイン</button>
        </form>
    </body>
    </html>
    '''

# 管理者ログ閲覧画面（IP・アクセス地域付き）
@app.route('/admin/logs')
def view_logs():
    if not session.get('is_admin'):
        return redirect('/admin/login')

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('SELECT uid, username, target_followers, created_at, ip_address, location FROM sim_logs ORDER BY id DESC LIMIT 100')
    logs = cursor.fetchall()
    conn.close()

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>管理者用 実行ログ</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f4f4f9; }
            h2 { color: #333; }
            table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); font-size:13px; }
            th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
            th { background: #dc2743; color: white; }
            tr:nth-child(even) { background: #f9f9f9; }
            .badge { background: #e0e0e0; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
            .ip-box { font-family: monospace; color: #555; }
            .loc-box { font-weight: bold; color: #2b6cb0; }
        </style>
    </head>
    <body>
        <h2>📊 シミュレーション実行ログ（最新100件）</h2>
        <p><a href="/" style="color:#0095f6;">← サイトトップへ戻る</a></p>
        <table>
            <tr>
                <th>UID (ユーザーID)</th>
                <th>実行日時</th>
                <th>アカウント名</th>
                <th>目標数</th>
                <th>アクセス地域 (県・市)</th>
                <th>IPアドレス</th>
            </tr>
    '''
    for log in logs:
        loc = log[5] if log[5] else '不明'
        ip = log[4] if log[4] else '不明'
        html += f'''
            <tr>
                <td><span class="badge">{log[0]}</span></td>
                <td>{log[3]}</td>
                <td>@{log[1]}</td>
                <td>{log[2]:,}</td>
                <td><span class="loc-box">📍 {loc}</span></td>
                <td><span class="ip-box">{ip}</span></td>
            </tr>
        '''
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
