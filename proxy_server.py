from flask import Flask, request, jsonify, Response
import requests as rq
import urllib3
import json
import os
from pathlib import Path

urllib3.disable_warnings()

app = Flask(__name__)
CHAT_FILE = Path('chat_sync.json')

# Прокси для GigaChat
@app.route('/proxy', methods=['GET', 'POST', 'OPTIONS'])
def proxy():
    if request.method == 'OPTIONS':
        resp = Response('', status=204)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return resp
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'no url'}), 400
    try:
        skip = ('host', 'content-length', 'origin', 'referer', 'connection', 'cookie')
        headers = {k: v for k, v in request.headers if k.lower() not in skip}
        r = rq.request(method=request.method, url=url, headers=headers,
                       data=request.get_data(), verify=False, timeout=60)
        resp = Response(r.content, status=r.status_code)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Content-Type'] = r.headers.get('Content-Type', 'application/json')
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 502

# Синхронизация истории чата между мини-апом и ботом
@app.route('/chat_history', methods=['GET', 'POST', 'OPTIONS'])
def chat_history():
    if request.method == 'OPTIONS':
        resp = Response('', status=204)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return resp
    
    user_id = request.args.get('user_id', 'default')
    
    # Загрузка истории
    if request.method == 'GET':
        if CHAT_FILE.exists():
            try:
                data = json.loads(CHAT_FILE.read_text(encoding='utf-8'))
                return jsonify(data.get(user_id, []))
            except:
                return jsonify([])
        return jsonify([])
    
    # Сохранение истории
    elif request.method == 'POST':
        history = request.get_json(silent=True) or []
        if CHAT_FILE.exists():
            try:
                data = json.loads(CHAT_FILE.read_text(encoding='utf-8'))
            except:
                data = {}
        else:
            data = {}
        data[user_id] = history[-50:]  # храним последние 50 сообщений
        CHAT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return jsonify({'status': 'ok', 'count': len(history)})

# Проверка наличия видео на платформах
@app.route('/check_video', methods=['GET', 'OPTIONS'])
def check_video():
    if request.method == 'OPTIONS':
        resp = Response('', status=204)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        return resp
    
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'available': []})
    
    results = {}
    
    # YouTube
    try:
        r = rq.get(f'https://www.youtube.com/results?search_query={rq.utils.urls.url_quote(query)}',
                   headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, verify=False)
        results['youtube'] = r.status_code == 200 and 'no results' not in r.text.lower()
    except:
        results['youtube'] = False
    
    # VK Video
    try:
        r = rq.get(f'https://vk.com/video?q={rq.utils.urls.url_quote(query)}',
                   headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, verify=False)
        results['vk'] = r.status_code == 200
    except:
        results['vk'] = False
    
    # RuTube
    try:
        r = rq.get(f'https://rutube.ru/search/?q={rq.utils.urls.url_quote(query)}',
                   headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, verify=False)
        results['rutube'] = r.status_code == 200 and 'ничего не найдено' not in r.text.lower()
    except:
        results['rutube'] = False
    
    available = [k for k, v in results.items() if v]
    return jsonify({'available': available, 'all': results})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'chat_sync': CHAT_FILE.exists()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
