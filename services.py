import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Optional
import urllib3

# Отключаем предупреждения о SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ✅ ТВОИ РАБОЧИЕ КЛЮЧИ ОТ GIGACHAT
CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

SYSTEM_PROMPT = """Ты — дружелюбный ИИ-наставник для школьников «Сферум Навигатор». 
Твоя цель: помогать с учёбой, но НЕ давать готовых ответов на домашку. 
Используй метод Сократа: задавай наводящие вопросы, помогай разобраться в теме.
Если ученик просит составить план, спроси, сколько у него времени и какие предметы.
Отвечай кратко (2-4 предложения), понятно и поддерживающе. Только на русском языке."""

class AIService:
    @staticmethod
    def _get_token() -> str:
        """Получает токен от GigaChat"""
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
        return response.json()["access_token"]

    @staticmethod
    def process_message(message: str, user_context: Optional[Dict] = None) -> str:
        """Отправляет сообщение в GigaChat и возвращает ответ"""
        try:
            # Получаем токен
            token = AIService._get_token()
            
            # Формируем контекст
            context_text = ""
            if user_context and user_context.get("last_topic"):
                context_text = f"Ученик только что смотрел видео по теме: {user_context['last_topic']}. "

            # Отправляем запрос в GigaChat
            response = requests.post(
                url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "GigaChat:latest",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"{context_text}{message}"}
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7
                },
                verify=False
            )
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            print(f"Ошибка GigaChat: {e}")
            return "Извини, ИИ сейчас недоступен. Попробуй через минуту или напиши 'помощь'."

class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        """Генерация расписания"""
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        
        time_per_subject = available_minutes // len(subjects)
        schedule = []
        
        for subj in subjects:
            schedule.append({
                "subject": subj,
                "time_allocated": f"{time_per_subject} мин",
                "advice": f"Начни с теории, потом реши 2 задачи. Если останется время — перейди к '{subj}'."
            })
        return {"total_time": available_minutes, "schedule": schedule}
