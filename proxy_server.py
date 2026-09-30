import base64
import json
import logging
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


@app.get("/health")
async def health():
    return {"status": "ok", "chat_sync": CHAT_FILE.exists()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
