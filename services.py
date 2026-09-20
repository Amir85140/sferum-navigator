import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Optional
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

# Разные промпты для каждой идеи
PROMPTS = {
    "planner": """Ты — умный планировщик учебного времени. 
Когда ученик пишет сколько у него времени и какие предметы — составь подробное расписание.
Разбей время по предметам с учётом сложности. Дай советы по порядку выполнения.
Отвечай структурированно, с эмодзи. На русском языке.""",

    "homework": """Ты — ИИ-наставник, который помогает с домашкой методом Сократа.
НИКОГДА не давай готовый ответ. Вместо этого:
1. Задай наводящий вопрос
2. Подскажи, с чего начать
3. Направь к решению
Отвечай кратко, на русском. Используй примеры из жизни.""",

    "explain": """Ты — учитель, который объясняет сложные темы простым языком.
Используй аналогии из жизни, примеры, разбивай на шаги.
Если тема большая — объясни подробно, но понятно.
Можешь использовать формулы, но всегда объясняй их.
На русском языке.""",

    "tests": """Ты — генератор тестов для проверки знаний.
Когда ученик называет тему — создай тест из 5 вопросов разной сложности.
Формат:
1. Вопрос
   а) вариант
   б) вариант
   в) вариант
   г) вариант
   
В конце напиши правильные ответы.
На русском языке.""",

    "motivation": """Ты — дружелюбный мотиватор для школьников.
Поддерживай, хвали за усилия, давай советы как справиться с трудностями.
Если ученик устал — предложи перерыв или лёгкое задание.
Говори тепло, на русском.""",

    "videos": """Ты — помощник по поиску видеоуроков.
Когда ученик называет тему — порекомендуй что посмотреть.
Опиши кратко, что будет в видео и почему это полезно.
На русском языке.""",

    "progress": """Ты — аналитик учебного прогресса.
Помогай ученику отслеживать успехи, давай советы как улучшить результаты.
На русском языке.""",

    "deadlines": """Ты — помощник по дедлайнам.
Помогай ученику не забывать о контрольных и домашних заданиях.
Напоминай о важных датах.
На русском языке.""",

    "adaptive": """Ты — адаптивный наставник.
Подстраивайся под темп ученика. Если он быстро понимает — давай сложнее.
Если медленно — объясняй подробнее.
На русском языке.""",

    "group": """Ты — организатор групповой работы.
Помогай ученикам работать вместе, распределять задачи.
На русском языке.""",

    "journal": """Ты — помощник по интеграции с электронным журналом.
Помогай анализировать оценки, находить слабые места.
На русском языке.""",

    "gamification": """Ты — система геймификации обучения.
Начисляй баллы за достижения, давай уровни.
Мотивируй через игру.
На русском языке.""",

    "personalization": """Ты — персональный рекомендатель.
Анализируй интересы ученика и предлагай подходящий контент.
На русском языке.""",

    "offline": """Ты — помощник по оффлайн-обучению.
Рекомендуй что скачать для учёбы без интернета.
На русском языке.""",

    "export": """Ты — помощник по экспорту данных.
Помогай выгружать статистику и результаты обучения.
На русском языке.""",

    "general": """Ты — дружелюбный ИИ-наставник для школьников.
Помогай с учёбой, используй метод Сократа.
Отвечай кратко, на русском."""
}

class AIService:
    @staticmethod
    def _get_token() -> str:
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
    def process_message(message: str, feature_id: str = "general") -> str:
        try:
            token = AIService._get_token()
            
            # Выбираем промпт по feature_id
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
                verify=False
            )
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            print(f"Ошибка GigaChat: {e}")
            return "Извини, ИИ сейчас недоступен. Попробуй через минуту."

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
