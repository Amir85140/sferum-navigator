from dotenv import load_dotenv
import os
import asyncio
from maxapi import Bot, types
from services import AIService, detect_mode

# Загружаем переменные окружения
load_dotenv()

# Инициализируем бота
bot = Bot(token=os.environ["MAX_TOKEN"])

# Хранилище истории для каждого пользователя
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

@bot.on.message()
async def handle_message(message: types.Message):
    text = message.text
    user_id = message.chat.chat_id
    
    if not text:
        await message.answer("Отправь текст или фото задания!")
        return
    
    text = text.strip()
    text_lower = text.lower()
    
    # Команды
    if text_lower in ["начать", "старт", "start"]:
        clear_history(user_id)
        welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n\n"
        welcome += "Я запомню наш разговор и буду учитывать контекст.\n"
        welcome += "Напиши 'сброс', чтобы начать заново.\n\n"
        welcome += "Ты можешь:\n"
        welcome += "📷 Прислать фото задания — я прочитаю и помогу.\n"
        welcome += "💬 Или просто написать вопрос.\n"
        await message.answer(welcome)
        return
    
    if text_lower in ["сброс", "забудь", "очистить"]:
        clear_history(user_id)
        await message.answer("🗑️ Готово! Чем помочь?")
        return
    
    if text_lower in ["помощь", "меню", "режимы", "старт"]:
        menu = "🎯 Я сам определю режим по твоему вопросу.\n"
        menu += "Просто напиши, что нужно, или пришли фото задания!\n"
        menu += "Команды: 'сброс' — начать заново"
        await message.answer(menu)
        return
    
    # Определяем режим
    detected = detect_mode(text)
    data = get_user_data(user_id)
    if detected != "general":
        data["mode"] = detected
    mode = data["mode"]
    
    print(f"🎯 Режим: {MODES.get(mode, 'Общий')} (история: {len(data['history'])} сообщ.)")
    
    try:
        # Отправляем запрос к GigaChat
        response = AIService.process_message(text, mode, data["history"])
        
        # Сохраняем в историю
        add_to_history(user_id, "user", text)
        add_to_history(user_id, "assistant", response)
        
        # Отправляем ответ
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await message.answer(response[i:i+4000])
        else:
            await message.answer(response)
            
    except Exception as e:
        print(f"❌ Ошибка ИИ: {e}")
        await message.answer("Извини, произошла ошибка. Попробуй через минуту.")

if __name__ == "__main__":
    print("🚀 БОТ Sferum Navigator с GigaChat запущен!")
    print("✅ Подключено к MAX!")
    print("Ожидаю сообщения...\n")
    bot.run_forever()
