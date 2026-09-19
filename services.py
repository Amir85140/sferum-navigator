import requests
from typing import Dict, Optional
import base64

# ⚠️ ВСТАВЬ СЮДА СВОИ ДАННЫЕ ОТ GIGACHAT
CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "MDFhMGJhZmEtMjA2Zi03ZTA3LWEyZTctZGY5ZTBhY2VhMjg1OmZlZmUwOTYzLWNlNDQtNGUwZS1iYWM5LWVlMTZlOGJiODc3MQ=="

# URL для получения токена
TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
# URL для запросов к GigaChat
API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

SYSTEM_PROMPT = """Ты — дружелюбный ИИ-наставник для школьников «Сферум Навигатор». 
Твоя цель: помогать с учёбой, но НЕ давать готовых ответов на домашку. 
Используй метод Сократа: задавай наводящие вопросы, помогай разобраться в теме.
Если ученик просит составить план, спроси, сколько у него времени и какие предметы.
Отвечай кратко (2-4 предложения), понятно и поддерживающе. Только на русском языке."""

class AIService:
    @staticmethod
    def _get_token() -> str:
        """Получает OAuth-токен от GigaChat"""
        credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {"scope": "GIGACHAT_API_PERS"}
        
        response = requests.post(TOKEN_URL, headers=headers, data=data, verify=False)
        response.raise_for_status()
        return response.json()["access_token"]

    @staticmethod
    def process_message(message: str, user_context: Optional[Dict] = None) -> str:
        try:
            # Получаем токен
            token = AIService._get_token()
            
            context_text = ""
            if user_context and user_context.get("last_topic"):
                context_text = f"Ученик только что смотрел видео по теме: {user_context['last_topic']}. "

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "GigaChat:latest",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{context_text}{message}"}
                ],
                "max_tokens": 200,
                "temperature": 0.7
            }

            response = requests.post(API_URL, headers=headers, json=payload, verify=False, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            print(f"Ошибка GigaChat: {e}")
            return "Извини, ИИ сейчас недоступен. Попробуй через минуту или напиши 'помощь'."

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
                "advice": f"Начни с самого сложного задания по предмету '{subj}'."
            })
        return {"total_time": available_minutes, "schedule": schedule}
