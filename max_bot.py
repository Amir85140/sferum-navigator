import asyncio
import logging
import re
from dotenv import load_dotenv
import os
from maxapi import Bot, Dispatcher, F
from maxapi.types import BotStarted, MessageCreated
from maxapi.filters.command import CommandStart
from services import AIService, detect_mode, fix_keyboard_layout, GradeAnalyzer

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


def handle_grade_command(text: str, chat_id: int) -> str:
    """Обрабатывает команды, связанные с оценками"""
    data = get_user_data(chat_id)
    text_lower = text.lower().strip()
    
    # Команда: показать все оценки
    if text_lower in ["мои оценки", "оценки", "покажи оценки", "дневник", "журнал"]:
        return GradeAnalyzer.format_grades(data["grades"])
    
    # Команда: анализ успеваемости
    if text_lower in ["анализ оценок", "анализ успеваемости", "проанализируй оценки", "как моя успеваемость"]:
        return GradeAnalyzer.get_analysis(data["grades"])
    
    # Команда: удалить предмет
    if text_lower.startswith("удали предмет"):
        subject = text_lower.replace("удали предмет", "").strip()
        if not subject:
            return "❓ Укажи предмет: 'удали предмет математика'"
        return GradeAnalyzer.delete_subject(data["grades"], subject)
    
    # Команда: добавить оценку (разные форматы)
    add_patterns = [
        "добавь оценку", "добавить оценку", "запиши оценку", "записать оценку",
        "новая оценка", "получил оценку", "получила оценку"
    ]
    
    if any(text_lower.startswith(p) for p in add_patterns):
        subject, grades = GradeAnalyzer.parse_grades(text)
        
        if not subject:
            return "❓ Не смог определить предмет.\nПример: 'добавь оценку математика 5'"
        
        if not grades:
            return "❓ Не нашёл оценки (от 1 до 5).\nПример: 'добавь оценку математика 5'"
        
        return GradeAnalyzer.add_grades(data["grades"], subject, grades)
    
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


@dp.bot_started()
async def bot_started(event: BotStarted):
    welcome = "🎯 Привет! / Hello! / Hallo! / Bonjour!\n\n"
    welcome += "Я Sferum Navigator — ИИ-наставник для учёбы.\n"
    welcome += "Я запомню наш разговор и буду учитывать контекст.\n"
    welcome += "Напиши 'сброс', чтобы начать заново.\n\n"
    welcome += "📌 Что я умею:\n"
    welcome += "📝 Помощь с домашкой (метод Сократа)\n"
    welcome += "📅 Планирование подготовки к ОГЭ/ЕГЭ\n"
    welcome += "🎓 Объяснение сложных тем простым языком\n"
    welcome += "🌍 Практика иностранных языков и переводы\n"
    welcome += "📚 Дневник оценок (аналог МЭШ)\n"
    welcome += "✅ Проверка знаний через тесты и квизы\n"
    welcome += "🎥 Поиск видеоуроков\n"
    welcome += "💪 Мотивация и поддержка при выгорании\n\n"
    welcome += "📊 Команды дневника оценок:\n"
    welcome += "• 'добавь оценку математика 5' — добавить оценку\n"
    welcome += "• 'мои оценки' — посмотреть все оценки\n"
    welcome += "• 'анализ успеваемости' — подробный анализ\n"
    welcome += "• 'удали предмет физика' — удалить предмет"
    await bot.send_message(chat_id=event.chat_id, text=welcome)

@dp.message_created(CommandStart())
async def handle_start(event: MessageCreated):
    chat_id = get_chat_id(event)
    if not chat_id:
        return
    clear_history(chat_id)
    welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы."
    await event.message.answer(welcome)

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
    
    # Проверка команд управления
    if text_lower in ["начать", "старт", "start", "hello", "hi", "привет"]:
        clear_history(chat_id)
        welcome = "🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\n"
        welcome += "Напиши 'помощь', чтобы увидеть список команд."
        await event.message.answer(welcome)
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
        menu += "📊 Команды дневника оценок:\n"
        menu += "• 'добавь оценку математика 5'\n"
        menu += "• 'мои оценки'\n"
        menu += "• 'анализ успеваемости'"
        await event.message.answer(menu)
        return
    
    # Обработка команд для оценок
    grade_response = handle_grade_command(text, chat_id)
    if grade_response:
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", grade_response)
        await event.message.answer(grade_response)
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
        # Получаем контекст оценок для режима журнала
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
    print("✅ Режимы: текст, контекст, языки, дневник оценок (МЭШ)")
    print("Ожидаю сообщения...\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
