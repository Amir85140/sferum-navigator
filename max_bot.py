import requests
import time
import json
from services import AIService, detect_mode

# ===== КОНФИГУРАЦИЯ MAX =====
MAX_TOKEN = "f9LHodD0cOL_CTMQchAMtDovrgVanr2B904VleKpipLF22l4DnPeJKVTxWHLpDJi6VgmKRgGvRvRg4-2w8Mp"
GROUP_ID = 241621560
BASE_URL = "https://botapi.sberclass.ru/api/v1"  # Возможный endpoint для MAX

sent_message_ids = set()
user_data = {}
MAX_HISTORY_MESSAGES = 20

MODES = {
    "general": "🤖 Общий",
    "planner": "📅 Подготовка к экзаменам",
    "homework": "📝 Помощь с домашкой",
    "explain": "🎓 Объяснение темы",
    "tests": "✅ Проверка знаний",
    "motivation": "💪 Мотивация",
    "videos": "🎥 Видеоуроки",
    "journal": "📚 Оценки и МЭШ",
    "offline": "📱 Оффлайн материалы",
    "photo": "🖼️ Фото задания"
}

class MAXClient:
    """Клиент для работы с MAX API"""
    
    def __init__(self, token, group_id):
        self.token = token
        self.group_id = group_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
    
    def method(self, method_name, params=None):
        """Вызов метода MAX API"""
        url = f"{BASE_URL}/{method_name}"
        try:
            response = self.session.post(url, json=params or {})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log(f"❌ Ошибка API {method_name}: {e}")
            return None
    
    def get_long_poll_server(self):
        """Получить сервер Long Poll"""
        result = self.method("groups.getLongPollServer", {
            "group_id": self.group_id
        })
        return result
    
    def send_message(self, peer_id, text, random_id=None):
        """Отправить сообщение"""
        params = {
            "peer_id": peer_id,
            "message": text,
            "random_id": random_id or int(time.time() * 1000)
        }
        return self.method("messages.send", params)


def log(msg):
    print(msg, flush=True)

def get_user_data(peer_id):
    if peer_id not in user_data:
        user_data[peer_id] = {"history": [], "mode": "general"}
    return user_data[peer_id]

def add_to_history(peer_id, role, content):
    data = get_user_data(peer_id)
    data["history"].append({"role": role, "content": content})
    if len(data["history"]) > MAX_HISTORY_MESSAGES:
        data["history"] = data["history"][-MAX_HISTORY_MESSAGES:]

def clear_history(peer_id):
    if peer_id in user_data:
        user_data[peer_id]["history"] = []
        user_data[peer_id]["mode"] = "general"
        log(f"🗑️ История очищена для {peer_id}")

def handle_message(client, peer_id, text, photo_url=None):
    log(f"\n📩 ПОЛУЧЕНО от {peer_id}: текст='{text}'")
    
    data = get_user_data(peer_id)
    
    if not text:
        return
    
    text = str(text).strip()
    text_lower = text.lower()
    
    if text_lower in ["начать", "start"]:
        clear_history(peer_id)
        welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n\n"
        welcome += "Я запомню наш разговор и буду учитывать контекст.\n"
        welcome += "Напиши 'сброс', чтобы начать заново.\n"
        client.send_message(peer_id, welcome)
        return
    
    if text_lower in ["сброс", "забудь", "очистить"]:
        clear_history(peer_id)
        client.send_message(peer_id, "🗑️ Готово! Чем помочь?")
        return
    
    detected = detect_mode(text)
    if detected != "general":
        data["mode"] = detected
    mode = data["mode"]
    log(f"🎯 Режим: {MODES.get(mode, 'Общий')}")
    
    try:
        response = AIService.process_message(text, mode, data["history"])
        log(f"✅ Ответ получен ({len(response)} симв.)")
        
        add_to_history(peer_id, "user", text)
        add_to_history(peer_id, "assistant", response)
        
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                client.send_message(peer_id, response[i:i+4000])
        else:
            client.send_message(peer_id, response)
    except Exception as e:
        log(f"❌ Ошибка ИИ: {e}")
        client.send_message(peer_id, "Извини, произошла ошибка. Попробуй через минуту.")

def main():
    log("🚀 БОТ Sferum Navigator в MAX запущен!")
    log(f"📌 Group ID: {GROUP_ID}")
    log(f"🌐 Base URL: {BASE_URL}")
    
    client = MAXClient(MAX_TOKEN, GROUP_ID)
    
    # Проверяем подключение
    log("🔍 Проверяем подключение к MAX API...")
    result = client.get_long_poll_server()
    
    if not result:
        log("❌ Не удалось подключиться к MAX API!")
        log("💡 Возможно, нужен другой BASE_URL или формат авторизации")
        log("💡 Попробуем альтернативные endpoints...")
        
        # Пробуем другие возможные endpoints
        alt_urls = [
            "https://api.sferum.ru/api/v1",
            "https://botapi.max.ru/api/v1",
            "https://sberclass.ru/api/v1"
        ]
        
        for url in alt_urls:
            log(f"🔄 Пробуем {url}...")
            client = MAXClient(MAX_TOKEN, GROUP_ID)
            client.session.headers.update({})  # Сбрасываем
            BASE_URL_GLOBAL = url
            result = client.get_long_poll_server()
            if result:
                log(f"✅ Работает с {url}!")
                break
        
        if not result:
            log("💥 Ни один endpoint не сработал!")
            log("📋 Нужна документация MAX API или правильный endpoint")
            return
    
    log("✅ Подключено! Ожидаю сообщения...")
    
    # TODO: Реализовать Long Poll для MAX
    # Пока что бот будет работать в режиме опроса
    log("⚠️ Long Poll для MAX ещё не реализован")
    log("💡 Бот готов, но нужен правильный механизм получения сообщений")

if __name__ == "__main__":
    main()
