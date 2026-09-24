import vk_api
from vk_api import vk_api as vk_api_module
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import time
import requests
from services import AIService, detect_mode

# ===== КОНФИГУРАЦИЯ MAX (Сферум) =====
# Переопределяем URL API на MAX (нужно сделать ДО создания сессии!)
vk_api_module.API_URL = 'https://api.max.ru/method/'

MAX_TOKEN = "f9LHodD0cOL_CTMQchAMtDovrgVanr2B904VleKpipLF22l4DnPeJKVTxWHLpDJi6VgmKRgGvRvRg4-2w8Mp"
GROUP_ID = 241621560  # ⚠️ Проверь, что это правильный ID для MAX!

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
    "photo": "🖼️ Фото заданий"
}

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

def send_message(vk, peer_id, text):
    global sent_message_ids
    log(f"📤 Отправка пользователю {peer_id}...")
    try:
        msg_id = vk.messages.send(
            peer_id=peer_id,
            message=text,
            random_id=int(time.time() * 1000)
        )
        if msg_id:
            sent_message_ids.add(msg_id)
        log(f"✅ Доставлено! (id={msg_id})")
        return msg_id
    except Exception as e:
        log(f"❌ Ошибка отправки: {e}")
        return None

def extract_photo(obj):
    attachments = getattr(obj, "attachments", None)
    if not attachments:
        return None
    for att in attachments:
        if att.get("type") == "photo":
            photo = att.get("photo")
            if photo and "sizes" in photo:
                largest = max(photo["sizes"], key=lambda s: s.get("width", 0) * s.get("height", 0))
                return largest.get("url")
    return None

def download_photo(url):
    try:
        log(f"📥 Скачивание фото: {url[:60]}...")
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        log(f"📥 Скачано {len(r.content)} байт")
        return r.content
    except Exception as e:
        log(f"❌ Ошибка скачивания фото: {e}")
        return None

def handle_message(vk, peer_id, text, photo_url=None):
    log(f"\n📩 ПОЛУЧЕНО от {peer_id}: текст='{text}', фото={'да' if photo_url else 'нет'}")
    
    data = get_user_data(peer_id)
    
    if photo_url:
        send_message(vk, peer_id, "🔍 Анализирую фото, подожди пару секунд...")
        image_bytes = download_photo(photo_url)
        if image_bytes:
            try:
                response = AIService.process_image(image_bytes, text or "", data["history"])
                add_to_history(peer_id, "user", f"[Фото] {text or ''}")
                add_to_history(peer_id, "assistant", response)
            except Exception as e:
                log(f"❌ Ошибка ИИ при анализе фото: {e}")
                response = "Извини, не получилось проанализировать фото. Попробуй ещё раз."
            send_message(vk, peer_id, response)
        else:
            send_message(vk, peer_id, "Не смог скачать фото 😔 Попробуй отправить его ещё раз.")
        return
    
    if not text:
        return
    
    text = str(text).strip()
    text_lower = text.lower()
    
    if text_lower in ["начать", "start"]:
        clear_history(peer_id)
        welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n\n"
        welcome += "Я запомню наш разговор и буду учитывать контекст.\n"
        welcome += "Напиши 'сброс', чтобы начать заново.\n\n"
        welcome += "Ты можешь:\n"
        welcome += "📷 Прислать фото задания — я прочитаю и помогу.\n"
        welcome += "💬 Или просто написать вопрос.\n"
        send_message(vk, peer_id, welcome)
        return
    
    if text_lower in ["сброс", "забудь", "начать заново", "очистить"]:
        clear_history(peer_id)
        send_message(vk, peer_id, "🗑️ Готово! Я забыл наш разговор. Чем помочь?")
        return
    
    if text_lower in ["режимы", "меню", "помощь", "help", "/start"]:
        menu = "🎯 Я сам определю режим по твоему вопросу.\n"
        menu += "Просто напиши, что нужно, или пришли фото задания!\n"
        menu += "Команды: 'сброс' — начать заново"
        send_message(vk, peer_id, menu)
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
                send_message(vk, peer_id, response[i:i+4000])
        else:
            send_message(vk, peer_id, response)
    except Exception as e:
        log(f"❌ Ошибка ИИ: {e}")
        send_message(vk, peer_id, "Извини, произошла ошибка. Попробуй через минуту.")

def main():
    log("🚀 БОТ Sferum Navigator в MAX с GigaChat запущен!")
    log(f"📌 Group ID: {GROUP_ID}")
    log(f"🌐 API URL: {vk_api_module.API_URL}")
    
    try:
        vk_session = vk_api.VkApi(
            token=MAX_TOKEN,
            api_version='5.131'
        )
        vk = vk_session.get_api()
        
        longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID, wait=20)
        log("✅ MAX Bot Long Poll подключен! Ожидаю сообщения...\n")
        
        for event in longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    obj = event.obj
                    photo_url = extract_photo(obj)
                    handle_message(vk, obj.peer_id, obj.text, photo_url)
                
                elif event.type == VkBotEventType.MESSAGE_REPLY:
                    obj = event.obj
                    msg_id = getattr(obj, "id", None)
                    
                    if msg_id in sent_message_ids:
                        sent_message_ids.discard(msg_id)
                        continue
                    
                    if getattr(obj, "out", 0) == 1 and getattr(obj, "random_id", 0) < 0:
                        photo_url = extract_photo(obj)
                        handle_message(vk, obj.peer_id, obj.text, photo_url)
                        
            except Exception as e:
                log(f"⚠️ Ошибка обработки события: {e}")
                
    except Exception as e:
        log(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
