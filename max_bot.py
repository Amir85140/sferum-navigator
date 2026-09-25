import asyncio
import logging
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
    chat_id = event.message.chat.chat_id
    clear_history(chat_id)
    welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n\n"
    welcome += "Я запомню наш разговор и буду учитывать контекст.\n"
    welcome += "Напиши 'сброс', чтобы начать заново.\n"
    await event.message.answer(welcome)

@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    text = event.message.body.text
    chat_id = event.message.chat.chat_id
    
    if not text:
        await event.message.answer("Отправь текст или фото задания!")
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
    print("🚀 БОТ Sferum Navigator с GigaChat запущен!")
    print("✅ Подключено к MAX!")
    print("Ожидаю сообщения...\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
