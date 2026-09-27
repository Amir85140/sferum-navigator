from flask import Flask, request, jsonify, Response
import requests as rq
import urllib3

urllib3.disable_warnings()

app = Flask(__name__)

@app.route('/proxy', methods=['GET', 'POST', 'OPTIONS'])
def proxy():
    # Разрешаем CORS для любого источника
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
        r = rq.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            verify=False,   # обходим недоверенный сертификат Сбера
            timeout=60
        )
        resp = Response(r.content, status=r.status_code)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Content-Type'] = r.headers.get('Content-Type', 'application/json')
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 502

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
