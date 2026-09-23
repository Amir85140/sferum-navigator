import vk_api
import time
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from services import AIService, detect_mode

GROUP_ID = 241621560
BOT_TOKEN = "vk1.a.9BNdW2YFQFAa_3mTuZxhfvJQxp8jOHrlzFYs4K9CrLASaKg8qcpDjVNKVI8TOWYUZ_fMCHmSpN_iZAZLFnyp06mGujmxXp_7k3uKACkO4oxT0yCrr8OLICeT47cCOeyHkk10uffc2dJUNl2w75qrkl15n2DB6ZZh1s8vZemIDeEcitMdI8dxV0DlYUjjB-8MjheTED6Lc1zu-1Diztlq-Q"

# Множество для хранения ID собственных сообщений бота (защита от цикла)
sent_message_ids = set()

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

def log(msg):
    print(msg, flush=True)

def send_message(vk, peer_id, text):
    global sent_message_ids
    log(f"📤 Отправка пользователю {peer_id}...")
    try:
        msg_id = vk.messages.send(
            peer_id=peer_id,
            message=text,
            random_id=int(time.time() * 1000)
        )
        # Запоминаем ID нашего сообщения, чтобы потом его игнорировать
        if msg_id:
            sent_message_ids.add(msg_id)
        log(f"✅ Доставлено! (id={msg_id})")
        return msg_id
    except Exception as e:
        log(f"❌ Ошибка отправки: {e}")
        return None

def handle_message(vk, peer_id, text):
    if not text:
        return
    
    log(f"\n📩 ПОЛУЧЕНО от {peer_id}: '{text}'")
    text = str(text).strip()
    text_lower = text.lower()
    
    if text_lower in ["режимы", "меню", "помощь", "help", "/start", "старт"]:
        menu = "🎯 Привет! Я сам определю режим по твоему вопросу.\n\nПросто напиши, что тебе нужно:\n"
        menu += "• 'Составь план подготовки к ЕГЭ по математике'\n"
        menu += "• 'Объясни фотосинтез простыми словами'\n"
        menu += "• 'Дай ссылки на видеоуроки по физике'\n"
        menu += "• 'Я устал и не хочу учиться'"
        send_message(vk, peer_id, menu)
        return
    
    try:
        mode = detect_mode(text)
        log(f"🎯 Режим: {MODES.get(mode, 'Общий')}")
    except Exception as e:
        log(f"⚠️ Ошибка определения режима: {e}")
        mode = "general"
    
    try:
        log("🤖 Запрос к GigaChat...")
        response = AIService.process_message(text, mode)
        log(f"✅ Ответ получен ({len(response)} симв.)")
        
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                send_message(vk, peer_id, response[i:i+4000])
        else:
            send_message(vk, peer_id, response)
    except Exception as e:
        log(f"❌ Ошибка ИИ: {e}")
        send_message(vk, peer_id, "Извини, произошла ошибка. Попробуй через минуту.")

def main():
    log("🚀 БОТ Sferum Navigator с GigaChat запущен!")
    log(f"📌 Group ID: {GROUP_ID}")
    
    try:
        vk_session = vk_api.VkApi(token=BOT_TOKEN, api_version='5.131')
        vk = vk_session.get_api()
        
        longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID, wait=20)
        log("✅ Bot Long Poll подключен! Ожидаю сообщения...\n")
        
        for event in longpoll.listen():
            try:
                # 1. Обычные пользователи (друзья, одноклассники, жюри)
                if event.type == VkBotEventType.MESSAGE_NEW:
                    obj = event.obj
                    handle_message(vk, obj.peer_id, obj.text)
                
                # 2. Владелец пишет со стороны сообщества (владельцев в MAX)
                elif event.type == VkBotEventType.MESSAGE_REPLY:
                    obj = event.obj
                    msg_id = getattr(obj, "id", None)
                    
                    # Если это наше собственное сообщение — пропускаем (защита от цикла)
                    if msg_id in sent_message_ids:
                        sent_message_ids.discard(msg_id)
                        continue
                    
                    # Отвечаем только если это сообщение, набранное вручную админом
                    if getattr(obj, "out", 0) == 1 and getattr(obj, "random_id", 0) < 0:
                        handle_message(vk, obj.peer_id, obj.text)
                        
            except Exception as e:
                log(f"⚠️ Ошибка обработки события: {e}")
                
    except Exception as e:
        log(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
