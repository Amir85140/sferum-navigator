import os
import logging
import json
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
USER_DATA_FILE = Path('user_data.json')

# ===== ХРАНИЛИЩЕ =====
user_data: Dict[int, Dict[str, Any]] = {}

def load_user_data():
    global user_data
    if USER_DATA_FILE.exists():
        try:
            user_data = json.loads(USER_DATA_FILE.read_text(encoding='utf-8'))
            user_data = {int(k): v for k, v in user_data.items()}
        except Exception as e:
            logger.error(f"Failed to load user data: {e}")
            user_data = {}

def save_user_data():
    try:
        USER_DATA_FILE.write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.error(f"Failed to save user data: {e}")

load_user_data()

# ===== СИНХРОНИЗАЦИЯ ЧАТА С МИНИ-АПОМ =====
def save_chat_to_server(user_id: int, history: List[Dict]):
    """Сохраняет историю чата на сервер через прокси"""
    try:
        proxy_url = f"{PROXY_BASE}/chat_history?user_id=user_{user_id}"
        requests.post(proxy_url, json=history[-50:], timeout=5, verify=False)
    except Exception as e:
        logger.error(f"Failed to save chat history: {e}")

def load_chat_from_server(user_id: int) -> List[Dict]:
    """Загружает историю чата с сервера"""
    try:
        proxy_url = f"{PROXY_BASE}/chat_history?user_id=user_{user_id}"
        r = requests.get(proxy_url, timeout=5, verify=False)
        if r.ok:
            return r.json()
    except Exception as e:
        logger.error(f"Failed to load chat history: {e}")
    return []

# ===== GIGACHAT API =====
giga_token = None
giga_exp = 0

def get_giga_token():
    global giga_token, giga_exp
    import time
    import uuid
    if giga_token and time.time() < giga_exp:
        return giga_token
    try:
        auth = f"{GIGA_ID}:{GIGA_SECRET}"
        import base64
        auth_b64 = base64.b64encode(auth.encode()).decode()
        r = requests.post(
            'https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
            headers={
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded',
                'RqUID': str(uuid.uuid4())
            },
            data={'scope': 'GIGACHAT_API_PERS'},
            verify=False,
            timeout=30
        )
        if r.ok:
            data = r.json()
            giga_token = data['access_token']
            giga_exp = time.time() + 1700
            return giga_token
    except Exception as e:
        logger.error(f"Failed to get GigaChat token: {e}")
    return None

def ask_gigachat(prompt: str, system_prompt: str = None, max_tokens: int = 800, history: List[Dict] = None) -> str:
    token = get_giga_token()
    if not token:
        return "❌ Не удалось подключиться к GigaChat"
    try:
        messages = [{'role': 'system', 'content': system_prompt or 'Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно, без LaTeX и Markdown.'}]
        if history:
            messages.extend(history[-16:])
        messages.append({'role': 'user', 'content': prompt})
        
        r = requests.post(
            'https://gigachat.devices.sberbank.ru/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'model': 'GigaChat:latest', 'messages': messages, 'max_tokens': max_tokens, 'temperature': 0.7},
            verify=False,
            timeout=60
        )
        if r.ok:
            data = r.json()
            return data['choices'][0]['message']['content'].replace('**', '').replace('#', '').replace('`', '')
    except Exception as e:
        logger.error(f"GigaChat error: {e}")
    return "❌ Ошибка при обращении к GigaChat"

# ===== БОТ =====
bot = Bot(token=BOT_TOKEN)

@bot.on.message()
async def handle_message(message: types.Message):
    user_id = message.user.user_id
    text = message.body.text or ''
    
    # Инициализация пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            'chat_history': load_chat_from_server(user_id),
            'grades': {}
        }
    
    # Команда /start
    if text.strip() == '/start':
        await message.answer(
            "👋 Привет! Я **Sferum Navigator** — твой ИИ-наставник.\n\n"
            "🤖 Задавай вопросы по учёбе\n"
            "📚 Пиши про оценки — сам запишу в дневник\n"
            "📱 Команда /мини — открою приложение\n\n"
            "Попробуй написать: *«объясни дроби»* или *«математика 5 5 5»*"
        )
        save_user_data()
        return
    
    # Команда /мини
    if text.strip() == '/мини' or text.strip() == '/mini':
        await message.answer(
            f"📱 Открываю мини-приложение Sferum Navigator!\n\n"
            f"Там ты найдёшь:\n"
            f"📅 Персональный план подготовки\n"
            f"✅ Тренажёр с тестами\n"
            f"🎥 Видеоуроки\n"
            f"💪 Мотивацию\n\n"
            f"👉 {MINI_APP_URL}"
        )
        save_user_data()
        return
    
    # Проверка на оценки
    grade_triggers = ['оценк', 'получил', 'получила', 'поставили', 'поставил', 'заработал', 'заработала', 'балл', 'отметк']
    has_grades = any(t in text.lower() for t in grade_triggers)
    has_digits = any(d in text for d in '12345')
    
    if has_grades and has_digits:
        try:
            response = ask_gigachat(
                f'Ученик написал про свои оценки: «{text}». Определи ВСЕ школьные предметы (полные нормальные названия по-русски, с учётом сленга) и список оценок для каждого (числа 1-5). Верни СТРОГО JSON-массив: [{{"subject":"название предмета","grades":[5,4]}}, ...]',
                'Верни только валидный JSON-массив, без пояснений.',
                500
            )
            match = json.loads(response) if response.startswith('[') else None
            if not match:
                import re
                m = re.search(r'\[[\s\S]*\]', response)
                if m:
                    match = json.loads(m.group())
            
            if match and isinstance(match, list):
                for item in match:
                    if 'subject' in item and 'grades' in item and isinstance(item['grades'], list):
                        subject = item['subject']
                        grades = [g for g in item['grades'] if isinstance(g, int) and 1 <= g <= 5]
                        if grades:
                            if subject not in user_data[user_id]['grades']:
                                user_data[user_id]['grades'][subject] = []
                            user_data[user_id]['grades'][subject].extend(grades)
                            
                            await message.answer(f"📚 Записал в дневник: **{subject}** → {', '.join(map(str, grades))}")
                save_user_data()
        except Exception as e:
            logger.error(f"Failed to parse grades: {e}")
    
    # Обычный разговор с GigaChat
    user_data[user_id]['chat_history'].append({'role': 'user', 'content': text, 'timestamp': int(__import__('time').time() * 1000)})
    
    await message.answer("⏳ Думаю...")
    
    response = ask_gigachat(
        text,
        'Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно. Помни весь предыдущий разговор. Если ученик рассказывает про свои оценки — порадуйся или поддержи.',
        800,
        user_data[user_id]['chat_history']
    )
    
    user_data[user_id]['chat_history'].append({'role': 'assistant', 'content': response, 'timestamp': int(__import__('time').time() * 1000)})
    
    # Синхронизация с сервером
    save_chat_to_server(user_id, user_data[user_id]['chat_history'])
    
    await message.answer(response)
    save_user_data()

if __name__ == '__main__':
    logger.info("Bot is starting...")
    bot.run()
