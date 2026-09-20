from typing import Dict, Optional
from gigachat import GigaChat

# ⚠️ ВАЖНО: Вставь свои данные в формате "Client_ID:Client_Secret"
# Без пробелов до и после двоеточия!
CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

# Собираем строку для авторизации
CREDENTIALS = f"{CLIENT_ID}:{CLIENT_SECRET}"

SYSTEM_PROMPT = """Ты — дружелюбный ИИ-наставник для школьников «Сферум Навигатор». 
Твоя цель: помогать с учёбой, но НЕ давать готовых ответов на домашку. 
Используй метод Сократа: задавай наводящие вопросы, помогай разобраться в теме.
Отвечай кратко (2-4 предложения), понятно и поддерживающе. Только на русском языке."""

class AIService:
    @staticmethod
    def process_message(message: str, user_context: Optional[Dict] = None) -> str:
        try:
            context_text = ""
            if user_context and user_context.get("last_topic"):
                context_text = f"Ученик только что смотрел видео по теме: {user_context['last_topic']}. "

            # Используем официальную библиотеку GigaChat
            # verify_ssl_certs=False ОБЯЗАТЕЛЕН для работы в Codespaces
            with GigaChat(credentials=CREDENTIALS, verify_ssl_certs=False) as giga:
                response = giga.chat(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"{context_text}{message}"}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                return response.choices[0].message.content
                
        except Exception as e:
            error_msg = str(e)
            # Если ошибка в авторизации, подскажем пользователю (для тебя)
            if "401" in error_msg or "400" in error_msg:
                print("❌ ОШИБКА АВТОРИЗАЦИИ: Проверь, нет ли пробелов в Client ID или Secret!")
            
            return "Извини, мой ИИ-мозг сейчас перезагружается. Попробуй задать вопрос через 10 секунд!"

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
