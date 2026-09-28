import os
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
from max_sdk import Bot, types

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'AgAEAAEAAAAAAAAAAAAAAABgJmUAAAAAYmY0YjEwZjEtNjQ2OC00MjVlLTg2ZDctMjM5ZjQ3ZjQ3ZjQ3')
GIGA_ID = os.environ.get('GIGA_ID', '01a0bafa-206f-7e07-a2e7-df9e0acea285')
GIGA_SECRET = os.environ.get('GIGA_SECRET', '93e085d7-803b-4fe2-b1da-468aff78a450')
CODESPACE_NAME = os.environ.get('CODESPACE_NAME', 'automatic-system-p7gg76p4wqqwf99rj')
PROXY_BASE = f"https://{CODESPACE_NAME}-8000.app.github.dev"
MINI_APP_URL = "https://amir85140.github.io/sferum-navigator/"
CHANNEL = 'main'                      # общий канал чата для MAX и мини-апа
USER_DATA_FILE = Path('user_data.json')

user_data: Dict[int, Dict[str, Any]] = {}

def load_user_data():
    global user_data
    if USER_DATA_FILE.exists():
        try:
            raw = json.loads(USER_DATA_FILE.read_text(encoding='utf-8'))
            user_data = {int(k): v for k, v in raw.items()}
        except Exception as e:
            logger.error(f"load user_data: {e}")
            user_data = {}

def save_user_data():
    try:
        USER_DATA_FILE.write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.error(f"save user_data: {e}")

load_user_data()

def now_ms():
    return int(time.time() * 1000)

# ===== ОБЩИЙ ЧАТ-КАНАЛ НА СЕРВЕРЕ =====
def load_chat_from_server(channel=CHANNEL) -> List[Dict]:
    try:
        r = requests.get(f"{PROXY_BASE}/chat_history?user_id={channel}", timeout=5, verify=False)
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.error(f"load chat: {e}")
    return []

def save_chat_to_server(history: List[Dict], channel=CHANNEL):
    try:
        requests.post(f"{PROXY_BASE}/chat_history?user_id={channel}",
                      json=history[-50:], timeout=5, verify=False)
    except Exception as e:
        logger.error(f"save chat: {e}")

# ===== GIGACHAT =====
giga_token = None
giga_exp = 0

def get_giga_token():
    global giga_token, giga_exp
    if giga_token and time.time() < giga_exp:
        return giga_token
    try:
        auth_b64 = base64.b64encode(f"{GIGA_ID}:{GIGA_SECRET}".encode()).decode()
        r = requests.post(
            'https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
            headers={'Authorization': f'Basic {auth_b64}',
                     'Content-Type': 'application/x-www-form-urlencoded',
                     'RqUID': str(uuid.uuid4())},
            data={'scope': 'GIGACHAT_API_PERS'},
            verify=False, timeout=30)
        if r.ok:
            giga_token = r.json()['access_token']
            giga_exp = time.time() + 1700
            return giga_token
    except Exception as e:
        logger.error(f"token: {e}")
    return None

def ask_gigachat(prompt: str, system_prompt: str = None, max_tokens: int = 800, history: List[Dict] = None) -> str:
    token = get_giga_token()
    if not token:
        return "❌ Не удалось подключиться к GigaChat"
    try:
        messages = [{'role': 'system',
                     'content': system_prompt or 'Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно, без LaTeX-блоков и Markdown.'}]
        if history:
            messages.extend(history[-16:])
        messages.append({'role': 'user', 'content': prompt})
        r = requests.post(
            'https://gigachat.devices.sberbank.ru/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'model': 'GigaChat:latest', 'messages': messages,
                  'max_tokens': max_tokens, 'temperature': 0.7},
            verify=False, timeout=60)
        if r.ok:
            return r.json()['choices'][0]['message']['content'].replace('**', '').replace('`', '')
    except Exception as e:
        logger.error(f"giga: {e}")
    return "❌ Ошибка при обращении к GigaChat"

# ===== БОТ =====
bot = Bot(token=BOT_TOKEN)

@bot.on.message()
async def handle_message(message: types.Message):
    user_id = message.user.user_id
    text = (message.body.text or '').strip()

    if user_id not in user_data:
        user_data[user_id] = {'grades': {}}

    # /start
    if text == '/start':
        await message.answer(
            "👋 Привет! Я **Sferum Navigator** — твой ИИ-наставник.\n\n"
            "🔄 Наш чат ОБЩИЙ с мини-приложением: пиши здесь — увидишь на сайте, пиши на сайте — увижу здесь.\n"
            "📚 Пиши про оценки — сам запишу в дневник\n"
            "📱 /мини — открыть приложение\n"
            "📜 /история — общий чат\n"
            "🗑 /очистить — очистить общий чат")
        return

    # /мини
    if text in ('/мини', '/mini'):
        await message.answer(f"📱 Мини-приложение Sferum Navigator:\n{MINI_APP_URL}\n\nЧат там синхронизирован с этим диалогом 🔄")
        return

    # /история
    if text == '/история':
        hist = load_chat_from_server()
        if not hist:
            await message.answer("Общий чат пока пуст.")
            return
        lines = []
        for m in hist[-10:]:
            who = '🧑' if m.get('role') == 'user' else '🤖'
            src = ' (сайт)' if m.get('source') == 'web' else (' (MAX)' if m.get('source') == 'max' else '')
            lines.append(f"{who}{src}: {m.get('content','')[:120]}")
        await message.answer("📜 Последние сообщения общего чата:\n" + "\n".join(lines))
        return

    # /очистить
    if text == '/очистить':
        save_chat_to_server([])
        await message.answer("🗑 Общий чат очищен (и в MAX, и на сайте).")
        return

    # оценки -> дневник (локально у бота)
    grade_triggers = ['оценк', 'получил', 'получила', 'поставили', 'поставил', 'заработал', 'балл', 'отметк']
    if any(t in text.lower() for t in grade_triggers) and re.search(r'\b[1-5]\b', text):
        try:
            resp = ask_gigachat(
                f'Ученик написал про оценки: «{text}». Определи ВСЕ предметы и оценки. Верни СТРОГО JSON-массив: [{{"subject":"...","grades":[5,4]}}]',
                'Верни только валидный JSON-массив.', 500)
            m = re.search(r'\[[\s\S]*\]', resp)
            if m:
                for item in json.loads(m.group()):
                    subj = item.get('subject')
                    grades = [g for g in item.get('grades', []) if isinstance(g, int) and 1 <= g <= 5]
                    if subj and grades:
                        user_data[user_id]['grades'].setdefault(subj, []).extend(grades)
                        await message.answer(f"📚 Записал в дневник: **{subj}** → {', '.join(map(str, grades))}")
                save_user_data()
        except Exception as e:
            logger.error(f"grades parse: {e}")

    # ===== ОБЩИЙ ЧАТ: читаем серверную историю (включая сообщения с сайта) =====
    history = load_chat_from_server()
    history.append({'role': 'user', 'content': text, 'timestamp': now_ms(), 'source': 'max'})

    thinking = await message.answer("⏳ Думаю...")
    response = ask_gigachat(
        text,
        'Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно. Помни ВЕСЬ предыдущий разговор, включая сообщения с сайта. Если ученик рассказывает про оценки — порадуйся или поддержи.',
        800, history)
    history.append({'role': 'assistant', 'content': response, 'timestamp': now_ms(), 'source': 'max'})

    save_chat_to_server(history)

    try:
        await thinking.delete()
    except Exception:
        pass
    await message.answer(response)

if __name__ == '__main__':
    logger.info("Bot starting...")
    bot.run()
