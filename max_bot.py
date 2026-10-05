import os
import asyncio
import logging
import json
import time
import base64
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List
import requests
import urllib3
from maxapi import Bot, Dispatcher

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'f9LHodD0cOLAk1Ry-yn7J-4F5oi3mZW9vlXyawwC4SxvVwTZ3DILUsVm6QJhFo2e3ReJ-0ucg1NORcMQ_FNI')
GIGA_ID = os.environ.get('GIGA_ID', '01a0bafa-206f-7e07-a2e7-df9e0acea285')
GIGA_SECRET = os.environ.get('GIGA_SECRET', '93e085d7-803b-4fe2-b1da-468aff78a450')
CODESPACE_NAME = os.environ.get('CODESPACE_NAME', 'automatic-system-p7gg76p4wqqwf99rj')
PROXY_BASE = f"https://{CODESPACE_NAME}-8000.app.github.dev"
CHANNEL = 'main'
USER_DATA_FILE = Path('user_data.json')

NO_LATEX = (' СТРОГО ЗАПРЕЩЕНО использовать LaTeX (знаки $, $$, \\frac, \\sqrt и любые бэкслэши) '
            'и Markdown (**, #, `). Все формулы пиши ПРОСТЫМ текстом в одну строку.')

SYS_CHAT = ('Ты — Sferum Navigator, ИИ-наставник для школьников 5-11 классов. Правила:\n'
            '1) Отвечай СТРОГО на вопрос ученика.\n'
            '2) Учебная тема — дай краткое объяснение сути + один пример.\n'
            '3) Формулы пиши простым текстом (a = F / m).\n'
            '4) Отвечай коротко, до 10 строк.')

user_data: Dict[int, Dict[str, Any]] = {}

def load_user_data():
    global user_data
    if USER_DATA_FILE.exists():
        try:
            raw = json.loads(USER_DATA_FILE.read_text(encoding='utf-8'))
            user_data = {int(k): v for k, v in raw.items()}
        except Exception as e:
            logger.error(f"load user_data: {e}")

def save_user_data():
    try:
        USER_DATA_FILE.write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.error(f"save user_data: {e}")

load_user_data()

def now_ms():
    return int(time.time() * 1000)

def load_chat_from_server(channel=CHANNEL):
    try:
        r = requests.get(f"{PROXY_BASE}/chat_history?user_id={channel}", timeout=5, verify=False)
        if r.ok and isinstance(r.json(), list):
            return r.json()
    except Exception as e:
        logger.error(f"load chat: {e}")
    return []

def save_chat_to_server(history, channel=CHANNEL):
    try:
        requests.post(f"{PROXY_BASE}/chat_history?user_id={channel}", json=history[-50:], timeout=5, verify=False)
    except Exception as e:
        logger.error(f"save chat: {e}")

def latex_to_plain(t):
    if not t: return t
    s = t.replace('\\cdot', '*').replace('\\times', '*').replace('\\div', '/')
    s = s.replace('\\left', '').replace('\\right', '').replace('\\pi', 'пи')
    s = re.sub(r'\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'(\1) / (\2)', s)
    s = re.sub(r'\\sqrt\s*\{([^{}]*)\}', r'sqrt(\1)', s)
    s = s.replace('$$', ' ').replace('$', '').replace('**', '').replace('`', '')
    return s.strip()

giga_token, giga_exp = None, 0

def get_giga_token():
    global giga_token, giga_exp
    if giga_token and time.time() < giga_exp: return giga_token
    try:
        auth_b64 = base64.b64encode(f"{GIGA_ID}:{GIGA_SECRET}".encode()).decode()
        r = requests.post('https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
            headers={'Authorization': f'Basic {auth_b64}', 'Content-Type': 'ls', 'RqUID': str(uuid.uuid4())},
            data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=30)
        if r.ok:
            giga_token = r.json()['access_token']
            giga_exp = time.time() + 1700
            return giga_token
    except Exception as e:
        logger.error(f"token: {e}")
    return None

def ask_gigachat(prompt, system_prompt=None, max_tokens=800, history=None):
    sysp = (system_prompt or SYS_CHAT) + NO_LATEX
    hist = history or []
    for base in ('http://localhost:8000', PROXY_BASE):
        try:
            r = requests.post(base + '/chat', json={'prompt': prompt, 'system': sysp, 'max_tokens': max_tokens, 'history': hist}, timeout=75, verify=False)
            if r.ok and r.json().get('reply'):
                return latex_to_plain(r.json().get('reply', ''))
        except Exception as e:
            logger.error(f"chat via {base}: {e}")
    token = get_giga_token()
    if not token: return "❌ Не удалось подключиться к GigaChat"
    try:
        messages = [{'role': 'system', 'content': sysp}] + hist[-16:] + [{'role': 'user', 'content': prompt}]
        r = requests.post('https://gigachat.devices.sberbank.ru/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'model': 'GigaChat:latest', 'messages': messages, 'max_tokens': max_tokens, 'temperature': 0.7},
            verify=False, timeout=60)
        if r.ok:
            return latex_to_plain(r.json()['choices'][0]['message']['content'])
    except Exception as e:
        logger.error(f"giga direct: {e}")
    return "❌ Ошибка при обращении к GigaChat"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_uid(event):
    for src in (getattr(event, 'from_user', None), getattr(event, 'user', None), getattr(getattr(event, 'message', None), 'sender', None)):
        if src:
            for attr in ('user_id', 'id'):
                v = getattr(src, attr, None)
                if v is not None:
                    try: return int(v)
                    except: pass
    return 0

def get_text(event):
    m = getattr(event, 'message', None)
    if m:
        for attr in ('body', 'text'):
            v = getattr(m, attr, None)
            if isinstance(v, str): return v.strip()
            if v is not None and isinstance(getattr(v, 'text', None), str): return getattr(v, 'text').strip()
    return ''

async def reply(event, text, keyboard=None):
    cid = getattr(event, 'chat_id', None) or getattr(getattr(event, 'message', None), 'chat_id', None)
    uid = get_uid(event)
    for kw in ([{'chat_id': cid}] if cid else []) + ([{'user_id': uid}] if uid else []):
        try:
            return await bot.send_message(text=text, **kw)
        except: pass
    m = getattr(event, 'message', None)
    if m and callable(getattr(m, 'answer', None)):
        try: return await m.answer(text)
        except: pass

@dp.message_created()
async def handle_message(event):
    user_id = get_uid(event)
    text = get_text(event)
    
    # ===== ОТЛАДКА ФОТО =====
    msg = getattr(event, 'message', None)
    if msg:
        logger.info("=== НАЧАЛО СООБЩЕНИЯ ===")
        logger.info(f"TEXT: {text}")
        logger.info(f"MSG OBJECT: {msg}")
        atts = getattr(msg, 'attachments', None) or getattr(msg, 'attachment', None) or []
        logger.info(f"ATTACHMENTS: {atts}")
        logger.info("=== КОНЕЦ СООБЩЕНИЯ ===")

    # Пока просто отвечаем на текст, чтобы ты видел, что бот жив
    if text:
        await reply(event, f"Я получил текст: '{text}'. Отправь фото, и я покажу его структуру в терминале!")
    else:
        await reply(event, "Я получил сообщение без текста. Смотри терминал, там распечаталась структура фото!")

if __name__ == '__main__':
    logger.info("Bot starting with DEBUG mode...")
    try:
        asyncio.run(dp.start_polling(bot))
    except AttributeError:
        try: dp.run(bot)
        except AttributeError: bot.run()
