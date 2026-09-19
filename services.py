import requests
import time
from typing import Dict, Optional

# ⚠️ ВСТАВЬ СЮДА СВОЙ КЛЮЧ ВМЕСТО hf_ТВОЙ_КЛЮЧ_СЮДА (кавычки оставь!)
HF_API_TOKEN = "hf_ТВОЙ_КЛЮЧ_СЮДА"

API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"
headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

SYSTEM_PROMPT = """Ты — дружелюбный ИИ-наставник для школьников «Сферум Навигатор». 
Твоя цель: помогать с учёбой, но НЕ давать готовых ответов на домашку. 
Используй метод Сократа: задавай наводящие вопросы, помогай разобраться в теме.
Отвечай кратко (2-3 предложения), понятно и поддерживающе. Отвечай только на русском языке."""

class AIService:
    @staticmethod
    def process_message(message: str, user_context: Optional[Dict] = None) -> str:
        try:
            context_text = ""
            if user_context and user_context.get("last_topic"):
                context_text = f"Ученик только что смотрел видео по теме: {user_context['last_topic']}. "

            # Формат запроса для модели Qwen
            full_prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{context_text}{message}<|im_end|>\n<|im_start|>assistant\n"

            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }

            # Делаем запрос к нейросети
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            # ️ ЕСЛИ МОДЕЛЬ "СПИТ" (ОШИБКА 503), ЖДЕМ 20 СЕКУНД И ПРОБУЕМ СНОВА
            if response.status_code == 503:
                time.sleep(20) 
                response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
                
            response.raise_for_status()
            result = response.json()
            
            # Извлекаем текст ответа
            if isinstance(result, list) and len(result) > 0:
                return result[0]['generated_text'].strip()
            else:
                return "Нейросеть вернула странный ответ. Попробуй перефразировать вопрос."
                
        except Exception as e:
            print(f"Ошибка API: {e}")
            return "Извини, мой ИИ-мозг сейчас перегружен. Подожди 10 секунд и попробуй снова, или напиши 'помощь'."

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
