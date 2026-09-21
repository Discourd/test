from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_user():
    data = request.get_json()
    username = data.get('username', '').strip().replace('@', '')

    if not username:
        return jsonify({'success': False, 'error': 'ユーザーIDを入力してください。'})

    url = f"https://www.instagram.com/web/search/topsearch/?query={username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=5)
        
        # レスポンスが正常なJSONの場合のみチェック
        if res.status_code == 200:
            try:
                json_data = res.json()
                users = json_data.get('users', [])
                matched_user = next((u['user'] for u in users if u['user']['username'].lower() == username.lower()), None)
                
                if matched_user:
                    full_name = matched_user.get('full_name') or username
                    return jsonify({
                        'success': True,
                        'username': username,
                        'full_name': full_name
                    })
            except Exception:
                pass # JSON解析失敗時は下のフォールバックへ

        # Instagramの自動ブロックや制限でエラーになった場合でも、IDをそのまま使って成功扱いにする（フォールバック処理）
        return jsonify({
            'success': True,
            'username': username,
            'full_name': username
        })

    except Exception as e:
        # 通信タイムアウト等でも止まらずに進行許可
        return jsonify({
            'success': True,
            'username': username,
            'full_name': username
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
