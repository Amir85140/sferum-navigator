import base64
import json
import logging
import re
import time
import uuid
import urllib.parse
from pathlib import Path

import requests
import urllib3
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import uvicorn

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("proxy")

GIGA_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
GIGA_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"
OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGA_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
CHAT_FILE = Path("chat_sync.json")

MATH_SYSTEM_DEFAULT = (
    "Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно. "
    "Не используй Markdown (**, #, `). Математические формулы пиши в LaTeX: "
    "инлайн в $...$, блочные в $$...$$."
)

app = FastAPI(title="Sferum Navigator Proxy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_token = None
_token_exp = 0


def _get_giga_token_sync():
    global _token, _token_exp
    if _token and time.time() < _token_exp:
        return _token
    auth_str = f"{GIGA_ID}:{GIGA_SECRET}".encode()
    r = requests.post(
        OAUTH_URL,
        headers={
            "Authorization": "Basic " + base64.b64encode(auth_str).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": str(uuid.uuid4()),
        },
        data={"scope": "GIGACHAT_API_PERS"},
        verify=False,
        timeout=30,
    )
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"OAuth failed: {r.text[:200]}")
    d = r.json()
    _token = d["access_token"]
    _token_exp = time.time() + 1700
    return _token


async def _get_giga_token():
    return _get_giga_token_sync()


def _load_store():
    if CHAT_FILE.exists():
        try:
            return json.loads(CHAT_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_store(store):
    CHAT_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


@app.api_route("/proxy", methods=["GET", "POST", "OPTIONS"])
async def proxy(request: Request, url: str = ""):
    if request.method == "OPTIONS":
        return Response(status_code=204)
    if not url:
        raise HTTPException(400, "no url")
    body = await request.body()
    skip = {"host", "content-length", "origin", "referer", "connection", "cookie", "accept-encoding"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in skip}
    try:
        r = requests.request(
            method=request.method, url=url, headers=headers,
            data=body, verify=False, timeout=60
        )
    except Exception as e:
        raise HTTPException(502, str(e))
    resp = Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("Content-Type", "application/json"),
    )
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.get("/chat_history")
async def chat_history_get(user_id: str = "main"):
    store = _load_store()
    return JSONResponse(
        content=store.get(user_id, []),
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.post("/chat_history")
async def chat_history_post(request: Request, user_id: str = "main"):
    data = await request.json()
    store = _load_store()
    store[user_id] = (data or [])[-50:]
    _save_store(store)
    return JSONResponse(
        content={"status": "ok", "count": len(store[user_id])},
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.post("/chat")
async def chat(request: Request, user_id: str = ""):
    try:
        payload = await request.json()
        prompt = payload.get("prompt", "")
        system = payload.get("system") or MATH_SYSTEM_DEFAULT
        max_tokens = int(payload.get("max_tokens") or 800)
        client_history = payload.get("history") or []
        use_store = bool(user_id)
        store_hist = []
        if use_store:
            raw = _load_store().get(user_id, [])
            store_hist = [m for m in raw if isinstance(m, dict) and m.get("role") in ("user", "assistant")][-16:]
        messages = [{"role": "system", "content": system}]
        for m in (store_hist + client_history)[-16:]:
            messages.append({"role": m.get("role"), "content": str(m.get("content", ""))})
        messages.append({"role": "user", "content": prompt})
        token = await _get_giga_token()
        r = requests.post(
            GIGA_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": "GigaChat:latest", "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=60,
            verify=False,
        )
        log.info("CHAT -> %s (user_id=%s)", r.status_code, user_id or "-")
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"GigaChat error: {r.text[:200]}")
        reply_text = r.json()["choices"][0]["message"]["content"]
        if use_store:
            st = _load_store()
            arr = st.get(user_id, [])
            ts = int(time.time() * 1000)
            arr.append({"role": "user", "content": prompt, "timestamp": ts, "source": "web"})
            arr.append({"role": "assistant", "content": reply_text, "timestamp": ts + 1, "source": "web"})
            st[user_id] = arr[-50:]
            _save_store(st)
        return {"reply": reply_text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка chat: {str(e)}")


@app.get("/search_video")
async def search_video(q: str = ""):
    if not q:
        return JSONResponse(content={"rutube": [], "vk": [], "youtube": []}, headers={"Access-Control-Allow-Origin": "*"})
    rt = []
    try:
        r = requests.get('https://rutube.ru/api/video/',
                         params={'query': q, 'page': 1, 'per_page': 6},
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False)
        if r.ok:
            ws = [w for w in re.split(r'\s+', q.lower()) if len(w) > 3]
            for v in (r.json().get('results') or []):
                title = re.sub(r'<[^>]+>', '', v.get('title', '') or '')
                tl = title.lower()
                if ws and not any(w in tl for w in ws):
                    continue
                rt.append({'title': title[:80],
                           'url': v.get('video_url') or f"https://rutube.ru/video/{v.get('id','')}/"})
                if len(rt) >= 3:
                    break
    except Exception as e:
        log.info(f"search_video rutube: {e}")
    vk = []
    try:
        r2 = requests.get('https://vk.com/video', params={'q': q},
                          headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                                   'Accept-Language': 'ru-RU,ru;q=0.9'},
                          timeout=10, verify=False)
        if r2.ok:
            seen = set()
            for pair in re.findall(r'video(-?\d+_\d+)', r2.text):
                if pair in seen:
                    continue
                seen.add(pair)
                vk.append({'url': f'https://vk.com/video{pair}'})
                if len(vk) >= 2:
                    break
    except Exception as e:
        log.info(f"search_video vk: {e}")
    yt = []
    try:
        r3 = requests.get('https://www.youtube.com/results', params={'search_query': q},
                          headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                   'Accept-Language': 'ru-RU,ru;q=0.9'}, timeout=10, verify=False)
        if r3.ok:
            ids = re.findall(r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})"', r3.text)
            if not ids:
                ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r3.text)
            seen = set()
            for vid in ids:
                if vid in seen:
                    continue
                seen.add(vid)
                yt.append({'url': f'https://www.youtube.com/watch?v={vid}'})
                if len(yt) >= 2:
                    break
    except Exception as e:
        log.info(f"search_video youtube: {e}")
    return JSONResponse(content={"rutube": rt, "vk": vk, "youtube": yt}, headers={"Access-Control-Allow-Origin": "*"})


@app.get("/check_video")
async def check_video(q: str = ""):
    if not q:
        return {"available": []}
    qq = urllib.parse.quote(q)
    checks = {
        "vk": f"https://vk.com/video?q={qq}",
        "rutube": f"https://rutube.ru/search/?q={qq}",
    }
    res = {}
    for k, u in checks.items():
        try:
            r = requests.get(
                u, headers={"User-Agent": "Mozilla/5.0"}, timeout=6, verify=False
            )
            txt = r.text.lower()
            res[k] = (
                r.status_code == 200
                and "ничего не найдено" not in txt
                and "no results" not in txt
            )
        except Exception:
            res[k] = False
    return {"available": [k for k, v in res.items() if v], "all": res}


@app.post("/vision")
async def vision(request: Request):
    """Принимает фото задачи, возвращает пошаговое решение"""
    try:
        payload = await request.json()
        image_b64 = payload.get("image")
        prompt = payload.get("prompt") or "Реши задачу на фото пошагово, с объяснением каждого шага. Формулы пиши простым текстом."
        
        if not image_b64:
            raise HTTPException(400, "no image")
        
        # Убираем префикс data:image/...;base64, если он есть
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        
        token = await _get_giga_token()
        
        messages = [
            {
                "role": "system",
                "content": "Ты — эксперт по школьным задачам. Реши задачу пошагово, объясни каждый шаг. Формулы пиши простым текстом (a = F / m). Если задача нечитаема — честно скажи."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }
        ]
        
        # Пробуем разные модели с поддержкой vision
        models_to_try = ["GigaChat-Max", "GigaChat-Pro", "GigaChat:latest"]
        last_err = None
        
        for model in models_to_try:
            try:
                r = requests.post(
                    GIGA_URL,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "max_tokens": 1500, "temperature": 0.3},
                    timeout=60,
                    verify=False,
                )
                if r.ok:
                    solution = r.json()["choices"][0]["message"]["content"]
                    log.info("VISION -> %s (model=%s)", r.status_code, model)
                    return {"solution": solution, "model": model}
                else:
                    last_err = f"{model}: {r.status_code}"
                    log.info("VISION fail %s: %s", model, r.text[:100])
            except Exception as e:
                last_err = f"{model}: {e}"
                log.info("VISION err %s: %s", model, e)
        
        raise HTTPException(500, f"Все модели не сработали: {last_err}")
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"vision error: {e}")
        raise HTTPException(500, f"Ошибка vision: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "chat_sync": CHAT_FILE.exists()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
