import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from services import AIService

BOT_TOKEN = "vk1.a.9BNdW2YFQFAa_3mTuZxhfvJQxp8jOHrlzFYs4K9CrLASaKg8qcpDjVNKVI8TOWYUZ_fMCHmSpN_iZAZLFnyp06mGujmxXp_7k3uKACkO4oxT0yCrr8OLICeT47cCOeyHkk10uffc2dJUNl2w75qrkl15n2DB6ZZh1s8vZemIDeEcitMdI8dxV0DlYUjjB-8MjheTED6Lc1zu-1Diztlq-Q"

MODES = {
    "general": " Общий",
    "planner": " Подготовка к экзаменам",
    "homework": "📝 Помощь с домашкой",
    "explain": "🎓 Объяснение темы",
    "tests": "✅ Проверка знаний",
    "motivation": "💪 Мотивация",
    "videos": "🎥 Видеоуроки",
    "journal": "📚 Оценки и МЭШ",
    "offline": "📱 Оффлайн материалы"
}

user_modes = {}

def send_message(vk, peer_id, text):
    print(f"📤 Отправка: {text[:60]}...")
    vk.method("messages.send", {
        "peer_id": peer_id,
        "message": text,
        "random_id": 0
    })

def handle_message(vk, peer_id, text):
    print(f"\n Получено от {peer_id}: '{text}'")
    text = str(text).strip()
    text_lower = text.lower()
    
    # Тест ИИ
    if text_lower == "тест ии":
        print(" Тест GigaChat...")
        try:
            resp = AIService.process_message("Скажи 'Привет, я работаю!'", "general")
            print(f"🧪 Ответ: {resp}")
            send_message(vk, peer_id, f"Тест ИИ:\n{resp}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            send_message(vk, peer_id, f"Ошибка: {e}")
        return
    
    # Смена режима
    for mode_id, mode_name in MODES.items():
        if mode_id in text_lower or mode_name.lower() in text_lower:
            user_modes[peer_id] = mode_id
            send_message(vk, peer_id, f"✅ Режим: {mode_name}\nЗадай вопрос!")
            return
    
    mode = user_modes.get(peer_id, "general")
    
    # Меню
    if text_lower in ["режимы", "меню", "помощь", "help", "/start", "старт"]:
        menu = "🎯 Выбери режим:\n\n"
        for mid, mname in MODES.items():
            menu += f"• {mname} ({mid})\n"
        menu += "\nИли напиши 'тест ии'."
        send_message(vk, peer_id, menu)
        return
    
    # ИИ
    print(f"🤖 GigaChat (режим: {mode})...")
    try:
        resp = AIService.process_message(text, mode)
        print(f"✅ Ответ: {resp[:100]}...")
        send_message(vk, peer_id, resp)
    except Exception as e:
        print(f"❌ Ошибка ИИ: {e}")
        send_message(vk, peer_id, f"Ошибка: {e}")

def main():
    print(" Бот запущен!")
    
    vk_session = vk_api.VkApi(token=BOT_TOKEN)
    vk = vk_session.get_api()
    
    # Получаем ID группы из токена
    try:
        groups = vk.groups.get()
        group_id = groups["items"][0]["id"]
        print(f"✅ Группа найдена: {group_id}")
    except Exception as e:
        print(f"❌ Не удалось получить группу: {e}")
        return
    
    longpoll = VkBotLongPoll(vk_session, group_id)
    print(f"✅ Long Poll подключен!\n")
    
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.object.message
            peer_id = msg["peer_id"]
            text = msg.get("text", "")
            
            if text:
                handle_message(vk, peer_id, text)

if __name__ == "__main__":
    main()
