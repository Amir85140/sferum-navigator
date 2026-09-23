import requests
from requests.auth import HTTPBasicAuth
from typing import Dict
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

# Кэш токена (живёт ~30 минут)
_token_cache = {"token": None, "expires_at": 0}

PROMPTS = {
    "planner": "Ты — умный планировщик подготовки к экзаменам. Сначала спроси: к чему готовишься, в какие дни, сколько времени, какие предметы. Потом составь расписание. Отвечай структурированно, с эмодзи. На русском.",
    "homework": "Ты — ИИ-наставник, помогающий с домашкой методом Сократа. НИКОГДА не давай готовый ответ. Задавай наводящие вопросы. На русском.",
    "explain": "Ты — учитель, объясняющий сложные темы простым языком. Используй аналогии, примеры, разбивай на шаги. На русском.",
    "tests": "Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов. В конце напиши правильные ответы. На русском.",
    "motivation": "Ты — дружелюбный мотиватор для школьников. Поддерживай, хвали, давай советы. На русском.",
    "videos": "Ты — помощник по поиску видеоуроков. Дай ссылки на RuTube или VK Видео по теме. Формат: 🎥 Название  Ссылка 📝 Описание. На русском.",
    "progress": "Ты — аналитик учебного прогресса. На русском.",
    "deadlines": "Ты — помощник по дедлайнам. На русском.",
    "adaptive": "Ты — адаптивный наставник. На русском.",
    "group": "Ты — организатор групповой работы. На русском.",
    "journal": "Ты — помощник по интеграции с МЭШ. Анализируй оценки. На русском.",
    "gamification": "Ты — система геймификации. На русском.",
    "personalization": "Ты — персональный рекомендатель. На русском.",
    "offline": "Ты — помощник по оффлайн-обучению. Дай ссылки на материалы для скачивания. На русском.",
    "export": "Ты — помощник по экспорту данных. На русском.",
    "general": "Ты — дружелюбный ИИ-наставник для школьников. Помогай с учёбой. На русском."
}

MODE_KEYWORDS = {
    "planner": ["план", "расписан", "подготов", "экзамен", "огэ", "егэ", "контрольн", "сколько времени", "когда учить"],
    "homework": ["домашк", "дз", "задач", "упражнен", "решить", "помоги с домаш"],
    "explain": ["объясни", "что такое", "как работает", "расскажи про", "почему", "тема"],
    "tests": ["тест", "проверь", "викторин", "квиз", "вопрос"],
    "motivation": ["устал", "не хочу", "лень", "мотивац", "скучно", "тяжело", "помоги"],
    "videos": ["видео", "урок", "посмотреть", "youtube", "rutube", "vk видео", "ссылк"],
    "journal": ["оценк", "журнал", "мэш", "четверт", "полугод", "год", "средний балл"],
    "offline": ["оффлайн", "скачать", "без интернета", "материал", "pdf"],
    "gamification": ["достижен", "уровен", "балл", "ачивк", "рейтинг"],
}


def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]
    
    print("🔑 Получение нового токена GigaChat...")
    response = requests.post(
        url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": "00000000-0000-0000-0000-000000000000"
        },
        data="scope=GIGACHAT_API_PERS",
        verify=False,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + 1700
    print("✅ Токен получен и закэширован")
    return _token_cache["token"]


def detect_mode(text: str) -> str:
    text_lower = text.lower()
    
    scores = {}
    for mode_id, keywords in MODE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[mode_id] = score
    
    if scores:
        best_mode = max(scores, key=scores.get)
        print(f" Режим определён по ключевым словам: {best_mode}")
        return best_mode
    
    print(" Определяю режим через ИИ...")
    try:
        token = _get_token()
        mode_list = ", ".join(MODE_KEYWORDS.keys())
        
        response = requests.post(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "model": "GigaChat:latest",
                "messages": [
                    {"role": "system", "content": f"Ты классификатор. Определи режим по тексту пользователя. Доступные режимы: {mode_list}. Ответь ТОЛЬКО одним словом — ID режима. Если не подходит ни один — ответь 'general'."},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            },
            verify=False,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            detected = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip().lower()
            if detected in MODE_KEYWORDS or detected == "general":
                print(f"🎯 Режим определён через ИИ: {detected}")
                return detected
    except Exception as e:
        print(f"⚠️ Не удалось определить режим через ИИ: {e}")
    
    print("🎯 Режим по умолчанию: general")
    return "general"


class AIService:
    @staticmethod
    def process_message(message: str, feature_id: str = "general") -> str:
        try:
            print(f"🤖 Запрос к GigaChat (режим: {feature_id}): '{message[:50]}...'")
            
            token = _get_token()
            system_prompt = PROMPTS.get(feature_id, PROMPTS["general"])

            response = requests.post(
                url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "GigaChat:latest",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7
                },
                verify=False,
                timeout=20
            )
            
            if response.status_code != 200:
                print(f"❌ GigaChat ошибка {response.status_code}: {response.text[:200]}")
                return "Извини, ИИ сейчас недоступен. Попробуй через минуту."
            
            result = response.json()
            
            if isinstance(result, dict) and 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0].get('message', {}).get('content', '')
                if content:
                    print(f"✅ Ответ получен ({len(content)} символов)")
                    return content
            
            return "Извини, не удалось получить ответ от ИИ."
            
        except requests.exceptions.Timeout:
            print("❌ Таймаут GigaChat")
            return "Извини, ИИ не ответил вовремя. Попробуй ещё раз."
        except Exception as e:
            print(f"❌ Ошибка GigaChat: {e}")
            return f"Извини, произошла ошибка: {str(e)}"


class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        time_per_subject = available_minutes // len(subjects)
        schedule = [{"subject": subj, "time_allocated": f"{time_per_subject} мин", "advice": "Начни с теории, потом реши 2 задачи."} for subj in subjects]
        return {"total_time": available_minutes, "schedule": schedule}
