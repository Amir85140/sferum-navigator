import requests
import time
import json
from services import AIService

BOT_TOKEN = "vk1.a.9BNdW2YFQFAa_3mTuZxhfvJQxp8jOHrlzFYs4K9CrLASaKg8qcpDjVNKVI8TOWYUZ_fMCHmSpN_iZAZLFnyp06mGujmxXp_7k3uKACkO4oxT0yCrr8OLICeT47cCOeyHkk10uffc2dJUNl2w75qrkl15n2DB6ZZh1s8vZemIDeEcitMdI8dxV0DlYUjjB-8MjheTED6Lc1zu-1Diztlq-Q"
API_VERSION = "5.131"

MODES = {
    "general": "🤖 Общий",
    "planner": "📅 Подготовка к экзаменам",
    "homework": " Помощь с домашкой",
    "explain": "🎓 Объяснение темы",
    "tests": "✅ Проверка знаний",
    "motivation": "💪 Мотивация",
    "videos": "🎥 Видеоуроки",
    "journal": "📚 Оценки и МЭШ",
    "offline": "📱 Оффлайн материалы"
}

user_modes = {}

def send_message(user_id, text):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": BOT_TOKEN,
        "peer_id": user_id,
        "message": text,
        "random_id": int(time.time() * 1000),
        "v": API_VERSION
    }
    response = requests.post(url, data=params)
    result = response.json()
    if "error" in result:
        print(f"❌ Ошибка VK API: {result['error']}")
    return result

def handle_message(user_id, text):
    text_lower = text.lower().strip()
    
    # Проверка на смену режима
    for mode_id, mode_name in MODES.items():
        if mode_name.lower() in text_lower or mode_id in text_lower:
            user_modes[user_id] = mode_id
            send_message(user_id, f"✅ Выбран режим: {mode_name}\n\nТеперь напиши свой вопрос!")
            return
    
    mode = user_modes.get(user_id, "general")
    
    # Вызов меню
    if text_lower in ["режимы", "меню", "помощь", "help", "/start", "старт"]:
        menu_text = "🎯 Привет! Я ИИ-наставник Sferum Navigator.\n\nВыбери режим, написав его название:\n\n"
        for mode_id, mode_name in MODES.items():
            menu_text += f"• {mode_name} (напиши: {mode_id})\n"
        menu_text += "\nИли просто задай вопрос — я отвечу в текущем режиме."
        send_message(user_id, menu_text)
        return
    
    # Отправка в GigaChat
    try:
        response = AIService.process_message(text, mode)
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
        "lp_version": "3"
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
        print("⛔ Не удалось подключиться.")
        return
    
    server = server_data["server"]
    key = server_data["key"]
    ts = server_data["ts"]
    
    print(f"✅ Подключено к Long Poll! ts={ts}")
    
    while True:
        try:
            poll_url = f"https://{server}?act=a_check&key={key}&ts={ts}&wait=25&mode=2&version=3"
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
                        print("🔄 Переподключение...")
                elif poll_response["failed"] == 3:
                    ts = poll_response["ts"]
                continue
            
            if "updates" in poll_response:
                for update in poll_response["updates"]:
                    if not isinstance(update, list):
                        continue
                    
                    event_type = update[0]
                    
                    if event_type == 4:
                        flags = update[1]
                        peer_id = update[3]
                        
                        if flags & 2:
                            text = ""
                            if len(update) > 5:
                                text = update[5] if isinstance(update[5], str) else ""
                            
                            if text and text != "":
                                print(f"📩 [{peer_id}]: {text}")
                                handle_message(peer_id, text)
            
            ts = poll_response.get("ts", ts)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)
            server_data = get_long_poll_server()
            if server_data:
                server = server_data["server"]
                key = server_data["key"]
                ts = server_data["ts"]

if __name__ == "__main__":
    main()
