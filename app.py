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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        res = requests.get(url, headers=headers, timeout=5)
        
        # Instagramのメタタグから情報を抽出
        og_image = re.search(r'property="og:image"\s+content="([^"]+)"', res.text)
        og_title = re.search(r'property="og:title"\s+content="([^"]+)"', res.text)

        # 実在する公開アカウントの場合、og:title に「名前 (@username) • Instagram photos and videos」のような形式が入る
        if og_title and username.lower() in og_title.group(1).lower():
            profile_pic = ""
            full_name = username

            if og_image:
                profile_pic = og_image.group(1).replace("&amp;", "&")

            # titleから表示名を取得
            title_text = og_title.group(1)
            if '•' in title_text:
                full_name = title_text.split('•')[0].strip()
            elif '(' in title_text:
                full_name = title_text.split('(')[0].strip()

            # 画像が取れなかった場合のみフォールバック
            if not profile_pic or "static/images" in profile_pic:
                profile_pic = f"https://ui-avatars.com/api/?name={username}&background=random"

            return jsonify({
                'success': True,
                'username': username,
                'full_name': full_name,
                'profile_pic': profile_pic,
                'initial_followers': 1000
            })
        else:
            # メタタグにユーザー名が含まれていない＝存在しないか非公開・ブロック
            return jsonify({'success': False, 'error': f'@{username} は存在しないか、非公開アカウントです。'})

    except Exception as e:
        return jsonify({'success': False, 'error': f'通信エラー: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
