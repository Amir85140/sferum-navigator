import requests
import time
import json
import sys

# Функция для гарантированного вывода в терминал
def log(msg):
    print(msg)
    sys.stdout.flush()

BOT_TOKEN = "vk1.a.9BNdW2YFQFAa_3mTuZxhfvJQxp8jOHrlzFYs4K9CrLASaKg8qcpDjVNKVI8TOWYUZ_fMCHmSpN_iZAZLFnyp06mGujmxXp_7k3uKACkO4oxT0yCrr8OLICeT47cCOeyHkk10uffc2dJUNl2w75qrkl15n2DB6ZZh1s8vZemIDeEcitMdI8dxV0DlYUjjB-8MjheTED6Lc1zu-1Diztlq-Q"
API_VERSION = "5.131"

def get_long_poll_server():
    log("🔄 [Диагностика] Делаем запрос к VK за Long Poll сервером...")
    url = "https://api.vk.com/method/messages.getLongPollServer"
    params = {"access_token": BOT_TOKEN, "v": API_VERSION, "lp_version": "3"}
    try:
        resp = requests.post(url, data=params, timeout=10).json()
        log(f"📡 [Диагностика] Сырой ответ от VK: {resp}")
        return resp.get("response")
    except Exception as e:
        log(f"❌ [Диагностика] Критическая ошибка запроса: {e}")
        return None

def main():
    log("🚀 [1/4] Скрипт max_bot.py успешно стартовал!")
    log("🚀 [2/4] Пытаемся подключиться к Long Poll...")
    
    server_data = get_long_poll_server()
    
    if not server_data:
        log("⛔ [3/4] ОШИБКА: Не удалось получить данные сервера. Бот остановлен.")
        return
    
    server = server_data.get("server")
    key = server_data.get("key")
    ts = server_data.get("ts")
    
    log(f"✅ [3/4] Long Poll подключен! (server={server}, ts={ts})")
    log("🟢 [4/4] БОТ РАБОТАЕТ И ЖДЕТ СООБЩЕНИЙ. Напиши ему что-нибудь в MAX/VK.\n")
    
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
                            log(f"📩 ПОЛУЧЕНО СООБЩЕНИЕ от {peer_id}: '{text}'")
                            # Здесь пока просто эхо-ответ для проверки связи
                            requests.post("https://api.vk.com/method/messages.send", data={
                                "access_token": BOT_TOKEN,
                                "peer_id": peer_id,
                                "message": f"Эхо: я получил твое сообщение '{text}'",
                                "random_id": int(time.time() * 1000),
                                "v": API_VERSION
                            })
            
            ts = poll_resp.get("ts", ts)
        except Exception as e:
            log(f"⚠️ Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"💥 КРИТИЧЕСКИЙ СБОЙ ПРИ ЗАПУСКЕ: {e}")
