from datetime import datetime
from typing import List, Dict, Optional

# База видеоуроков (RuTube и VK)
VIDEO_DATABASE = {
    "Математика": {
        "Квадратные уравнения": {"url": "https://rutube.ru/video/abc123", "duration": 15},
        "Производные": {"url": "https://rutube.ru/video/def456", "duration": 20}
    },
    "Русский язык": {
        "Синтаксис": {"url": "https://vk.com/video/ghi789", "duration": 18}
    }
}

class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: List[str]) -> Dict:
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        
        time_per_subject = available_minutes // len(subjects)
        schedule = []
        
        for subj in subjects:
            topic = list(VIDEO_DATABASE.get(subj, {}).keys())[0] if subj in VIDEO_DATABASE else "Общая тема"
            schedule.append({
                "subject": subj,
                "topic": topic,
                "time_allocated": f"{time_per_subject} мин",
                "video_link": VIDEO_DATABASE.get(subj, {}).get(topic, {}).get("url", "Нет видео")
            })
        return {"total_time": available_minutes, "schedule": schedule}

class AIService:
    @staticmethod
    def process_message(message: str) -> str:
        msg = message.lower()
        if "не понял" in msg or "объясни" in msg:
            return "Какую тему ты смотрел? Напиши, и я объясню простыми словами."
        if "ответ" in msg or "реши" in msg:
            return "Я не даю готовых ответов, но помогу разобраться! Напиши условие задачи."
        if "тест" in msg:
            return "Отлично! Давай проверим знания. По какому предмету хочешь тест?"
        return "Я твой ИИ-наставник. Спроси меня про домашку или попроси составить план!"
