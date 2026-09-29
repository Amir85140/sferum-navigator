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
FILES_URL = "https://gigachat.devices.sberbank.ru/api/v1/files"
CHAT_FILE = Path("chat_sync.json")

VISION_MODELS = ("GigaChat-Pro", "GigaChat-Max", "GigaChat-2-Pro", "GigaChat-2-Max")
STUB_MARKERS = (
    "изображение не предоставлено", "прикрепи картинку", "опиши её словами",
    "не вижу изображения", "изображение не получено", "приложите изображение",
    "приложите снова", "увидеть саму картинку", "мне нужно увидеть",
    "не могу увидеть", "изображение снова", "attach the image", "image again",
    "i need to see", "please attach", "no image", "не приложено",
)

VISION_SYSTEM = (
    "Ты — дружелюбный ИИ-наставник для школьников. "
    "Анализируй прикреплённое изображение внимательно. "
    "Если это задача — реши пошагово. "
    "Математические формулы пиши в LaTeX: инлайн в $...$, блочные в $$...$$. "
    "Не используй Markdown."
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


def _clean_ans(t):
    return t.replace("**", "").replace("`", "").strip()


def _is_stub(content):
    low = (content or "").lower()
    return any(m in low for m in STUB_MARKERS)


def _chat(token, messages, model, attachments=None):
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": 1200,
        "temperature": 0.5,
    }
    if attachments:
        body["attachments"] = attachments
    return requests.post(
        GIGA_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=90,
        verify=False,
    )


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
    return JSONResponse(
        content=store.get(user_id, []),
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.post("/chat_history")
async def chat_history_post(request: Request, user_id: str = "main"):
    data = await request.json()
    store = _load_store()
    store[user_id] = (data or [])[-50:]
    CHAT_FILE.write_text(
        json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return JSONResponse(
        content={"status": "ok", "count": len(store[user_id])},
        headers={"Access-Control-Allow-Origin": "*"},
    )


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

        b64 = data_url.split(";base64,", 1)[1] if ";base64," in data_url else data_url
        token = await _get_giga_token()

        hist_msgs = []
        for m in (history or [])[-8:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                hist_msgs.append({"role": m["role"], "content": str(m.get("content", ""))})
        q = text or "Опиши, что на этой картинке."
        errors = []
        file_id = None

        # 1) загрузка файла multipart
        try:
            raw = base64.b64decode(b64)
            fr = requests.post(
                FILES_URL,
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("photo.jpg", raw, "image/jpeg")},
                data={"purpose": "general"},
                timeout=60,
                verify=False,
            )
            log.info("VISION files -> %s %s", fr.status_code, fr.text[:150])
            if fr.status_code == 200:
                file_id = fr.json().get("id")
        except Exception as e:
            log.info("VISION files exc: %s", e)

        # 2) ждём, пока файл обработается (modalities станет непустым)
        if file_id:
            for attempt in range(5):
                try:
                    gr = requests.get(
                        f"{FILES_URL}/{file_id}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=15,
                        verify=False,
                    )
                    mods = (gr.json() or {}).get("modalities") or []
                    log.info("VISION file-status #%s -> %s modalities=%s", attempt, gr.status_code, mods)
                    if mods:
                        break
                except Exception as e:
                    log.info("VISION file-status exc: %s", e)
                time.sleep(1.2)

        # 3) чат с attachments: перебор всех моделей
        if file_id:
            msgs = [{"role": "system", "content": VISION_SYSTEM}] + hist_msgs + [{"role": "user", "content": q}]
            for model in VISION_MODELS:
                r = _chat(token, msgs, model, [file_id])
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    stub = _is_stub(content)
                    log.info("VISION att-%s -> 200 stub=%s %s", model, stub, content[:100])
                    if not stub:
                        return {"reply": _clean_ans(content)}
                    errors.append(f"{model}: заглушка")
                else:
                    log.info("VISION att-%s -> %s %s", model, r.status_code, r.text[:150])
                    errors.append(f"{model}: {r.status_code}")

        raise HTTPException(502, "GigaChat не увидел фото ни на одной модели: " + " | ".join(errors))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка vision: {str(e)}")

MATH_SYSTEM_DEFAULT = (
    "Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно. "
    "Не используй Markdown (**, #, `). Математические формулы пиши в LaTeX: "
    "инлайн в $...$, блочные в $$...$$."
)


@app.post("/chat")
async def chat(request: Request):
    try:
        payload = await request.json()
        prompt = payload.get("prompt", "")
        system = payload.get("system") or MATH_SYSTEM_DEFAULT
        max_tokens = int(payload.get("max_tokens") or 800)
        history = payload.get("history") or []
        if not prompt:
            raise HTTPException(400, "empty prompt")
        token = await _get_giga_token()
        messages = [{"role": "system", "content": system}]
        for m in history[-16:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                messages.append({"role": m["role"], "content": str(m.get("content", ""))})
        messages.append({"role": "user", "content": prompt})
        r = requests.post(
            GIGA_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": "GigaChat:latest", "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=60,
            verify=False,
        )
        log.info("CHAT -> %s", r.status_code)
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"GigaChat error: {r.text[:200]}")
        return {"reply": r.json()["choices"][0]["message"]["content"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка chat: {str(e)}")
@app.get("/health")
async def health():
    return {"status": "ok", "chat_sync": CHAT_FILE.exists()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
