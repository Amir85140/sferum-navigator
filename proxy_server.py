import json
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

GIGA_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
GIGA_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"
OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGA_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
CHAT_FILE = Path("chat_sync.json")

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
    r = requests.post(
        OAUTH_URL,
        headers={
            "Authorization": "Basic " + base64.b64encode(f"{GIGA_ID}:{GIGA_SECRET}".encode()).decode() if False else __import__("base64").b64encode(f"{GIGA_ID}:{GIGA_SECRET}".encode()).decode(),
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

# ===== УНИВЕРСАЛЬНЫЙ ПРОКСИ =====
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
        r = requests.request(method=request.method, url=url, headers=headers, data=body, verify=False, timeout=60)
    except Exception as e:
        raise HTTPException(502, str(e))
    resp = Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("Content-Type", "application/json"))
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

# ===== СИНХРОНИЗАЦИЯ ЧАТА =====
def _load_store():
    if CHAT_FILE.exists():
        try:
            return json.loads(CHAT_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

@app.get("/chat_history")
async def chat_history_get(user_id: str = "main"):
    store = _load_store()
    return JSONResponse(content=store.get(user_id, []), headers={"Access-Control-Allow-Origin": "*"})

@app.post("/chat_history")
async def chat_history_post(request: Request, user_id: str = "main"):
    data = await request.json()
    store = _load_store()
    store[user_id] = (data or [])[-50:]
    CHAT_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    return JSONResponse(content={"status": "ok", "count": len(store[user_id])},
                        headers={"Access-Control-Allow-Origin": "*"})

# ===== ПРОВЕРКА ВИДЕО =====
@app.get("/check_video")
async def check_video(q: str = ""):
    if not q:
        return {"available": []}
    qq = urllib.parse.quote(q)
    checks = {
        "youtube": f"https://www.youtube.com/results?search_query={qq}",
        "vk": f"https://vk.com/video?q={qq}",
        "rutube": f"https://rutube.ru/search/?q={qq}",
    }
    res = {}
    for k, u in checks.items():
        try:
            r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=6, verify=False)
            txt = r.text.lower()
            res[k] = r.status_code == 200 and ("ничего не найдено" not in txt) and ("no results" not in txt)
        except Exception:
            res[k] = False
    return {"available": [k for k, v in res.items() if v], "all": res}

# ===== VISION: АНАЛИЗ ФОТО (JSON base64, без multipart) =====
@app.post("/vision")
async def vision(request: Request):
    try:
        payload = await request.json()
        data_url = payload.get("dataUrl", "")
        text = payload.get("text", "")
        history = payload.get("history", [])
        if not data_url.startswith("data:image/"):
            raise HTTPException(400, "Нужна картинка data:image/...;base64,...")
        if len(data_url) > 8 * 1024 * 1024:
            raise HTTPException(400, "Картинка слишком большая")
        token = await _get_giga_token()
        hist_msgs = []
        for m in (history or [])[-8:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                hist_msgs.append({"role": m["role"], "content": str(m.get("content", ""))})
        user_content = [
            {"type": "text", "text": text or "Опиши, что на этой картинке."},
            {"type": "image_url", "image_url": {"url": data_url}}
        ]
        system = ("Ты — дружелюбный ИИ-наставник для школьников. Анализируй изображение внимательно. "
                  "Если это задача — реши пошагово. Математические формулы пиши в LaTeX: инлайн в $...$, "
                  "блочные в $$...$$. Не используй Markdown.")
        messages = [{"role": "system", "content": system}] + hist_msgs + [{"role": "user", "content": user_content}]
        resp = requests.post(
            GIGA_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": "GigaChat-Max", "messages": messages, "max_tokens": 1200, "temperature": 0.5},
            timeout=90,
            verify=False
        )
        if resp.status_code != 200:
            raise HTTPException(resp.status_code, f"GigaChat error: {resp.text[:300]}")
        ans = resp.json()["choices"][0]["message"]["content"]
        ans = ans.replace("**", "").replace("`", "").strip()
        return {"reply": ans}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка vision: {str(e)}")

# ===== HEALTH =====
@app.get("/health")
async def health():
    return {"status": "ok", "chat_sync": CHAT_FILE.exists()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
