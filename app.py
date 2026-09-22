from flask import Flask, render_template, request, jsonify, make_response, redirect, session
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)
# セッション暗号化用の秘密鍵（適当な英数字でOK）
app.secret_key = 'your_secret_admin_key_here'

# ★ あなただけの管理者パスワードを設定（ここを好きな文字に変えてください）
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
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    # ユーザーがアクセスしたらUID（サイト内ID）を自動発行してCookieに保存
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

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO sim_logs (uid, username, target_followers, created_at) VALUES (?, ?, ?, ?)',
        (uid, username, target, now_str)
    )
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# ★ 管理者ログイン画面
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True  # あなたを管理者として認識！
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

# ★ ログ閲覧ページ（あなただけが見れるページ）
@app.route('/admin/logs')
def view_logs():
    # 管理者ログインしていない人はログイン画面に追い返す（判定処理）
    if not session.get('is_admin'):
        return redirect('/admin/login')

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('SELECT uid, username, target_followers, created_at FROM sim_logs ORDER BY id DESC LIMIT 100')
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
            table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background: #dc2743; color: white; }
            tr:nth-child(even) { background: #f9f9f9; }
            .badge { background: #e0e0e0; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
        </style>
    </head>
    <body>
        <h2>📊 シミュレーション実行ログ（最新100件）</h2>
        <p><a href="/" style="color:#0095f6;">← サイトトップへ戻る</a></p>
        <table>
            <tr>
                <th>ユーザーUID (自動発行ID)</th>
                <th>実行日時</th>
                <th>入力されたユーザー名</th>
                <th>目標フォロワー数</th>
            </tr>
    '''
    for log in logs:
        html += f'''
            <tr>
                <td><span class="badge">{log[0]}</span></td>
                <td>{log[3]}</td>
                <td>@{log[1]}</td>
                <td>{log[2]:,}</td>
            </tr>
        '''
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
