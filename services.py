import requests
from typing import Dict, Optional

# ВСТАВЬ СЮДА СВОЙ КЛЮЧ ОТ HUGGING FACE (начинается на hf_)
HF_API_TOKEN = "hf_ВСТАВЬ_СЮДА_СВОЙ_ДЛИННЫЙ_КЛЮЧ"

# Используем бесплатную и быструю модель, которая отлично знает русский язык
API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

SYSTEM_PROMPT = """Ты — дружелюбный ИИ-наставник для школьников «Сферум Навигатор». 
Твоя цель: помогать с учёбой, но НЕ давать готовых ответов на домашку. 
Используй метод Сократа: задавай наводящие вопросы, помогай разобраться в теме.
Если ученик просит составить план, спроси, сколько у него времени и какие предметы.
Отвечай кратко (максимум 3-4 предложения), понятно и поддерживающе."""

class AIService:
    @staticmethod
    def process_message(message: str, user_context: Optional[Dict] = None) -> str:
        """Отправляет сообщение в бесплатную нейросеть Hugging Face"""
        try:
            context_text = ""
            if user_context and user_context.get("last_topic"):
                context_text = f"Ученик только что смотрел видео по теме: {user_context['last_topic']}. "

            full_prompt = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{context_text}Сообщение ученика: {message}\n<|assistant|>\n"

            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": 150, # Ограничиваем длину ответа, чтобы было быстро
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }

            response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            # Hugging Face возвращает список, берем первый элемент и текст
            if isinstance(result, list) and len(result) > 0:
                return result[0]['generated_text'].strip()
            else:
                return "Не удалось сгенерировать ответ, попробуй перефразировать вопрос."
                
        except Exception as e:
            # Если нейросеть перегружена (бесплатный тариф иногда ждет), бот не падает!
            print(f"Ошибка API: {e}")
            return "Сейчас мой ИИ-мозг немного перегружен другими учениками. Подожди 10 секунд и попробуй снова, или напиши 'помощь'."

class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        """Логика планировщика остается простой и надежной"""
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
