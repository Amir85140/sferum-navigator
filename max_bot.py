import requests
import time
import json
from services import AIService

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

def send_message(peer_id, text):
    print(f"📤 Отправка в VK (peer_id={peer_id}): {text[:80]}...")
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": BOT_TOKEN,
        "peer_id": peer_id,
        "message": text,
        "random_id": int(time.time() * 1000),
        "v": API_VERSION
    }
    try:
        response = requests.post(url, data=params, timeout=10)
        result = response.json()
        if "error" in result:
            print(f"❌ Ошибка VK: {result['error']}")
        else:
            print(f"✅ Успешно отправлено!")
        return result
    except Exception as e:
        print(f"⚠️ Ошибка сети VK: {e}")

def handle_message(peer_id, text):
    print(f"\n{'='*50}")
    print(f"📩 Получено от {peer_id}: '{text}'")
    
    text = str(text).strip()
    text_lower = text.lower()
    
    # Тест ИИ
    if text_lower == "тест ии":
        print("🧪 Запуск прямого теста GigaChat...")
        try:
            raw_response = AIService.process_message("Скажи просто 'Привет, я работаю!'", "general")
            print(f"🧪 Сырой ответ от GigaChat: {raw_response}")
            send_message(peer_id, f"Тест ИИ:\n{raw_response}")
        except Exception as e:
            print(f"❌ Ошибка теста: {e}")
            send_message(peer_id, f"Ошибка теста: {e}")
        return

    # Смена режима
    for mode_id, mode_name in MODES.items():
        if mode_name.lower() in text_lower or mode_id in text_lower:
            user_modes[peer_id] = mode_id
            print(f" Смена режима на: {mode_name}")
            send_message(peer_id, f"✅ Выбран режим: {mode_name}\nТеперь задай вопрос!")
            return
    
    mode = user_modes.get(peer_id, "general")
    
    # Меню
    if text_lower in ["режимы", "меню", "помощь", "help", "/start", "старт"]:
        menu = "🎯 Выбери режим (напиши название):\n\n"
        for mid, mname in MODES.items():
            menu += f"• {mname} ({mid})\n"
        menu += "\nИли напиши 'тест ии' для проверки связи."
        send_message(peer_id, menu)
        return
    
    # Запрос к ИИ
    print(f"🤖 Запрос к GigaChat (режим: {mode})...")
    try:
        response = AIService.process_message(text, mode)
        print(f"✅ Ответ GigaChat: {response[:100]}...")
        
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                send_message(peer_id, response[i:i+4000])
        else:
            send_message(peer_id, response)
    except Exception as e:
        print(f"❌ Ошибка GigaChat: {e}")
        send_message(peer_id, f"Ошибка ИИ: {e}")

def get_long_poll_server():
    url = "https://api.vk.com/method/messages.getLongPollServer"
    params = {
        "access_token": BOT_TOKEN,
        "v": API_VERSION,
        "lp_version": "3"
    }
    resp = requests.post(url, data=params).json()
    if "response" in resp:
        return resp["response"]
    else:
        print(f"❌ Ошибка получения сервера: {resp}")
        return None

def main():
    print("🚀 Бот запущен! Ожидаю сообщения...")
    server_data = get_long_poll_server()
    if not server_data:
        print("⛔ Ошибка подключения к Long Poll!")
        return
    
    server = server_data["server"]
    key = server_data["key"]
    ts = server_data["ts"]
    print(f"✅ Long Poll подключен! ts={ts}\n")
    
    debug_count = 0  # Для отладки первых 3 событий
    
    while True:
        try:
            poll_url = f"https://{server}?act=a_check&key={key}&ts={ts}&wait=25&mode=2&version=3"
            poll_resp = requests.get(poll_url, timeout=30).json()
            
            if "failed" in poll_resp:
                if poll_resp["failed"] == 1: ts = poll_resp["ts"]
                elif poll_resp["failed"] == 2:
                    server_data = get_long_poll_server()
                    if server_data:
                        server, key, ts = server_data["server"], server_data["key"], server_data["ts"]
                        print("🔄 Переподключение...")
                elif poll_resp["failed"] == 3: ts = poll_resp["ts"]
                continue
            
            if "updates" in poll_resp:
                for update in poll_resp["updates"]:
                    # ОТЛАДКА: выводим первые 3 события полностью
                    if debug_count < 3:
                        print(f" DEBUG update #{debug_count}: {update}")
                        debug_count += 1
                    
                    if not isinstance(update, list) or len(update) < 6:
                        continue
                    
                    event_type = update[0]
                    
                    if event_type == 4:  # Новое сообщение
                        flags = update[1]
                        peer_id = update[3]
                        text = str(update[5]) if update[5] else ""
                        
                        print(f"🔍 Тип={event_type}, Флаги={flags}, Peer={peer_id}, Текст='{text}'")
                        
                        # flags & 2 = входящее сообщение (от пользователя к боту)
                        if (flags & 2) and text:
                            handle_message(peer_id, text)
            
            ts = poll_resp.get("ts", ts)
        except Exception as e:
            print(f"️ Ошибка цикла: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)
            server_data = get_long_poll_server()
            if server_data:
                server, key, ts = server_data["server"], server_data["key"], server_data["ts"]

if __name__ == "__main__":
    main()
