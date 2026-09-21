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

    # Web検索用の簡易エンドポイントで存在確認を試行
    url = f"https://www.instagram.com/web/search/topsearch/?query={username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            users = res.json().get('users', [])
            # 検索結果の中に完全一致するIDがあるか確認
            matched_user = next((u['user'] for u in users if u['user']['username'].lower() == username.lower()), None)
            
            if matched_user:
                full_name = matched_user.get('full_name') or username
                return jsonify({
                    'success': True,
                    'username': username,
                    'full_name': full_name,
                    'is_verified': matched_user.get('is_verified', False)
                })
            else:
                return jsonify({'success': False, 'error': f'@{username} というユーザーは見つかりませんでした。'})
        else:
            # 制限等でAPI拒否された場合はID直接チェック
            direct_url = f"https://www.instagram.com/{username}/"
            d_res = requests.get(direct_url, headers=headers, timeout=5)
            if d_res.status_code == 200 and f'"{username}"' in d_res.text.lower():
                return jsonify({
                    'success': True,
                    'username': username,
                    'full_name': username,
                    'is_verified': False
                })
            
            return jsonify({'success': False, 'error': f'@{username} は存在しないか、検索制限中です。'})

    except Exception as e:
        return jsonify({'success': False, 'error': f'通信エラーが発生しました: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
