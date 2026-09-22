from flask import Flask, render_template, request, jsonify, make_response
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)

# データベースの初期化（ログ保存用テーブルの作成）
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
    # CookieからUIDを取得。なければ新規発行
    user_id = request.cookies.get('user_uid')
    if not user_id:
        user_id = f"UID_{uuid.uuid4().hex[:8]}"  # 8文字のランダムIDを作成
    
    resp = make_response(render_template('index.html', uid=user_id))
    # クッキーにUIDを保存（有効期限1年）
    resp.set_cookie('user_uid', user_id, max_age=60*60*24*365)
    return resp

# シミュレーション実行時にログを保存するAPI
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

# ★ あなた専用のログ確認ページ (/admin)
@app.route('/admin/logs')
def view_logs():
    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('SELECT uid, username, target_followers, created_at FROM sim_logs ORDER BY id DESC LIMIT 100')
    logs = cursor.fetchall()
    conn.close()

    # 簡単なログ閲覧画面を出力
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
        </style>
    </head>
    <body>
        <h2>📊 シミュレーション実行ログ（最新100件）</h2>
        <table>
            <tr>
                <th>ユーザーUID</th>
                <th>実行日時</th>
                <th>設定したユーザー名</th>
                <th>目標フォロワー数</th>
            </tr>
    '''
    for log in logs:
        html += f'''
            <tr>
                <td><b>{log[0]}</b></td>
                <td>{log[3]}</td>
                <td>@{log[1]}</td>
                <td>{log[2]:,}</td>
            </tr>
        '''
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
