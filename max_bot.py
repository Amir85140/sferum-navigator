import asyncio
import logging
from dotenv import load_dotenv
import os
from maxapi import Bot, Dispatcher, F
from maxapi.types import BotStarted, MessageCreated
from maxapi.filters.command import CommandStart
from services import (AIService, detect_mode, fix_keyboard_layout, 
                      GradeAnalyzer, should_check_for_grades, extract_grades_with_ai)

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
    "videos": "🎥 Видеоуроки", "journal": "📚 Оценки и дневник",
    "offline": "📱 Оффлайн материалы", "context": "🔗 Контекст",
    "languages": "🌍 Иностранные языки"
}

def get_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"history": [], "mode": "general", "grades": {}}
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


def get_grades_context_for_ai(chat_id: int) -> str:
    """Формирует контекст оценок для ИИ"""
    data = get_user_data(chat_id)
    if not data["grades"]:
        return ""
    
    context = ""
    for subject, grades in data["grades"].items():
        if grades:
            avg = sum(grades) / len(grades)
            context += f"{subject}: {', '.join(map(str, grades))} (средний: {avg:.2f})\n"
    return context


def try_auto_detect_grades(text: str, chat_id: int) -> str:
    """
    Пытается автоматически определить, рассказывает ли пользователь об оценках.
    Если да — добавляет их в дневник и возвращает сообщение-подтверждение.
    Если нет — возвращает None.
    """
    # Быстрая проверка на триггеры
    if not should_check_for_grades(text):
        return None
    
    # Умная проверка через ИИ
    is_grades, subject, grades = extract_grades_with_ai(text)
    
    if is_grades and subject and grades:
        data = get_user_data(chat_id)
        confirmation = GradeAnalyzer.add_grades(data["grades"], subject, grades)
        
        # Сохраняем в историю
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", confirmation)
        
        return confirmation
    
    return None


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
    welcome += "📚 Умный дневник оценок — просто расскажи о своих оценках, я сам добавлю!\n"
    welcome += "✅ Проверка знаний через тесты и квизы\n"
    welcome += "🎥 Поиск видеоуроков\n"
    welcome += "💪 Мотивация и поддержка при выгорании"
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
    
    # Автоисправление раскладки
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
        menu += "🌍 Пиши на любом языке — я пойму!\n\n"
        menu += "📚 Дневник оценок:\n"
        menu += "Просто расскажи о своих оценках — я сам добавлю!\n"
        menu += "Например: 'получил пятёрку по математике'\n\n"
        menu += "'мои оценки' — посмотреть все\n"
        menu += "'анализ успеваемости' — подробный разбор"
        await event.message.answer(menu)
        return
    
    # Команды просмотра дневника (только просмотр, без ручного добавления)
    if text_lower in ["мои оценки", "оценки", "покажи оценки", "дневник", "журнал"]:
        data = get_user_data(chat_id)
        response = GradeAnalyzer.format_grades(data["grades"])
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", response)
        await event.message.answer(response)
        return
    
    if text_lower in ["анализ оценок", "анализ успеваемости", "как моя успеваемость"]:
        data = get_user_data(chat_id)
        response = GradeAnalyzer.get_analysis(data["grades"])
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", response)
        await event.message.answer(response)
        return
    
    # АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ОЦЕНОК ЧЕРЕЗ ИИ
    auto_grade_response = try_auto_detect_grades(text, chat_id)
    if auto_grade_response:
        print(f"🎯 Автоматически обнаружены оценки!")
        await event.message.answer(auto_grade_response)
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
        grades_context = ""
        if mode == "journal":
            grades_context = get_grades_context_for_ai(chat_id)
        
        response = AIService.process_message(text, mode, data["history"], grades_context)
        
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
    print("✅ Режимы: текст, контекст, языки, умный дневник оценок")
    print("Ожидаю сообщения...\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
