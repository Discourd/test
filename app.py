from flask import Flask, render_template, request, jsonify, make_response, redirect
import sqlite3
import uuid
import urllib.request
import json
from datetime import datetime

app = Flask(__name__)

# ★ あなた専用の管理者UID
ADMIN_UID = 'UID_546d63df'

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

def get_location_from_ip(ip):
    if not ip or ip in ['127.0.0.1', 'localhost', '::1']:
        return "ローカル環境"
    
    try:
        url = f"http://ip-api.com/json/{ip}?lang=ja"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            if data.get('status') == 'success':
                region = data.get('regionName', '')
                city = data.get('city', '')
                return f"{region} {city}".strip()
    except Exception as e:
        print(f"GeoIP Error: {e}")
    
    return "解析不能"

@app.route('/')
def index():
    user_id = request.cookies.get('user_uid')
    if not user_id:
        user_id = f"UID_{uuid.uuid4().hex[:8]}"
    
    resp = make_response(render_template('index.html', uid=user_id))
    resp.set_cookie('user_uid', user_id, max_age=60*60*24*365)
    return resp

@app.route('/api/log_simulation', methods=['POST'])
def log_simulation():
    data = request.json
    uid = request.cookies.get('user_uid', 'UNKNOWN')
    username = data.get('username', 'demo_user')
    target = data.get('target', 0)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    location = get_location_from_ip(ip_address)

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    
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

# ★ ログ個別削除API
@app.route('/admin/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    current_uid = request.cookies.get('user_uid')
    if current_uid != ADMIN_UID:
        return jsonify({'status': 'error', 'message': '権限がありません'}), 403

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sim_logs WHERE id = ?', (log_id,))
    conn.commit()
    conn.close()

    return redirect('/admin/logs')

# ★ ログ全件削除API
@app.route('/admin/clear_all_logs', methods=['POST'])
def clear_all_logs():
    current_uid = request.cookies.get('user_uid')
    if current_uid != ADMIN_UID:
        return jsonify({'status': 'error', 'message': '権限がありません'}), 403

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sim_logs')
    conn.commit()
    conn.close()

    return redirect('/admin/logs')

# ★ ログ閲覧画面（削除ボタン付き）
@app.route('/admin/logs')
def view_logs():
    current_uid = request.cookies.get('user_uid')
    
    if current_uid != ADMIN_UID:
        return '<h3 style="color:red; text-align:center; margin-top:50px;">🚫 403 Forbidden: 管理者権限がありません</h3>', 403

    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, uid, username, target_followers, created_at, ip_address, location FROM sim_logs ORDER BY id DESC LIMIT 100')
    logs = cursor.fetchall()
    conn.close()

    html = '''
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>管理者用 実行ログ</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 15px; background: #f4f4f9; margin:0; color: #333; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
            h2 { font-size: 18px; margin: 0; }
            .btn-group-head { display: flex; gap: 10px; align-items: center; }
            .back-btn { font-size: 13px; color: #0095f6; text-decoration: none; font-weight: bold; }
            .clear-all-btn { background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold; cursor: pointer; }
            
            .log-list { display: flex; flex-direction: column; gap: 12px; }
            .log-card { background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 5px solid #dc2743; position: relative; }
            
            .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px; padding-right: 50px; }
            .uid-badge { background: #eef2f7; color: #334155; padding: 3px 8px; border-radius: 6px; font-family: monospace; font-size: 12px; font-weight: bold; }
            .time { font-size: 12px; color: #888; }
            
            .card-body { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px; }
            .field-label { font-size: 11px; color: #888; margin-bottom: 2px; }
            .field-value { font-weight: 600; word-break: break-all; }
            .loc-text { color: #2b6cb0; font-weight: bold; }

            .del-btn { position: absolute; top: 12px; right: 12px; background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; padding: 4px 8px; border-radius: 6px; font-size: 11px; cursor: pointer; font-weight: bold; }
            .del-btn:hover { background: #fca5a5; color: white; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📊 実行ログ</h2>
            <div class="btn-group-head">
                <form action="/admin/clear_all_logs" method="POST" onsubmit="return confirm('本当に全てのログを消去しますか？');" style="margin:0;">
                    <button type="submit" class="clear-all-btn">🗑️ 全削除</button>
                </form>
                <a href="/" class="back-btn">← サイトへ</a>
            </div>
        </div>
        
        <div class="log-list">
    '''
    
    if not logs:
        html += '<p style="text-align:center; color:#888; margin-top:30px;">ログはありません</p>'

    for log in logs:
        log_id = log[0]
        loc = log[6] if log[6] else '不明'
        ip = log[5] if log[5] else '不明'
        html += f'''
            <div class="log-card">
                <form action="/admin/delete_log/{log_id}" method="POST" onsubmit="return confirm('このログを削除しますか？');" style="margin:0;">
                    <button type="submit" class="del-btn">削除</button>
                </form>
                <div class="card-header">
                    <span class="uid-badge">{log[1]}</span>
                    <span class="time">{log[4]}</span>
                </div>
                <div class="card-body">
                    <div>
                        <div class="field-label">アカウント名</div>
                        <div class="field-value">@{log[2]}</div>
                    </div>
                    <div>
                        <div class="field-label">目標フォロワー</div>
                        <div class="field-value">{log[3]:,} 人</div>
                    </div>
                    <div style="grid-column: span 2;">
                        <div class="field-label">推定アクセス地域</div>
                        <div class="field-value loc-text">📍 {loc}</div>
                    </div>
                    <div style="grid-column: span 2;">
                        <div class="field-label">IPアドレス</div>
                        <div class="field-value" style="font-family:monospace; font-size:12px; color:#555;">{ip}</div>
                    </div>
                </div>
            </div>
        '''
        
    html += '''
        </div>
    </body>
    </html>
    '''
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
