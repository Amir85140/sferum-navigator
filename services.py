import requests
from requests.auth import HTTPBasicAuth
from typing import Dict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

PROMPTS = {
    "planner": """Ты — умный планировщик подготовки к экзаменам.
Сначала спроси: к чему готовишься, в какие дни, сколько времени, какие предметы.
Потом составь расписание. Отвечай структурированно, с эмодзи. На русском.""",

    "homework": """Ты — ИИ-наставник, помогающий с домашкой методом Сократа.
НИКОГДА не давай готовый ответ. Задавай наводящие вопросы. На русском.""",

    "explain": """Ты — учитель, объясняющий сложные темы простым языком.
Используй аналогии, примеры, разбивай на шаги. На русском.""",

    "tests": """Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов.
В конце напиши правильные ответы. На русском.""",

    "motivation": """Ты — дружелюбный мотиватор для школьников.
Поддерживай, хвали, давай советы. На русском.""",

    "videos": """Ты — помощник по поиску видеоуроков.
Дай ссылки на RuTube или VK Видео по теме. На русском.""",

    "progress": """Ты — аналитик учебного прогресса. На русском.""",

    "deadlines": """Ты — помощник по дедлайнам. На русском.""",

    "adaptive": """Ты — адаптивный наставник. На русском.""",

    "group": """Ты — организатор групповой работы. На русском.""",

    "journal": """Ты — помощник по интеграции с МЭШ. На русском.""",

    "gamification": """Ты — система геймификации. На русском.""",

    "personalization": """Ты — персональный рекомендатель. На русском.""",

    "offline": """Ты — помощник по оффлайн-обучению. Дай ссылки на материалы. На русском.""",

    "export": """Ты — помощник по экспорту данных. На русском.""",

    "general": """Ты — дружелюбный ИИ-наставник для школьников. На русском."""
}

class AIService:
    @staticmethod
    def _get_token() -> str:
        print("🔑 Получение токена GigaChat...")
        response = requests.post(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "RqUID": "00000000-0000-0000-0000-000000000000"
            },
            data="scope=GIGACHAT_API_PERS",
            verify=False
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ Токен получен")
        return data["access_token"]

    @staticmethod
    def process_message(message: str, feature_id: str = "general") -> str:
        try:
            print(f"🤖 Запрос к GigaChat: '{message[:50]}...' (режим: {feature_id})")
            
            token = AIService._get_token()
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
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                verify=False,
                timeout=30
            )
            
            print(f" Статус ответа GigaChat: {response.status_code}")
            
            # Проверяем статус
            if response.status_code != 200:
                error_text = response.text[:200]
                print(f"❌ GigaChat вернул ошибку {response.status_code}: {error_text}")
                return f"Извини, ИИ сейчас недоступен (ошибка {response.status_code}). Попробуй через минуту."
            
            result = response.json()
            print(f"📦 Получен ответ: {type(result)}")
            
            # Проверяем структуру ответа
            if isinstance(result, str):
                print(f"️ GigaChat вернул строку вместо JSON: {result[:100]}")
                return result
            
            if not isinstance(result, dict):
                print(f"⚠️ Неожиданный тип ответа: {type(result)}")
                return "Извини, ИИ вернул неожиданный формат ответа."
            
            # Извлекаем текст
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]
                if isinstance(choice, dict) and 'message' in choice:
                    message_obj = choice['message']
                    if isinstance(message_obj, dict) and 'content' in message_obj:
                        content = message_obj['content']
                        print(f"✅ Ответ получен: {content[:100]}...")
                        return content
                    else:
                        print(f"⚠️ message не содержит content: {message_obj}")
                else:
                    print(f"⚠️ choice не содержит message: {choice}")
            else:
                print(f"⚠️ Ответ не содержит choices: {result}")
            
            # Если не удалось извлечь текст — возвращаем весь ответ
            return str(result)
            
        except requests.exceptions.Timeout:
            print("❌ Таймаут GigaChat")
            return "Извини, ИИ не ответил вовремя. Попробуй ещё раз."
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Ошибка соединения с GigaChat: {e}")
            return "Извини, не удалось подключиться к ИИ."
        except Exception as e:
            print(f"❌ Неожиданная ошибка GigaChat: {e}")
            import traceback
            traceback.print_exc()
            return f"Извини, произошла ошибка: {str(e)}"

class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        
        time_per_subject = available_minutes // len(subjects)
        schedule = []
        
        for subj in subjects:
            schedule.append({
                "subject": subj,
                "time_allocated": f"{time_per_subject} мин",
                "advice": f"Начни с теории, потом реши 2 задачи."
            })
        return {"total_time": available_minutes, "schedule": schedule}
