from flask import Flask, render_template, request, jsonify
import requests
import re

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

    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            # メタタグからアイコン画像と名前を取得
            profile_pic = ""
            full_name = username

            og_image = re.search(r'property="og:image"\s+content="([^"]+)"', res.text)
            if og_image:
                profile_pic = og_image.group(1).replace("&amp;", "&")

            og_title = re.search(r'property="og:title"\s+content="([^"]+)"', res.text)
            if og_title:
                full_name = og_title.group(1).split('•')[0].strip()

            if not profile_pic:
                profile_pic = f"https://ui-avatars.com/api/?name={username}&background=random"

            return jsonify({
                'success': True,
                'username': username,
                'full_name': full_name,
                'profile_pic': profile_pic,
                'initial_followers': 1000
            })
        elif res.status_code == 404:
            return jsonify({'success': False, 'error': f'@{username} は存在しません。'})
        else:
            return jsonify({'success': False, 'error': f'情報取得に失敗しました (Status: {res.status_code})'})

    except Exception as e:
        return jsonify({'success': False, 'error': f'通信エラー: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
