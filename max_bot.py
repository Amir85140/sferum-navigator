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
    """Достаёт ссылку на фото из сообщения"""
    try:
        # Пробуем разные пути к вложениям
        attachments = None
        
        # Вариант 1: message.body.attachments
        try:
            attachments = event.message.body.attachments
        except Exception:
            pass
        
        # Вариант 2: message.attachments
        if attachments is None:
            try:
                attachments = event.message.attachments
            except Exception:
                pass
        
        if not attachments:
            return None
        
        print(f"📷 Найдено вложений: {len(attachments)}")
        
        # Ищем первое фото
        for att in attachments:
            try:
                # Выводим для диагностики
                print(f"   Вложение: {att}")
                
                # Пробуем разные способы получить ссылку
                for attr in ['url', 'image', 'photo', 'file', 'thumbnail']:
                    try:
                        obj = getattr(att, attr, None)
                        if obj is not None:
                            if isinstance(obj, str) and obj.startswith('http'):
                                return obj
                            # Если это объект с полями
                            for sub in ['url', 'big', 'medium', 'small']:
                                try:
                                    url = getattr(obj, sub, None)
                                    if url and isinstance(url, str):
                                        return url
                                except Exception:
                                    pass
                    except Exception:
                        pass
                        
            except Exception as e:
                print(f"   ⚠️ Ошибка при разборе вложения: {e}")
                continue
        
        return None
    except Exception as e:
        print(f"⚠️ Ошибка при извлечении фото: {e}")
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
    await event.message.answer("🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.")

@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    text = event.message.body.text
    chat_id = get_chat_id(event)
    
    if not chat_id:
        return
    
    if not text:
        return
    
    text = text.strip()
    text_lower = text.lower()
    
    if text_lower in ["начать", "старт", "start"]:
        clear_history(chat_id)
        await event.message.answer("🎯 Привет! Я Sferum Navigator.")
        return
    
    if text_lower in ["сброс", "забудь", "очистить"]:
        clear_history(chat_id)
        await event.message.answer("🗑️ Готово! Чем помочь?")
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
        await event.message.answer("Извини, произошла ошибка.")

@dp.message_created(F.message.body.attachments)
async def handle_photo(event: MessageCreated):
    """Обработчик сообщений с фото"""
    chat_id = get_chat_id(event)
    if not chat_id:
        return
    
    # Если есть текст вместе с фото
    try:
        caption = event.message.body.text
    except Exception:
        caption = ""
    
    print(f"\n🖼️ ПОЛУЧЕНО ФОТО!")
    print(f"   Подпись: '{caption}'")
    
    # Отправляем сообщение о начале обработки
    await event.message.answer("🔍 Анализирую фото, подожди 5-10 секунд...")
    
    # Извлекаем ссылку на фото
    photo_url = extract_photo_url(event)
    
    if not photo_url:
        await event.message.answer("😔 Не смог найти фото в сообщении. Попробуй отправить его ещё раз.")
        return
    
    # Скачиваем фото
    image_bytes = download_photo(photo_url)
    
    if not image_bytes:
        await event.message.answer("😔 Не смог скачать фото. Попробуй отправить его ещё раз.")
        return
    
    # Отправляем в GigaChat для анализа
    try:
        data = get_user_data(chat_id)
        response = AIService.process_image(image_bytes, caption, data["history"])
        
        add_to_history(chat_id, "user", f"[Фото] {caption}")
        add_to_history(chat_id, "assistant", response)
        
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await event.message.answer(response[i:i+4000])
        else:
            await event.message.answer(response)
    except Exception as e:
        print(f"❌ Ошибка анализа фото: {e}")
        await event.message.answer("Извини, не получилось проанализировать фото. Попробуй ещё раз.")

async def main():
    print("🚀 БОТ Sferum Navigator запущен!")
    print("✅ Режимы: текст + фото")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
