import requests
import base64
from requests.auth import HTTPBasicAuth
from typing import Dict
import urllib3
import time
import os
import puremagic
from PIL import Image
import io

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = os.environ.get("GIGACHAT_CLIENT_ID", "01a0bafa-206f-7e07-a2e7-df9e0acea285")
CLIENT_SECRET = os.environ.get("GIGACHAT_CLIENT_SECRET", "93e085d7-803b-4fe2-b1da-468aff78a450")

_token_cache = {"token": None, "expires_at": 0}

PROMPTS = {
    "planner": "Ты — умный планировщик подготовки к экзаменам. Помни весь разговор с учеником и учитывай то, что он уже рассказал. Отвечай структурированно, с эмодзи. На русском.",
    "homework": "Ты — ИИ-наставник, помогающий с домашкой методом Сократа. НИКОГДА не давай готовый ответ. Задавай наводящие вопросы. Помни контекст разговора. На русском.",
    "explain": "Ты — учитель, объясняющий сложные темы простым языком. Помни, о чём вы уже говорили, и учитывай это. На русском.",
    "tests": "Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов. В конце напиши правильные ответы. На русском.",
    "motivation": "Ты — дружелюбный мотиватор для школьников. Помни, что ученик рассказывал о себе, и поддерживай его. На русском.",
    "videos": """Ты — помощник по поиску видеоуроков. Дай ссылки на поиск видео по теме ученика.

ВАЖНО: Используй ТОЛЬКО эти форматы поисковых ссылок:
- Поиск на RuTube: https://rutube.ru/search/?q=ТЕМА
- Поиск на VK Видео: https://vk.com/video?q=ТЕМА
- Поиск на YouTube: https://www.youtube.com/results?search_query=ТЕМА

Замени ТЕМА на предмет/тему ученика. На русском языке.""",
    "journal": "Ты — помощник по интеграции с МЭШ. Анализируй оценки. На русском.",
    "offline": """Ты — помощник по оффлайн-обучению. Дай ссылки на проверенные образовательные ресурсы.

ВАЖНО: Используй ТОЛЬКО эти проверенные сайты:
- Фоксфорд: https://foxford.ru
- Решу ЕГЭ: https://ege.sdamgia.ru
- Решу ОГЭ: https://oge.sdamgia.ru
- Учи.ру: https://uchi.ru
- Библиотека МЭШ: https://uchebnik.mos.ru
- Интернетурок: https://interneturok.ru

На русском языке.""",
    "photo": "Ты — ИИ-наставник, который анализирует фотографии заданий, тетрадей, учебников и расписаний. Внимательно рассмотри изображение: прочитай текст, разбери задачу или таблицу. Помоги ученику методом Сократа — задавай наводящие вопросы, не давай готовых ответов. Отвечай на русском.",
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


def detect_image_format(image_bytes: bytes):
    """Автоматически определяет формат изображения"""
    try:
        magic_result = puremagic.from_string(image_bytes)
        
        format_map = {
            'jpeg': ('image.jpg', 'image/jpeg'),
            'jpg': ('image.jpg', 'image/jpeg'),
            'png': ('image.png', 'image/png'),
            'webp': ('image.webp', 'image/webp'),
            'gif': ('image.gif', 'image/gif'),
            'bmp': ('image.bmp', 'image/bmp'),
        }
        
        for ext, (filename, mime) in format_map.items():
            if ext in magic_result.lower():
                print(f"🔍 Определён формат: {ext.upper()} ({mime})")
                return filename, mime
        
        print(f"⚠️ Формат не определён ({magic_result}), используем JPEG")
        return 'image.jpg', 'image/jpeg'
        
    except Exception as e:
        print(f"⚠️ Ошибка определения формата: {e}, используем JPEG")
        return 'image.jpg', 'image/jpeg'


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

    @staticmethod
    def process_image(image_bytes: bytes, question: str = "", history: list = None) -> str:
        """Анализ фото через GigaChat с предварительной загрузкой файла"""
        try:
            token = _get_token()
        except Exception as e:
            return f"Не удалось получить токен: {str(e)}"
        
        user_text = question if question.strip() else "Рассмотри это изображение. Прочитай текст, разбери задачу и помоги ученику с учёбой."
        system_prompt = PROMPTS.get("photo")
        
        # Конвертируем изображение в JPEG и сжимаем
        try:
            print("🔄 Конвертация и сжатие изображения...")
            img = Image.open(io.BytesIO(image_bytes))
            
            # Уменьшаем размер если слишком большое
            max_size = 1024
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                print(f"   Уменьшено до {img.size}")
            
            # Если изображение с прозрачностью (RGBA) — конвертируем в RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Сохраняем в JPEG с более сильным сжатием
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=75, optimize=True)
            image_bytes = buffer.getvalue()
            
            print(f"✅ Конвертировано в JPEG ({len(image_bytes)} байт)")
            
            filename = 'image.jpg'
            mime_type = 'image/jpeg'
            
        except Exception as e:
            print(f"⚠️ Ошибка конвертации: {e}")
            filename, mime_type = detect_image_format(image_bytes)
        
        # Загружаем файл в GigaChat
        try:
            print("📤 Загрузка файла в GigaChat...")
            
            files = {
                'file': (filename, image_bytes, mime_type)
            }
            data = {
                'purpose': 'general'
            }
            
            response = requests.post(
                url="https://gigachat.devices.sberbank.ru/api/v1/files",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=data,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"⚠️ Ошибка загрузки файла: {response.status_code}")
                print(f"   Ответ: {response.text[:200]}")
                return ("🖼️ Я вижу, ты прислал фото!\n\n"
                        "К сожалению, не удалось загрузить изображение для анализа.\n"
                        "Но ты можешь перепечатать текст задания сюда — и я помогу его решить! 🙌")
            
            file_data = response.json()
            file_id = file_data.get('id')
            
            if not file_id:
                print(f"⚠️ Не получен file_id. Ответ: {file_data}")
                return "Не удалось обработать фото. Попробуй ещё раз."
            
            print(f"✅ Файл загружен! ID: {file_id}")
            
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
            return ("🖼️ Я вижу, ты прислал фото!\n\n"
                    "К сожалению, произошла ошибка при загрузке.\n"
                    "Но ты можешь перепечатать текст задания сюда — и я помогу его решить! 🙌")
        
        # Отправляем запрос с file_id (с увеличенным таймаутом и ретраями)
        max_retries = 2
        for attempt in range(max_retries):
            try:
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    messages.extend(history)
                
                user_message = {
                    "role": "user",
                    "content": user_text,
                    "attachments": [
                        {
                            "file_id": file_id
                        }
                    ]
                }
                messages.append(user_message)
                
                print(f"🤖 Отправка запроса с файлом (попытка {attempt+1}/{max_retries})...")
                
                response = requests.post(
                    url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "model": "GigaChat:latest",
                        "messages": messages,
                        "max_tokens": 600,
                        "temperature": 0.5
                    },
                    verify=False,
                    timeout=90  # Увеличили с 45 до 90 секунд
                )
                
                print(f"   Статус: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0].get('message', {}).get('content', '')
                        if content:
                            print(f"✅ Фото проанализировано! ({len(content)} символов)")
                            return content
                
                print(f"⚠️ Ошибка анализа: {response.text[:200]}")
                
                if attempt < max_retries - 1:
                    print("   Пробуем ещё раз через 3 секунды...")
                    time.sleep(3)
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"⏱️ Таймаут (попытка {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    print("   Пробуем ещё раз через 5 секунд...")
                    time.sleep(5)
                    continue
            except Exception as e:
                print(f"⚠️ Ошибка анализа: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
        
        return ("🖼️ Я вижу, ты прислал фото!\n\n"
                "К сожалению, анализ занял слишком много времени.\n"
                "Попробуй отправить фото ещё раз или перепечатай текст задания! 🙌")


class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        time_per_subject = available_minutes // len(subjects)
        schedule = [{"subject": subj, "time_allocated": f"{time_per_subject} мин", "advice": "Начни с теории, потом реши 2 задачи."} for subj in subjects]
        return {"total_time": available_minutes, "schedule": schedule}
