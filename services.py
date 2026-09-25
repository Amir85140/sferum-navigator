import requests
from requests.auth import HTTPBasicAuth
from typing import Dict
import urllib3
import time
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = os.environ.get("GIGACHAT_CLIENT_ID", "01a0bafa-206f-7e07-a2e7-df9e0acea285")
CLIENT_SECRET = os.environ.get("GIGACHAT_CLIENT_SECRET", "93e085d7-803b-4fe2-b1da-468aff78a450")

_token_cache = {"token": None, "expires_at": 0}

PROMPTS = {
    "planner": """Ты — умный планировщик подготовки к экзаменам. 

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.

Отвечай структурированно, с эмодзи. На русском.""",

    "homework": """Ты — ИИ-наставник, помогающий с домашкой методом Сократа. 

ВАЖНО: 
- НИКОГДА не давай готовый ответ
- Задавай наводящие вопросы
- Ты помнишь ВЕСЬ разговор с учеником
- Если ученик спрашивает "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте

На русском.""",

    "explain": """Ты — учитель, объясняющий сложные темы простым языком.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.

На русском.""",

    "tests": """Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов. В конце напиши правильные ответы.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

На русском.""",

    "motivation": """Ты — дружелюбный мотиватор для школьников.

ВАЖНО: 
- Ты помнишь ВЕСЬ разговор с учеником
- Всегда учитывай контекст предыдущих сообщений
- Если ученик хвалит тебя ("ты молодец", "спасибо") и потом спрашивает "знаешь почему?" — отвечай в контексте его похвалы
- Задавай уточняющие вопросы, если контекст неясен

На русском.""",

    "videos": """Ты — помощник по поиску видеоуроков. Дай ссылки на поиск видео по теме ученика.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

Используй ТОЛЬКО эти форматы поисковых ссылок:
- Поиск на RuTube: https://rutube.ru/search/?q=ТЕМА
- Поиск на VK Видео: https://vk.com/video?q=ТЕМА
- Поиск на YouTube: https://www.youtube.com/results?search_query=ТЕМА

Замени ТЕМА на предмет/тему ученика. На русском языке.""",

    "journal": """Ты — помощник по интеграции с МЭШ. Анализируй оценки.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

На русском.""",

    "offline": """Ты — помощник по оффлайн-обучению. Дай ссылки на проверенные образовательные ресурсы.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

Используй ТОЛЬКО эти проверенные сайты:
- Фоксфорд: https://foxford.ru
- Решу ЕГЭ: https://ege.sdamgia.ru
- Решу ОГЭ: https://oge.sdamgia.ru
- Учи.ру: https://uchi.ru
- Библиотека МЭШ: https://uchebnik.mos.ru
- Интернетурок: https://interneturok.ru

На русском языке.""",

    "context": """Ты — дружелюбный ИИ-наставник для школьников.

КРИТИЧЕСКИ ВАЖНО: Ученик задаёт вопрос, который относится к предыдущему сообщению в разговоре.
Внимательно прочитай историю разговора и пойми, о чём именно спрашивает ученик.

Примеры:
- Если ученик сказал "Ты молодец!" и потом спрашивает "Знаешь почему?" — он спрашивает, почему ты молодец
- Если ученик сказал "Мне не нравится математика" и потом спрашивает "Почему?" — он спрашивает, почему ему не нравится математика
- Если ученик задал вопрос и потом спрашивает "Что именно?" — он просит уточнить

Отвечай в контексте предыдущего разговора. Задавай уточняющие вопросы, если контекст неясен.

На русском.""",

    "general": """Ты — дружелюбный ИИ-наставник для школьников.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.

Помогай с учёбой. На русском."""
}

MODE_KEYWORDS = {
    "planner": ["план", "расписан", "подготов", "экзамен", "огэ", "егэ", "контрольн", "сколько времени"],
    "homework": ["домашк", "дз", "задач", "упражнен", "решить"],
    "explain": ["объясни", "что такое", "как работает", "расскажи про", "почему"],
    "tests": ["тест", "проверь", "викторин", "квиз"],
    "motivation": ["устал", "не хочу", "лень", "мотивац", "скучно", "тяжело"],
    "videos": ["видео", "урок", "посмотреть", "ролик", "ютуб", "youtube", "rutube", "ссылк"],
    "journal": ["оценк", "журнал", "мэш", "четверт", "полугод"],
    "offline": ["оффлайн", "скачать", "без интернета", "материал", "сайт", "ресурс", "учебник"],
    "context": ["почему", "зачем", "что именно", "знаешь", "понимаешь", "объясни", "уточни"],
}


def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]
    print("🔑 Получение нового токена GigaChat...")
    for attempt in range(3):
        try:
            response = requests.post(
                url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded", "RqUID": "00000000-0000-0000-0000-000000000000"},
                data="scope=GIGACHAT_API_PERS",
                verify=False,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            _token_cache["token"] = data["access_token"]
            _token_cache["expires_at"] = now + 1700
            print("✅ Токен получен и закэширован")
            return _token_cache["token"]
        except Exception as e:
            print(f"⚠️ Попытка {attempt+1} получения токена не удалась: {e}")
            time.sleep(2)
    raise Exception("Не удалось получить токен GigaChat после 3 попыток")


def detect_mode(text: str, has_history: bool = False) -> str:
    """Определяет режим работы бота"""
    text_lower = text.lower().strip()
    
    # Если сообщение очень короткое и есть история — скорее всего это контекстный вопрос
    if has_history and len(text_lower) < 30:
        context_keywords = ["почему", "зачем", "что", "как", "когда", "где", "знаешь", "понимаешь"]
        if any(kw in text_lower for kw in context_keywords):
            print(f"🎯 Определён контекстный вопрос (короткое сообщение с историей)")
            return "context"
    
    scores = {}
    for mode_id, keywords in MODE_KEYWORDS.items():
        if mode_id == "context":  # Пропускаем context в обычном поиске
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[mode_id] = score
    
    if scores:
        best_mode = max(scores, key=scores.get)
        print(f"🎯 Режим определён по ключевым словам: {best_mode}")
        return best_mode
    
    return "general"


class AIService:
    @staticmethod
    def process_message(message: str, feature_id: str = "general", history: list = None) -> str:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🤖 Запрос к GigaChat (режим: {feature_id}, история: {len(history) if history else 0} сообщ.)")
                token = _get_token()
                system_prompt = PROMPTS.get(feature_id, PROMPTS["general"])
                
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": message})
                
                response = requests.post(
                    url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "model": "GigaChat:latest",
                        "messages": messages,
                        "max_tokens": 600,
                        "temperature": 0.7
                    },
                    verify=False,
                    timeout=30
                )
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return "Извини, ИИ сейчас недоступен. Попробуй через минуту."
                
                result = response.json()
                
                if isinstance(result, dict) and 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0].get('message', {}).get('content', '')
                    if content:
                        print(f"✅ Ответ получен ({len(content)} символов)")
                        return content
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "Извини, не удалось получить ответ от ИИ."
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"⏱️ Таймаут (попытка {attempt+1}), пробуем ещё раз...")
                    time.sleep(3)
                    continue
                return "Извини, ИИ не ответил вовремя. Попробуй ещё раз."
            except Exception as e:
                print(f"⚠️ Ошибка GigaChat: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"Извини, произошла ошибка: {str(e)}"
        
        return "Извини, ИИ временно недоступен. Попробуй позже."


class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        time_per_subject = available_minutes // len(subjects)
        schedule = [{"subject": subj, "time_allocated": f"{time_per_subject} мин", "advice": "Начни с теории, потом реши 2 задачи."} for subj in subjects]
        return {"total_time": available_minutes, "schedule": schedule}
