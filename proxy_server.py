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

        # ВАРИАНТ 1: загрузка файла multipart/form-data (как делает SDK Сбера)
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
            log.info("VISION files-multipart -> %s %s", fr.status_code, fr.text[:200])
            if fr.status_code == 200:
                file_id = fr.json().get("id")
        except Exception as e:
            log.info("VISION files-multipart exc: %s", e)

        # ВАРИАНТ 2: загрузка файла JSON base64
        if not file_id:
            try:
                fr = requests.post(
                    FILES_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"base64_content": b64, "purpose": "general", "filename": "photo.jpg"},
                    timeout=60,
                    verify=False,
                )
                log.info("VISION files-json -> %s %s", fr.status_code, fr.text[:200])
                if fr.status_code == 200:
                    file_id = fr.json().get("id")
            except Exception as e:
                log.info("VISION files-json exc: %s", e)

        # ЧАТ С ATTACHMENTS (Max, затем Pro)
        if file_id:
            msgs = [{"role": "system", "content": VISION_SYSTEM}] + hist_msgs + [{"role": "user", "content": q}]
            for model in ("GigaChat-Max", "GigaChat-Pro"):
                r = _chat(token, msgs, model, [file_id])
                log.info("VISION att-%s -> %s %s", model, r.status_code, r.text[:200])
                if r.status_code == 200:
                    return {"reply": _clean_ans(r.json()["choices"][0]["message"]["content"])}
                errors.append(f"att-{model} {r.status_code}: {r.text[:100]}")

        # ФОЛБЭК: inline base64 в content (Max, затем Pro)
        msgs2 = (
            [{"role": "system", "content": VISION_SYSTEM}]
            + hist_msgs
            + [{"role": "user", "content": [
                {"type": "text", "text": q},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]}]
        )
        for model in ("GigaChat-Max", "GigaChat-Pro"):
            r = _chat(token, msgs2, model)
            log.info("VISION inline-%s -> %s %s", model, r.status_code, r.text[:200])
            if r.status_code == 200:
                return {"reply": _clean_ans(r.json()["choices"][0]["message"]["content"])}
            errors.append(f"inline-{model} {r.status_code}: {r.text[:100]}")

        raise HTTPException(502, "Vision не прошёл: " + " | ".join(errors))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка vision: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "chat_sync": CHAT_FILE.exists()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
