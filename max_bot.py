import asyncio
import logging
from dotenv import load_dotenv
import os
from maxapi import Bot, Dispatcher, F
from maxapi.types import BotStarted, MessageCreated
from maxapi.filters.command import CommandStart
from services import AIService, detect_mode, fix_keyboard_layout

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.environ["MAX_TOKEN"])
dp = Dispatcher()

user_data = {}
MAX_HISTORY_MESSAGES = 20

# Ссылка на мини-приложение (GitHub Pages)
MINI_APP_LINK = "https://amir85140.github.io/sferum-navigator/"

MODES = {
    "general": "🤖 Общий", "planner": "📅 Подготовка к экзаменам",
    "homework": "📝 Помощь с домашкой", "explain": "🎓 Объяснение темы",
    "tests": "✅ Проверка знаний", "motivation": "💪 Мотивация",
    "videos": "🎥 Видеоуроки", "offline": "📱 Оффлайн материалы",
    "context": "🔗 Контекст", "languages": "🌍 Иностранные языки"
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


async def send_mini_app(event):
    """
    Отправляет мини-приложение максимально "как в Telegram":
    1) Пробует web_app-кнопку (открытие внутри MAX)
    2) Если не поддерживается — link-кнопку (встроенный браузер MAX)
    3) Если и это не вышло — просто ссылку текстом
    """
    # Попытка 1: web_app кнопка (настоящее мини-приложение внутри MAX)
    try:
        from maxapi.types import InlineKeyboardButton
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🚀 Открыть в MAX", web_app={"url": MINI_APP_LINK}))
        await event.message.answer("📱 Мини-приложение Sferum Navigator:", attachments=[builder.as_markup()])
        print("✅ Отправлено через web_app-кнопку (внутри MAX)")
        return
    except Exception as e:
        print(f"⚠️ web_app-кнопка не поддержалась: {type(e).__name__}")
    
    # Попытка 2: link-кнопка (откроется во встроенном браузере MAX)
    try:
        from maxapi.types import InlineKeyboardButton
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🚀 Открыть приложение", url=MINI_APP_LINK))
        await event.message.answer("📱 Мини-приложение Sferum Navigator:", attachments=[builder.as_markup()])
        print("✅ Отправлено через link-кнопку (встроенный браузер)")
        return
    except Exception as e:
        print(f"⚠️ link-кнопка не поддержалась: {type(e).__name__}")
    
    # Попытка 3: просто ссылка
    msg = "📱 Мини-приложение Sferum Navigator!\n\n"
    msg += MINI_APP_LINK + "\n\n"
    msg += "Внутри: планировщик подготовки и тренажёр."
    await event.message.answer(msg)
    print("✅ Отправлено просто ссылкой")


@dp.bot_started()
async def bot_started(event: BotStarted):
    welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n\n"
    welcome += "✨ Я запомню наш разговор и буду учитывать контекст.\n"
    welcome += "📝 Напиши 'сброс', чтобы начать заново.\n\n"
    welcome += "📌 Что я умею:\n"
    welcome += "📝 Помощь с домашкой (метод Сократа)\n"
    welcome += "📅 Планирование подготовки к ОГЭ/ЕГЭ\n"
    welcome += "🎓 Объяснение сложных тем простым языком\n"
    welcome += "🌍 Практика иностранных языков и переводы\n"
    welcome += "✅ Проверка знаний через тесты и квизы\n"
    welcome += "🎥 Поиск видеоуроков\n"
    welcome += "💪 Мотивация и поддержка при выгорании\n"
    welcome += "📱 Мини-приложение: напиши 'мини'"
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
    
    if not chat_id or not text:
        return
    
    # Автоисправление раскладки клавиатуры
    original_text = text
    text = fix_keyboard_layout(text)
    if text != original_text:
        print(f"⌨️ Исправлена раскладка")
    
    text = text.strip()
    text_lower = text.lower()
    
    # Команды управления
    if text_lower in ["начать", "старт", "start", "hello", "hi", "привет"]:
        clear_history(chat_id)
        await event.message.answer("🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\nНапиши 'помощь', чтобы увидеть список команд.")
        return
    
    if text_lower in ["сброс", "забудь", "очистить", "reset", "clear"]:
        clear_history(chat_id)
        await event.message.answer("🗑️ Готово! Чем помочь?")
        return
    
    if text_lower in ["помощь", "меню", "режимы", "help", "menu"]:
        menu = "🎯 Я сам определю режим по твоему вопросу.\n"
        menu += "Просто напиши, что нужно!\n"
        menu += "Команды: 'сброс' — начать заново\n"
        menu += "🌍 Пиши на любом языке — я пойму!\n"
        menu += "📱 'мини' — открыть мини-приложение"
        await event.message.answer(menu)
        return
    
    # Команда открытия мини-приложения
    if text_lower in ["мини", "приложение", "мини приложение", "mini", "app"]:
        await send_mini_app(event)
        return
    
    # Определяем режим
    data = get_user_data(chat_id)
    has_history = len(data["history"]) > 0
    
    detected = detect_mode(text, has_history)
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
    print("✅ Режимы: текст, контекст, языки, мини-приложение")
    print("Ожидаю сообщения...\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
