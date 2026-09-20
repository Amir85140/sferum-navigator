import json
import time
import requests
from services import AIService

# Токен бота (мы получим его позже, пока оставь так)
BOT_TOKEN = "ТВОЙ_ТОКЕН_БОТА"

def send_message(user_id, text, button_url=None):
    """Функция отправки сообщения. Если есть ссылка - добавляет кнопку Mini App."""
    
    # Формируем текст и кнопки
    message_data = {
        "user_id": user_id,
        "message": text,
        "random_id": int(time.time())
    }
    
    # Если нам передали ссылку на Mini App, создаем кнопку
    if button_url:
        keyboard = {
            "one_time": False,
            "buttons": [
                [
                    {
                        "action": {
                            "type": "open_link",
                            "link": button_url,
                            "label": "🚀 Открыть Mini App"
                        }
                    }
                ]
            ]
        }
        message_data["keyboard"] = json.dumps(keyboard)

    # Отправляем запрос к API бота
    requests.post(
        "https://api.vk.com/method/messages.send",
        params={
            "access_token": BOT_TOKEN,
            "v": "5.131",
            **message_data
        }
    )

def handle_message(user_id, text):
    """Логика бота: что отвечать на сообщения"""
    
    # 1. Отвечаем с помощью ИИ (GigaChat)
    ai_response = AIService.process_message(text)
    
    # 2. Ссылка на наш Mini App (веб-интерфейс)
    mini_app_url = "https://твоя-ссылка-на-codespaces.app.github.dev"
    
    # 3. Отправляем ответ ИИ + кнопку для открытия Mini App
    send_message(user_id, ai_response, button_url=mini_app_url)

# Здесь будет код запуска бота (мы добавим его, когда получим токен)
print("Код бота готов! Он умеет отвечать через ИИ и отправлять кнопку Mini App.")
