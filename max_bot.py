import requests
import time
import json
import sys
from services import AIService, detect_mode

def log(msg):
    print(msg)
    sys.stdout.flush()

BOT_TOKEN = "vk1.a.9BNdW2YFQFAa_3mTuZxhfvJQxp8jOHrlzFYs4K9CrLASaKg8qcpDjVNKVI8import requests
import time
import json
import sys
from services import AIService, detect_mode

def log(msg):
    print(msg)
    sys.stdout.flush()

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
    "offline": " Оффлайн материалы"
}

def send_message(peer_id, text):
    log(f" Отправка ответа пользователю {peer_id}...")
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": BOT_TOKEN,
        "peer_id": peer_id,
        "message": text,
        "random_id": int(time.time() * 1000),
        "v": API_VERSION
    }
    try:
        resp = requests.post(url, data=params, timeout=10).json()
        if "error" in resp:
            log(f"❌ Ошибка VK: {resp['error']}")
        else:
            log("✅ Ответ успешно доставлен!")
    except Exception as e:
        log(f"⚠️ Ошибка сети VK: {e}")

def handle_message(peer_id, text):
    log(f"\n📩 ПОЛУЧЕНО от {peer_id}: '{text}'")
    text = str(text).strip()
    text_lower = text.lower()
    
    # Меню
    if text_lower in ["режимы", "меню", "помощь", "help", "/start", "старт"]:
        menu = " Привет! Я сам определю режим по твоему вопросу.\n\nПросто напиши, что тебе нужно:\n"
        menu += "• 'Составь план подготовки к ЕГЭ по математике'\n"
        menu += "• 'Объясни фотосинтез простыми словами'\n"
        menu += "• 'Дай ссылки на видеоуроки по физике'\n"
        menu += "• 'Я устал и не хочу учиться'"
        send_message(peer_id, menu)
        return
    
    # Автоопределение режима
    try:
        mode = detect_mode(text)
        log(f"🎯 ИИ выбрал режим: {MODES.get(mode, 'Общий')}")
    except Exception as e:
        log(f"⚠️ Ошибка определения режима: {e}, используем general")
        mode = "general"
    
    # Запрос к GigaChat с гарантированным ответом
    try:
        log(" Запрос к GigaChat...")
        response = AIService.process_message(text, mode)
        log(f"✅ Получен ответ от ИИ ({len(response)} симв.)")
        
        # Разбиваем длинные сообщения (лимит VK 4096)
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                send_message(peer_id, response[i:i+4000])
        else:
            send_message(peer_id, response)
    except Exception as e:
        log(f"❌ Критическая ошибка ИИ: {e}")
        # Fallback — всегда отвечаем пользователю
        send_message(peer_id, "Извини, произошла ошибка при обработке запроса. Попробуй ещё раз через минуту.")

def get_long_poll_server():
    url = "https://api.vk.com/method/messages.getLongPollServer"
    params = {"access_token": BOT_TOKEN, "v": API_VERSION, "lp_version": "3"}
    try:
        return requests.post(url, data=params, timeout=10).json().get("response")
    except Exception as e:
        log(f"❌ Ошибка получения сервера: {e}")
        return None

def main():
    log("🚀 БОТ Sferum Navigator с GigaChat запущен!")
    server_data = get_long_poll_server()
    if not server_data:
        log("⛔ ОШИБКА: Не удалось подключиться к Long Poll.")
        return
    
    server = server_data.get("server")
    key = server_data.get("key")
    ts = server_data.get("ts")
    log(f"✅ Long Poll подключен! Ожидаю сообщения...\n")
    
    while True:
        try:
            poll_url = f"https://{server}?act=a_check&key={key}&ts={ts}&wait=25&mode=2&version=3"
            poll_resp = requests.get(poll_url, timeout=30).json()
            
            if "failed" in poll_resp:
                if poll_resp["failed"] == 1: ts = poll_resp["ts"]
                elif poll_resp["failed"] == 2:
                    log("🔄 Переподключение к Long Poll...")
                    server_data = get_long_poll_server()
                    if server_data:
                        server, key, ts = server_data["server"], server_data["key"], server_data["ts"]
                elif poll_resp["failed"] == 3: ts = poll_resp["ts"]
                continue
            
            if "updates" in poll_resp:
                for update in poll_resp["updates"]:
                    if isinstance(update, list) and len(update) >= 6 and update[0] == 4:
                        flags = update[1]
                        peer_id = update[3]
                        text = str(update[5]) if update[5] else ""
                        if (flags & 2) and text:
                            handle_message(peer_id, text)
            
            ts = poll_resp.get("ts", ts)
        except Exception as e:
            log(f"⚠️ Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"💥 КРИТИЧЕСКИЙ СБОЙ: {e}")TOWYUZ_fMCHmSpN_iZAZLFnyp06mGujmxXp_7k3uKACkO4oxT0yCrr8OLICeT47cCOeyHkk10uffc2dJUNl2w75qrkl15n2DB6ZZh1s8vZemIDeEcitMdI8dxV0DlYUjjB-8MjheTED6Lc1zu-1Diztlq-Q"
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
    "offline": " Оффлайн материалы"
}

def send_message(peer_id, text):
    log(f" Отправка ответа пользователю {peer_id}...")
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": BOT_TOKEN,
        "peer_id": peer_id,
        "message": text,
        "random_id": int(time.time() * 1000),
        "v": API_VERSION
    }
    try:
        resp = requests.post(url, data=params, timeout=10).json()
        if "error" in resp:
            log(f"❌ Ошибка VK: {resp['error']}")
        else:
            log("✅ Ответ успешно доставлен!")
    except Exception as e:
        log(f"⚠️ Ошибка сети VK: {e}")

def handle_message(peer_id, text):
    log(f"\n📩 ПОЛУЧЕНО от {peer_id}: '{text}'")
    text = str(text).strip()
    text_lower = text.lower()
    
    # Меню
    if text_lower in ["режимы", "меню", "помощь", "help", "/start", "старт"]:
        menu = " Привет! Я сам определю режим по твоему вопросу.\n\nПросто напиши, что тебе нужно:\n"
        menu += "• 'Составь план подготовки к ЕГЭ по математике'\n"
        menu += "• 'Объясни фотосинтез простыми словами'\n"
        menu += "• 'Дай ссылки на видеоуроки по физике'\n"
        menu += "• 'Я устал и не хочу учиться'"
        send_message(peer_id, menu)
        return
    
    # Автоопределение режима
    try:
        mode = detect_mode(text)
        log(f"🎯 ИИ выбрал режим: {MODES.get(mode, 'Общий')}")
    except Exception as e:
        log(f"⚠️ Ошибка определения режима: {e}, используем general")
        mode = "general"
    
    # Запрос к GigaChat с гарантированным ответом
    try:
        log(" Запрос к GigaChat...")
        response = AIService.process_message(text, mode)
        log(f"✅ Получен ответ от ИИ ({len(response)} симв.)")
        
        # Разбиваем длинные сообщения (лимит VK 4096)
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                send_message(peer_id, response[i:i+4000])
        else:
            send_message(peer_id, response)
    except Exception as e:
        log(f"❌ Критическая ошибка ИИ: {e}")
        # Fallback — всегда отвечаем пользователю
        send_message(peer_id, "Извини, произошла ошибка при обработке запроса. Попробуй ещё раз через минуту.")

def get_long_poll_server():
    url = "https://api.vk.com/method/messages.getLongPollServer"
    params = {"access_token": BOT_TOKEN, "v": API_VERSION, "lp_version": "3"}
    try:
        return requests.post(url, data=params, timeout=10).json().get("response")
    except Exception as e:
        log(f"❌ Ошибка получения сервера: {e}")
        return None

def main():
    log("🚀 БОТ Sferum Navigator с GigaChat запущен!")
    server_data = get_long_poll_server()
    if not server_data:
        log("⛔ ОШИБКА: Не удалось подключиться к Long Poll.")
        return
    
    server = server_data.get("server")
    key = server_data.get("key")
    ts = server_data.get("ts")
    log(f"✅ Long Poll подключен! Ожидаю сообщения...\n")
    
    while True:
        try:
            poll_url = f"https://{server}?act=a_check&key={key}&ts={ts}&wait=25&mode=2&version=3"
            poll_resp = requests.get(poll_url, timeout=30).json()
            
            if "failed" in poll_resp:
                if poll_resp["failed"] == 1: ts = poll_resp["ts"]
                elif poll_resp["failed"] == 2:
                    log("🔄 Переподключение к Long Poll...")
                    server_data = get_long_poll_server()
                    if server_data:
                        server, key, ts = server_data["server"], server_data["key"], server_data["ts"]
                elif poll_resp["failed"] == 3: ts = poll_resp["ts"]
                continue
            
            if "updates" in poll_resp:
                for update in poll_resp["updates"]:
                    if isinstance(update, list) and len(update) >= 6 and update[0] == 4:
                        flags = update[1]
                        peer_id = update[3]
                        text = str(update[5]) if update[5] else ""
                        if (flags & 2) and text:
                            handle_message(peer_id, text)
            
            ts = poll_resp.get("ts", ts)
        except Exception as e:
            log(f"⚠️ Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"💥 КРИТИЧЕСКИЙ СБОЙ: {e}")
