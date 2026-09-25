import asyncio
import logging
import requests
from dotenv import load_dotenv
import os
from maxapi import Bot, Dispatcher, F
from maxapi.types import BotStarted, MessageCreated
from maxapi.filters.command import CommandStart
from services import AIService, detect_mode

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.environ["MAX_TOKEN"])
dp = Dispatcher()

user_data = {}
MAX_HISTORY_MESSAGES = 20

MODES = {
    "general": "🤖 Общий", "planner": "📅 Подготовка к экзаменам",
    "homework": "📝 Помощь с домашкой", "explain": "🎓 Объяснение темы",
    "tests": "✅ Проверка знаний", "motivation": "💪 Мотивация",
    "videos": "🎥 Видеоуроки", "journal": "📚 Оценки и МЭШ",
    "offline": "📱 Оффлайн материалы", "photo": "🖼️ Фото заданий"
}

def get_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"history": [], "mode": "general"}
    return user_data[user_id]

def add_to_history(user_id, role, content):
    data = get_user_data(user_id)
    data["history"].append({"role": role, "content": content})
    if len(data["history"]) > MAX_HISTORY_MESSAGES:
        data["history"] = data["history"][-MAX_HISTORY_MESSAGES:]

def clear_history(user_id):
    if user_id in user_data:
        user_data[user_id]["history"] = []
        user_data[user_id]["mode"] = "general"

def get_chat_id(event):
    """Пробует разные способы получить chat_id"""
    ways = [
        ("recipient.chat_id", lambda e: e.recipient.chat_id),
        ("message.recipient.chat_id", lambda e: e.message.recipient.chat_id),
        ("chat.chat_id", lambda e: e.chat.chat_id),
        ("message.chat_id", lambda e: e.message.chat_id),
        ("sender.user_id", lambda e: e.sender.user_id),
    ]
    for name, func in ways:
        try:
            return func(event)
        except Exception:
            pass
    return None

def extract_photo_url(event):
    """Достаёт ссылку на фото из сообщения MAX"""
    try:
        # Ищем вложения в разных местах
        attachments = None
        
        try:
            attachments = event.message.body.attachments
        except Exception:
            pass
        
        if attachments is None:
            try:
                attachments = event.message.attachments
            except Exception:
                pass
        
        if not attachments:
            print("❌ Вложений не найдено")
            return None
        
        print(f"📷 Найдено вложений: {len(attachments)}")
        
        for att in attachments:
            try:
                att_type = getattr(att, 'type', 'unknown')
                print(f"   Тип вложения: {att_type}")
                
                # Пропускаем не-фото
                if att_type != 'image':
                    continue
                
                # ГЛАВНЫЙ ПУТЬ: payload.url (именно так устроен MAX API)
                try:
                    payload = att.payload
                    url = payload.url
                    if url and isinstance(url, str) and url.startswith('http'):
                        print(f"   ✅ URL найден через payload.url: {url[:60]}...")
                        return url
                except Exception as e:
                    print(f"   ⚠️ payload.url не работает: {e}")
                
                # Запасные пути (на всякий случай)
                for path in ['url', 'image', 'photo', 'file']:
                    try:
                        url = getattr(att, path, None)
                        if url and isinstance(url, str) and url.startswith('http'):
                            print(f"   ✅ URL найден через {path}: {url[:60]}...")
                            return url
                    except Exception:
                        pass
                        
            except Exception as e:
                print(f"   ⚠️ Ошибка разбора вложения: {e}")
                continue
        
        print("❌ Не удалось найти URL фото ни одним способом")
        return None
    except Exception as e:
        print(f"⚠️ Критическая ошибка extract_photo_url: {e}")
        return None

def download_photo(url):
    """Скачивает фото по ссылке"""
    try:
        print(f"📥 Скачивание: {url[:60]}...")
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        print(f"📥 Скачано {len(r.content)} байт")
        return r.content
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
        return None

@dp.bot_started()
async def bot_started(event: BotStarted):
    welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n\n"
    welcome += "Я запомню наш разговор и буду учитывать контекст.\n"
    welcome += "Напиши 'сброс', чтобы начать заново.\n\n"
    welcome += "Ты можешь:\n"
    welcome += "📷 Прислать фото задания — я прочитаю и помогу.\n"
    welcome += "💬 Или просто написать вопрос.\n"
    await bot.send_message(chat_id=event.chat_id, text=welcome)

@dp.message_created(CommandStart())
async def handle_start(event: MessageCreated):
    chat_id = get_chat_id(event)
    if not chat_id:
        return
    clear_history(chat_id)
    welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы."
    await event.message.answer(welcome)

@dp.message_created(F.message.body.attachments)
async def handle_photo(event: MessageCreated):
    """Обработчик сообщений с фото (должен идти ПЕРЕД текстовым!)"""
    chat_id = get_chat_id(event)
    if not chat_id:
        return
    
    # Пытаемся получить подпись к фото
    caption = ""
    try:
        if event.message.body.text:
            caption = event.message.body.text
    except Exception:
        pass
    
    print(f"\n🖼️ ПОЛУЧЕНО ФОТО!")
    print(f"   Подпись: '{caption}'")
    
    # Сообщаем пользователю, что начали обработку
    await event.message.answer("🔍 Анализирую фото, подожди 5-10 секунд...")
    
    # Достаём URL фото
    photo_url = extract_photo_url(event)
    
    if not photo_url:
        await event.message.answer("😔 Не смог найти фото в сообщении. Попробуй отправить его ещё раз.")
        return
    
    # Скачиваем фото
    image_bytes = download_photo(photo_url)
    
    if not image_bytes:
        await event.message.answer("😔 Не смог скачать фото. Попробуй отправить его ещё раз.")
        return
    
    # Анализируем через GigaChat
    try:
        data = get_user_data(chat_id)
        # Принудительно ставим режим "photo"
        data["mode"] = "photo"
        
        response = AIService.process_image(image_bytes, caption, data["history"])
        
        # Сохраняем в историю
        add_to_history(chat_id, "user", f"[Фото] {caption}")
        add_to_history(chat_id, "assistant", response)
        
        # Отправляем ответ (разбиваем если длинный)
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await event.message.answer(response[i:i+4000])
        else:
            await event.message.answer(response)
    except Exception as e:
        print(f"❌ Ошибка анализа фото: {e}")
        import traceback
        traceback.print_exc()
        await event.message.answer("Извини, не получилось проанализировать фото. Попробуй ещё раз.")

@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    """Обработчик обычных текстовых сообщений"""
    text = event.message.body.text
    chat_id = get_chat_id(event)
    
    if not chat_id or not text:
        return
    
    text = text.strip()
    text_lower = text.lower()
    
    if text_lower in ["начать", "старт", "start"]:
        clear_history(chat_id)
        welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n\n"
        welcome += "Я запомню наш разговор и буду учитывать контекст.\n"
        welcome += "Напиши 'сброс', чтобы начать заново.\n"
        await event.message.answer(welcome)
        return
    
    if text_lower in ["сброс", "забудь", "очистить"]:
        clear_history(chat_id)
        await event.message.answer("🗑️ Готово! Чем помочь?")
        return
    
    if text_lower in ["помощь", "меню", "режимы"]:
        menu = "🎯 Я сам определю режим по твоему вопросу.\n"
        menu += "Просто напиши, что нужно, или пришли фото задания!\n"
        menu += "Команды: 'сброс' — начать заново"
        await event.message.answer(menu)
        return
    
    detected = detect_mode(text)
    data = get_user_data(chat_id)
    if detected != "general":
        data["mode"] = detected
    mode = data["mode"]
    
    print(f"🎯 Режим: {MODES.get(mode, 'Общий')}")
    
    try:
        response = AIService.process_message(text, mode, data["history"])
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", response)
        
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await event.message.answer(response[i:i+4000])
        else:
            await event.message.answer(response)
    except Exception as e:
        print(f"❌ Ошибка ИИ: {e}")
        await event.message.answer("Извини, произошла ошибка. Попробуй через минуту.")

async def main():
    print("🚀 БОТ Sferum Navigator запущен!")
    print("✅ Режимы: текст + фото")
    print("Ожидаю сообщения...\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
