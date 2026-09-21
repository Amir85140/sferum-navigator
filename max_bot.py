import requests
import time
import json
from services import AIService

# Токен бота MAX/VK
BOT_TOKEN = "f9LHodD0cOL_CTMQchAMtDovrgVanr2B904VleKpipLF22l4DnPeJKVTxWHLpDJi6VgmKRgGvRvRg4-2w8Mp"
API_VERSION = "5.131"

# Режимы бота (кнопки)
MODES = {
    "general": "🤖 Общий",
    "planner": "📅 Подготовка к экзаменам",
    "homework": " Помощь с домашкой",
    "explain": "🎓 Объяснение темы",
    "tests": "✅ Проверка знаний",
    "motivation": "💪 Мотивация",
    "videos": "🎥 Видеоуроки",
    "journal": "📚 Оценки и МЭШ",
    "offline": " Оффлайн материалы"
}

# Хранилище режимов пользователей
user_modes = {}

def send_message(user_id, text, keyboard=None):
    """Отправка сообщения пользователю"""
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": BOT_TOKEN,
        "user_id": user_id,
        "message": text,
        "random_id": int(time.time() * 1000),
        "v": API_VERSION
    }
    if keyboard:
        params["keyboard"] = json.dumps(keyboard)
    
    response = requests.post(url, data=params)
    return response.json()

def create_main_keyboard():
    """Главная клавиатура с режимами"""
    buttons = []
    mode_ids = list(MODES.keys())
    
    # По 2 кнопки в ряд
    for i in range(0, len(mode_ids), 2):
        row = []
        for mode_id in mode_ids[i:i+2]:
            row.append({
                "action": {
                    "type": "text",
                    "label": MODES[mode_id]
                }
            })
        buttons.append(row)
    
    return {
        "one_time": False,
        "buttons": buttons
    }

def handle_message(user_id, text):
    """Обработка сообщения"""
    text_lower = text.lower().strip()
    
    # Проверяем, не выбор ли это режима
    for mode_id, mode_name in MODES.items():
        if mode_name.lower() in text_lower or mode_id in text_lower:
            user_modes[user_id] = mode_id
            send_message(user_id, f"✅ Выбран режим: {mode_name}\n\nТеперь напиши свой вопрос, и я помогу тебе в этом режиме!")
            return
    
    # Определяем режим пользователя
    mode = user_modes.get(user_id, "general")
    
    # Если пользователь написал "режимы" или "меню"
    if text_lower in ["режимы", "меню", "помощь", "help", "/start"]:
        keyboard = create_main_keyboard()
        send_message(user_id, "🎯 Выбери режим:", keyboard=keyboard)
        return
    
    # Отправляем в GigaChat
    try:
        response = AIService.process_message(text, mode)
        
        # Разбиваем длинные сообщения (VK лимит 4096 символов)
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                send_message(user_id, part)
        else:
            send_message(user_id, response)
    except Exception as e:
        send_message(user_id, "❌ Ошибка: " + str(e))

def get_long_poll_server():
    """Получение сервера Long Poll"""
    url = "https://api.vk.com/method/messages.getLongPollServer"
    params = {
        "access_token": BOT_TOKEN,
        "v": API_VERSION
    }
    response = requests.post(url, data=params).json()
    return response["response"]

def main():
    """Главный цикл бота"""
    print("🤖 Бот Sferum Navigator для MAX запущен!")
    print("Ожидаю сообщения...")
    
    # Получаем сервер Long Poll
    server_data = get_long_poll_server()
    server = server_data["server"]
    key = server_data["key"]
    ts = server_data["ts"]
    
    print(f"Подключено к серверу: {server}")
    
    while True:
        try:
            # Опрашиваем Long Poll
            poll_url = f"https://{server}?act=a_check&key={key}&ts={ts}&wait=25"
            poll_response = requests.get(poll_url).json()
            
            if "failed" in poll_response:
                if poll_response["failed"] == 1:
                    ts = poll_response["ts"]
                elif poll_response["failed"] == 2:
                    server_data = get_long_poll_server()
                    server = server_data["server"]
                    key = server_data["key"]
                    ts = server_data["ts"]
                    print("Переподключение к Long Poll...")
                elif poll_response["failed"] == 3:
                    ts = poll_response["ts"]
                continue
            
            if "updates" in poll_response:
                for event in poll_response["updates"]:
                    if event["type"] == "message_new":
                        message = event["object"]["message"]
                        user_id = message["from_id"]
                        text = message.get("text", "")
                        
                        if text:
                            print(f"[{user_id}]: {text}")
                            handle_message(user_id, text)
            
            ts = poll_response.get("ts", ts)
            
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)
            try:
                server_data = get_long_poll_server()
                server = server_data["server"]
                key = server_data["key"]
                ts = server_data["ts"]
            except:
                pass

if __name__ == "__main__":
    main()
