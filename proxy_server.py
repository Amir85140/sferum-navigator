import base64
import json
import logging
import re
import time
import uuid
import urllib.parse
import os
from pathlib import Path
from io import BytesIO

import requests
import urllib3
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

try:
    from PIL import Image, ImageOps, ImageStat
    import pytesseract
    OCR_OK = True
except Exception:
    OCR_OK = False

import db as navigator_db

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("proxy")

GIGA_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
GIGA_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"
OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGA_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
CHAT_FILE = Path("chat_sync.json")
BANK_FILE = Path("bank.json")

MATH_SYSTEM_DEFAULT = (
    "Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно. "
    "Не используй Markdown (**, #, `). Математические формулы пиши в LaTeX: "
    "инлайн в $...$, блочные в $$...$$."
)

app = FastAPI(title="Sferum Navigator Proxy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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


# ===== УЛУЧШЕННЫЙ OCR =====
def _preprocess_variants(img):
    g = img.convert("L")
    w, h = g.size
    out = []
    for scale in (2, 3):
        big = g.resize((w * scale, h * scale), Image.LANCZOS)
        mean = ImageStat.Stat(big).mean[0]
        inv = ImageOps.invert(big) if mean < 128 else big
        ac = ImageOps.autocontrast(big, cutoff=2)
        ac_inv = ImageOps.invert(ac)
        out += [inv.point(lambda p: 255 if p > 140 else 0),
                big.point(lambda p: 255 if p > 140 else 0),
                inv, ac, ac_inv]
    return out


def _ocr_score(t):
    digits = sum(ch.isdigit() for ch in t)
    math = sum(ch in "+-*/=()хxХ^" for ch in t)
    letters = sum(ch.isalpha() for ch in t)
    return digits * 3 + math * 3 + letters


def _ocr_from_base64(image_b64: str) -> str:
    if not OCR_OK:
        raise RuntimeError("Tesseract не установлен")
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    raw = base64.b64decode(image_b64)
    img = Image.open(BytesIO(raw))
    best = ""
    best_score = -1
    for var in _preprocess_variants(img):
        for psm in ("6", "3", "7", "11"):
            try:
                t = pytesseract.image_to_string(var, lang="rus+eng", config=f"--psm {psm}")
            except Exception:
                continue
            t = re.sub(r"\s+", " ", t).strip()
            if len(t) < 2:
                continue
            sc = _ocr_score(t)
            if sc > best_score:
                best_score = sc
                best = t
                if best_score >= 15:
                    return best
    return best


def _load_bank():
    if BANK_FILE.exists():
        try:
            return json.loads(BANK_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


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
    origin = request.headers.get('origin', '-')
    ua = request.headers.get('user-agent', '-')[:60]
    log.info(f"CHAT-IN origin={origin} ua={ua}")
    try:
        payload = await request.json()
        prompt = payload.get("prompt", "")
        system = payload.get("system") or MATH_SYSTEM_DEFAULT
        max_tokens = int(payload.get("max_tokens") or 4000)
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
    origin = request.headers.get('origin', '-')
    ua = request.headers.get('user-agent', '-')[:60]
    log.info(f"VISION-IN origin={origin} ua={ua}")
    try:
        payload = await request.json()
        image_b64 = payload.get("image")
        user_prompt = payload.get("prompt") or "Реши задачу пошагово, с объяснением каждого шага. Формулы пиши простым текстом (a = F / m)."

        if not image_b64:
            raise HTTPException(400, "no image")

        if not OCR_OK:
            raise HTTPException(500, "Tesseract не установлен")

        try:
            text = _ocr_from_base64(image_b64)
        except Exception as e:
            log.error(f"ocr failed: {e}")
            raise HTTPException(500, f"Не удалось распознать изображение: {e}")

        log.info("OCR result: %r", text[:200])

        if len(text) < 2:
            raise HTTPException(400, "На фото нет читаемого текста. Попробуй фото получше (светлый фон, крупный текст).")

        token = await _get_giga_token()
        prompt_full = (
            f"Текст с фото задачи (распознан OCR, возможны мелкие искажения): «{text}»\n\n"
            f"{user_prompt}\n\n"
            f"Если распознанный текст — математическое выражение (например 2 + 2 * 2), просто вычисли его по действиям и дай ответ. "
            f"Если OCR исказил числа/формулы — восстанови их по смыслу и реши."
        )
        msgs = [
            {"role": "system", "content": "Ты — эксперт по школьным задачам. Реши пошагово, объясни каждый шаг. Формулы пиши простым текстом (a = F / m), НЕ используй LaTeX."},
            {"role": "user", "content": prompt_full},
        ]
        r = requests.post(
            GIGA_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": "GigaChat:latest", "messages": msgs, "max_tokens": 3000, "temperature": 0.3},
            timeout=60, verify=False,
        )
        if not r.ok:
            raise HTTPException(r.status_code, f"GigaChat OCR solve error: {r.text[:200]}")
        sol = r.json()["choices"][0]["message"]["content"]
        log.info("VISION ocr+giga OK, text_len=%d", len(text))
        return {"solution": sol, "ocr": text, "model": "GigaChat:latest", "mode": "ocr"}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"vision error: {e}")
        raise HTTPException(500, f"Ошибка vision: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "chat_sync": CHAT_FILE.exists(), "ocr": OCR_OK}


# ===== PER-USER ДАННЫЕ (SQLite) =====
@app.get("/api/state")
async def api_state_get(user_id: str = "main"):
    navigator_db.ensure_user(user_id)
    return JSONResponse(content=navigator_db.get_state(user_id), headers={"Access-Control-Allow-Origin": "*"})


@app.post("/api/state")
async def api_state_post(request: Request, user_id: str = "main"):
    patch = await request.json()
    navigator_db.ensure_user(user_id)
    navigator_db.set_state(user_id, patch or {})
    return JSONResponse(content={"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


@app.get("/api/chat")
async def api_chat_get(user_id: str = "main", limit: int = 50):
    return JSONResponse(content=navigator_db.get_chat(user_id, limit), headers={"Access-Control-Allow-Origin": "*"})


@app.post("/api/chat")
async def api_chat_post(request: Request, user_id: str = "main"):
    m = await request.json()
    navigator_db.append_chat(user_id, m.get("role", "user"), m.get("content", ""), m.get("source", "web"))
    return JSONResponse(content={"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


# ===== ПРОГРЕСС ПО БАНКУ =====
@app.post("/api/progress")
async def api_progress_post(request: Request, user_id: str = "main"):
    m = await request.json()
    navigator_db.save_progress(user_id, m.get("topic_id",""), m.get("task_idx",0), bool(m.get("correct")))
    return JSONResponse(content={"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


@app.get("/api/progress")
async def api_progress_get(user_id: str = "main"):
    return JSONResponse(content=navigator_db.get_progress(user_id), headers={"Access-Control-Allow-Origin": "*"})


# ===== БАНК ЗАДАНИЙ (ФИПИ) =====
@app.get("/api/bank/subjects")
async def bank_subjects():
    bank = _load_bank()
    out = [{"id": k, "title": v.get("title", k)} for k, v in bank.items()]
    return JSONResponse(content=out, headers={"Access-Control-Allow-Origin": "*"})


@app.get("/api/bank/topics")
async def bank_topics(subject: str = ""):
    bank = _load_bank()
    subj = bank.get(subject) or {}
    topics = [{"id": t.get("id"), "title": t.get("title"), "count": len(t.get("tasks", []))}
              for t in subj.get("topics", [])]
    return JSONResponse(content=topics, headers={"Access-Control-Allow-Origin": "*"})


@app.get("/api/bank/tasks")
async def bank_tasks(subject: str = "", topic: str = ""):
    bank = _load_bank()
    subj = bank.get(subject) or {}
    for t in subj.get("topics", []):
        if t.get("id") == topic:
            return JSONResponse(content=t.get("tasks", []), headers={"Access-Control-Allow-Origin": "*"})
    return JSONResponse(content=[], headers={"Access-Control-Allow-Origin": "*"})


# ===== ГЕНЕРАЦИЯ ЗАДАНИЙ ФИПИ (GigaChat) =====
@app.get("/fipi_bank")
async def fipi_bank(exam: str = "ЕГЭ", subject: str = "Математика", year: str = "2024", num: int = 5):
    """Генерация заданий через GigaChat с пуленепробиваемой очисткой от мусора"""
    log.info(f"fipi_bank: exam={exam}, subject={subject}, year={year}, num={num}")
    try:
        token = await _get_giga_token()
        prompt = (
            f"Сгенерируй строго валидный JSON-массив из {num} заданий для {exam} по предмету '{subject}' за {year} год. "
            f"Формат каждого элемента: "
            f'{{"id": 1, "question": "Текст задания", "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"], "correct": 0, "explanation": "Пояснение"}}. '
            f"Верни ТОЛЬКО JSON-массив. Никакого текста до или после."
        )
        msgs = [
            {"role": "system", "content": "Ты — строгий JSON-генератор. Твой ответ ДОЛЖЕН начинаться с '[' и заканчиваться ']'. Никаких приветствий, никаких markdown-оберток."},
            {"role": "user", "content": prompt}
        ]
        r = requests.post(
            GIGA_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": "GigaChat:latest", "messages": msgs, "max_tokens": 4000, "temperature": 0.7},
            timeout=60, verify=False,
        )
        if not r.ok:
            raise HTTPException(r.status_code, f"GigaChat error: {r.text[:200]}")
        
        reply_text = r.json()["choices"][0]["message"]["content"]
        
        # === ПУЛЕНЕПРОБИВАЕМАЯ ОЧИСТКА ===
        start_idx = reply_text.find('[')
        end_idx = reply_text.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_json = reply_text[start_idx:end_idx+1]
        else:
            log.error(f"GigaChat вернул мусор без скобок: {reply_text[:200]}")
            raise HTTPException(500, f"GigaChat не вернул JSON-массив. Ответ: {reply_text[:100]}")
        
        try:
            tasks = json.loads(clean_json)
            if not isinstance(tasks, list):
                raise ValueError("Извлеченный JSON не является массивом")
            return JSONResponse(content=tasks, headers={"Access-Control-Allow-Origin": "*"})
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error: {e}. Cleaned snippet: {clean_json[:300]}")
            raise HTTPException(500, f"Ошибка парсинга JSON: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"fipi_bank error: {e}")
        raise HTTPException(500, f"Ошибка генерации заданий: {str(e)}")


# --- раздача мини-аппа (статика) ---
app.mount('/', StaticFiles(directory=os.path.dirname(os.path.abspath(__file__)), html=True), name='web')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
