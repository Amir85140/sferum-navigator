import requests
import time
import json
from services import AIService

# ТВОЙ РАБОЧИЙ ТОКЕН СООБЩЕСТВА
BOT_TOKEN = "vk1.a.9BNdW2YFQFAa_3mTuZxhfvJQxp8jOHrlzFYs4K9CrLASaKg8qcpDjVNKVI8TOWYUZ_fMCHmSpN_iZAZLFnyp06mGujmxXp_7k3uKACkO4oxT0yCrr8OLICeT47cCOeyHkk10uffc2dJUNl2w75qrkl15n2DB6ZZh1s8vZemIDeEcitMdI8dxV0DlYUjjB-8MjheTED6Lc1zu-1Diztlq-Q"
API_VERSION = "5.131"

MODES = {
    "general": "🤖 Общий",
    "planner": "📅 Подготовка к экзаменам",
    "homework": "📝 Помощь с домашкой",
    "explain": "🎓 Объяснение темы",
    "tests": "✅ Проверка знаний",
    "motivation": "💪 Мотивация",
    "videos": "🎥 Видеоуроки",
    "journal": "📚 Оценки и МЭШ",
    "offline": "📱 Оффлайн материалы"
}

user_modes = {}

def send_message(user_id, text, keyboard=None):
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
    result = response.json()
    if "error" in result:
        print(f"❌ Ошибка VK API: {result['error']}")
    return result

def create_main_keyboard():
    buttons = []
    mode_ids = list(MODES.keys())
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
    text_lower = text.lower().strip()
    
    # Проверка на смену режима
    for mode_id, mode_name in MODES.items():
        if mode_name.lower() in text_lower or mode_id in text_lower:
            user_modes[user_id] = mode_id
            send_message(user_id, f"✅ Выбран режим: {mode_name}\n\nТеперь напиши свой вопрос или задачу!")
            return
    
    mode = user_modes.get(user_id, "general")
    
    # Вызов меню
    if text_lower in ["режимы", "меню", "помощь", "help", "/start", "старт"]:
        keyboard = create_main_keyboard()
        send_message(user_id, "🎯 Привет! Я ИИ-наставник Sferum Navigator.\nВыбери режим для работы:", keyboard=keyboard)
        return
    
    # Отправка запроса в GigaChat
    try:
        response = AIService.process_message(text, mode)
        
        # VK имеет лимит 4096 символов на сообщение, разбиваем если нужно
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                send_message(user_id, part)
        else:
            send_message(user_id, response)
    except Exception as e:
        send_message(user_id, f"❌ Ошибка ИИ: {str(e)}")

def get_long_poll_server():
    url = "https://api.vk.com/method/messages.getLongPollServer"
    params = {
        "access_token": BOT_TOKEN,
        "v": API_VERSION,
        "need_pts": 1
    }
    response = requests.post(url, data=params).json()
    if "response" in response:
        return response["response"]
    else:
        print(f"❌ Ошибка получения сервера: {response}")
        return None

def main():
    print("🚀 Бот Sferum Navigator для MAX запущен!")
    print("Ожидаю сообщения...")
    
    server_data = get_long_poll_server()
    if not server_data:
        print("⛔ Не удалось подключиться. Проверь, включен ли Long Poll в настройках сообщества.")
        return
    
    server = server_data["server"]
    key = server_data["key"]
    ts = server_data["ts"]
    
    print(f"✅ Успешно подключено к серверу Long Poll!")
    
    while True:
        try:
            poll_url = f"https://{server}?act=a_check&key={key}&ts={ts}&wait=25"
            poll_response = requests.get(poll_url).json()
            
            if "failed" in poll_response:
                if poll_response["failed"] == 1:
                    ts = poll_response["ts"]
                elif poll_response["failed"] == 2:
                    server_data = get_long_poll_server()
                    if server_data:
                        server = server_data["server"]
                        key = server_data["key"]
                        ts = server_data["ts"]
                        print("🔄 Переподключение к Long Poll...")
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
                            print(f"📩 [{user_id}]: {text}")
                            handle_message(user_id, text)
            
            ts = poll_response.get("ts", ts)
        except Exception as e:
            print(f"⚠️ Ошибка цикла: {e}")
            time.sleep(5)
            server_data = get_long_poll_server()
            if server_data:
                server = server_data["server"]
                key = server_data["key"]
                ts = server_data["ts"]

if __name__ == "__main__":
    main()
