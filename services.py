import requests
import base64
from requests.auth import HTTPBasicAuth
from typing import Dict
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

_token_cache = {"token": None, "expires_at": 0}

IMAGE_MODELS = ["GigaChat:latest", "GigaChat-Pro:latest", "GigaChat:latest-preview", "GigaChat-Max:latest"]

PROMPTS = {
    "planner": "Ты — умный планировщик подготовки к экзаменам. Помни весь разговор с учеником и учитывай то, что он уже рассказал. Отвечай структурированно, с эмодзи. На русском.",
    "homework": "Ты — ИИ-наставник, помогающий с домашкой методом Сократа. НИКОГДА не давай готовый ответ. Задавай наводящие вопросы. Помни контекст разговора. На русском.",
    "explain": "Ты — учитель, объясняющий сложные темы простым языком. Помни, о чём вы уже говорили, и учитывай это. На русском.",
    "tests": "Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов. В конце напиши правильные ответы. На русском.",
    "motivation": "Ты — дружелюбный мотиватор для школьников. Помни, что ученик рассказывал о себе, и поддерживай его. На русском.",
    "videos": """Ты — помощник по поиску видеоуроков. Дай ссылки на поиск видео по теме ученика.

ВАЖНО: Используй ТОЛЬКО эти форматы поисковых ссылок (они гарантированно работают):
- Поиск на RuTube: https://rutube.ru/search/?q=ТЕМА
- Поиск на VK Видео: https://vk.com/video?q=ТЕМА
- Поиск на YouTube: https://www.youtube.com/results?search_query=ТЕМА

Замени ТЕМА на предмет/тему ученика.

Формат ответа:
🎥 Видеоуроки по теме "{тема}":
1. **Поиск на RuTube**: https://rutube.ru/search/?q=...
2. **Поиск на VK Видео**: https://vk.com/video?q=...
3. **Поиск на YouTube**: https://www.youtube.com/results?search_query=...

На русском языке.""",
    "progress": "Ты — аналитик учебного прогресса. На русском.",
    "deadlines": "Ты — помощник по дедлайнам. На русском.",
    "adaptive": "Ты — адаптивный наставник. На русском.",
    "group": "Ты — организатор групповой работы. На русском.",
    "journal": "Ты — помощник по интеграции с МЭШ. Анализируй оценки. На русском.",
    "gamification": "Ты — система геймификации. На русском.",
    "personalization": "Ты — персональный рекомендатель. На русском.",
    "offline": """Ты — помощник по оффлайн-обучению. Дай ссылки на проверенные образовательные ресурсы.

ВАЖНО: Используй ТОЛЬКО эти проверенные сайты (они гарантированно работают):
- Фоксфорд: https://foxford.ru
- Решу ЕГЭ: https://ege.sdamgia.ru
- Решу ОГЭ: https://oge.sdamgia.ru
- Учи.ру: https://uchi.ru
- Библиотека МЭШ: https://uchebnik.mos.ru
- Интернетурок: https://interneturok.ru

Формат ответа:
📚 Материалы для обучения по теме "{тема}":
1. **{Название ресурса}**: {ссылка}
   📝 {краткое описание}

На русском языке.""",
    "export": "Ты — помощник по экспорту данных. На русском.",
    "photo": "Ты — ИИ-наставник, который анализирует фотографии заданий, тетрадей, учебников и расписаний. Внимательно рассмотри изображение: прочитай текст, разбери задачу или таблицу. Затем помоги ученику. Отвечай на русском.",
    "general": "Ты — дружелюбный ИИ-наставник для школьников. Помни весь контекст разговора и учитывай его в ответах. Помогай с учёбой. На русском."
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
    "gamification": ["достижен", "уровен", "балл", "ачивк", "рейтинг"],
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


def detect_mode(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for mode_id, keywords in MODE_KEYWORDS.items():
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
                print(f"🤖 Запрос к GigaChat (попытка {attempt+1}/{max_retries}, режим: {feature_id}, история: {len(history) if history else 0} сообщ.)")
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
                    print(f"⚠️ GigaChat вернул {response.status_code}, пробуем ещё раз...")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return "Извини, ИИ сейчас недоступен. Попробуй через минуту."
                
                result = response.json()
                
                if isinstance(result, dict) and 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    if isinstance(choice, dict) and 'message' in choice:
                        msg = choice['message']
                        if isinstance(msg, dict) and 'content' in msg:
                            content = msg['content']
                            if content:
                                print(f"✅ Ответ получен ({len(content)} символов)")
                                return content
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "Извини, не удалось получить ответ от ИИ."
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return "Извини, ИИ не ответил вовремя. Попробуй ещё раз."
            except Exception as e:
                print(f"⚠️ Ошибка GigaChat (попытка {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"Извини, произошла ошибка: {str(e)}"
        
        return "Извини, ИИ временно недоступен. Попробуй позже."

    @staticmethod
    def process_image(image_bytes: bytes, question: str = "", history: list = None) -> str:
        """Пробует несколько моделей, чтобы найти ту, что умеет читать фото"""
        try:
            token = _get_token()
        except Exception as e:
            return f"Не удалось получить токен: {str(e)}"
        
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        img_data_url = f"data:image/jpeg;base64,{img_b64}"
        user_text = question if question.strip() else "Рассмотри это изображение. Прочитай текст, разбери задачу и помоги ученику с учёбой."
        system_prompt = PROMPTS.get("photo")
        
        user_content = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": img_data_url}}
        ]
        
        for model in IMAGE_MODELS:
            try:
                print(f"🖼️ Пробуем модель {model}...")
                
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": user_content})
                
                response = requests.post(
                    url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": 600,
                        "temperature": 0.5
                    },
                    verify=False,
                    timeout=45
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0].get('message', {}).get('content', '')
                        if content:
                            print(f"✅ Модель {model} прочитала фото! ({len(content)} символов)")
                            return content
                else:
                    print(f"⚠️ Модель {model} вернула {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                print(f"⚠️ Модель {model} не сработала: {e}")
                continue
        
        return ("🖼️ Я вижу, ты прислал фото!\n\n"
                "К сожалению, на текущем тарифе модель не может прочитать изображение.\n"
                "Но ты можешь перепечатать текст задания сюда — и я помогу его решить! 🙌")


class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        time_per_subject = available_minutes // len(subjects)
        schedule = [{"subject": subj, "time_allocated": f"{time_per_subject} мин", "advice": "Начни с теории, потом реши 2 задачи."} for subj in subjects]
        return {"total_time": available_minutes, "schedule": schedule}
