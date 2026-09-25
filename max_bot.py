import asyncio
import logging
import json
import os
from typing import Optional, Tuple, List
from dotenv import load_dotenv
from maxapi import Bot, Dispatcher, F
from maxapi.types import BotStarted, MessageCreated
from maxapi.filters.command import CommandStart
from services import (AIService, detect_mode, fix_keyboard_layout, 
                      GradeAnalyzer, should_check_for_grades, extract_grades_with_ai)

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.environ["MAX_TOKEN"])
dp = Dispatcher()

# Файл для сохранения данных пользователей (оценки, история)
DATA_FILE = "user_data.json"

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


# ============================================
# СОХРАНЕНИЕ И ЗАГРУЗКА ДАННЫХ
# ============================================

def load_user_data():
    """Загружает данные пользователей из файла при старте"""
    global user_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            print(f"💾 Загружены данные {len(user_data)} пользователей из {DATA_FILE}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки данных: {e}")
            user_data = {}
    else:
        print(f"📄 Файл {DATA_FILE} не найден — начинаем с чистого листа")
        user_data = {}


def save_user_data():
    """Сохраняет данные пользователей в файл"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        print(f"💾 Данные сохранены в {DATA_FILE}")
    except Exception as e:
        print(f"⚠️ Ошибка сохранения данных: {e}")


def get_user_data(user_id):
    """Получает данные пользователя, создаёт если нет"""
    user_id = str(user_id)  # Ключи в JSON должны быть строками
    if user_id not in user_data:
        user_data[user_id] = {"history": [], "mode": "general", "grades": {}}
    return user_data[user_id]


def add_to_history(user_id, role, content):
    data = get_user_data(user_id)
    data["history"].append({"role": role, "content": content})
    if len(data["history"]) > MAX_HISTORY_MESSAGES:
        data["history"] = data["history"][-MAX_HISTORY_MESSAGES:]


def clear_history(user_id):
    user_id = str(user_id)
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


def try_auto_detect_grades(text: str, chat_id: int) -> Optional[Tuple[str, List[int]]]:
    """
    Пытается автоматически определить, рассказывает ли пользователь об оценках.
    Если да — тихо ДОБАВЛЯЕТ их в дневник (не перезаписывает!) и возвращает (предмет, оценки).
    """
    if not should_check_for_grades(text):
        return None
    
    is_grades, subject, grades = extract_grades_with_ai(text)
    
    if is_grades and subject and grades:
        data = get_user_data(chat_id)
        
        # ДОБАВЛЯЕМ оценки (extend), а не перезаписываем
        if subject not in data["grades"]:
            data["grades"][subject] = []
        data["grades"][subject].extend(grades)
        
        # СОХРАНЯЕМ в файл сразу
        save_user_data()
        
        print(f"🎯 Добавлены оценки: {subject} → {grades} (всего: {len(data['grades'][subject])})")
        
        return subject, grades
    
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
    save_user_data()
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
        save_user_data()
        await event.message.answer("🎯 Привет! Я Sferum Navigator — ИИ-наставник для учёбы.\nНапиши 'помощь', чтобы увидеть список команд.")
        return
    
    if text_lower in ["сброс", "забудь", "очистить", "reset", "clear"]:
        clear_history(chat_id)
        save_user_data()
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
    
    # Команды просмотра дневника
    if text_lower in ["мои оценки", "оценки", "покажи оценки", "дневник", "журнал"]:
        data = get_user_data(chat_id)
        response = GradeAnalyzer.format_grades(data["grades"])
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", response)
        save_user_data()
        await event.message.answer(response)
        return
    
    if text_lower in ["анализ оценок", "анализ успеваемости", "как моя успеваемость"]:
        data = get_user_data(chat_id)
        response = GradeAnalyzer.get_analysis(data["grades"])
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", response)
        save_user_data()
        await event.message.answer(response)
        return
    
    # АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ОЦЕНОК ЧЕРЕЗ ИИ (тихое добавление)
    grades_info = try_auto_detect_grades(text, chat_id)
    added_grades_note = ""
    
    if grades_info:
        subject, grades = grades_info
        grades_str = ", ".join(str(g) for g in grades)
        added_grades_note = f"\n\n💾 P.S. Я сохранил твою оценку ({grades_str} по предмету '{subject}') в дневник. Напиши 'мои оценки', чтобы посмотреть все."
    
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
        
        # Если были добавлены оценки — добавляем контекст для ИИ
        if grades_info:
            subject, grades = grades_info
            grades_note_for_ai = f"\n\nВАЖНО: Ученик только что рассказал что получил оценки {grades} по предмету '{subject}'. Я (бот) сохранил их в его дневник. Ответь дружелюбно: поздравь, спроси о деталях, поддержи. Не упоминай явно 'я сохранил оценку' — я добавлю P.S. отдельно."
            if grades_context:
                grades_context += grades_note_for_ai
            else:
                grades_context = grades_note_for_ai
            mode = "journal"
        
        response = AIService.process_message(text, mode, data["history"], grades_context)
        
        # Добавляем P.S. про сохранение оценки
        if added_grades_note:
            response += added_grades_note
        
        add_to_history(chat_id, "user", text)
        add_to_history(chat_id, "assistant", response)
        save_user_data()
        
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await event.message.answer(response[i:i+4000])
        else:
            await event.message.answer(response)
    except Exception as e:
        print(f"❌ Ошибка ИИ: {e}")
        await event.message.answer("Извини, произошла ошибка. Попробуй через минуту.")

async def main():
    # Загружаем сохранённые данные при старте
    load_user_data()
    
    print("🚀 БОТ Sferum Navigator запущен!")
    print("✅ Режимы: текст, контекст, языки, умный дневник оценок")
    print("✅ Оценки сохраняются в файл и не теряются при перезапуске")
    print("Ожидаю сообщения...\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
