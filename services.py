import requests
import re
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Tuple, Optional
import urllib3
import time
import os
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = os.environ.get("GIGACHAT_CLIENT_ID", "01a0bafa-206f-7e07-a2e7-df9e0acea285")
CLIENT_SECRET = os.environ.get("GIGACHAT_CLIENT_SECRET", "93e085d7-803b-4fe2-b1da-468aff78a450")

_token_cache = {"token": None, "expires_at": 0}

FORMATTING_RULES = """

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА ФОРМАТИРОВАНИЯ:
❌ НИКОГДА не используй:
- LaTeX ($...$, $$...$$, \\frac, \\sqrt, \\alpha, \\cdot, \\left, \\right)
- Markdown (**жирный**, ### заголовки, --- разделители, _курсив_)
- Символы `^` для степеней (пиши x² вместо x^2)
- Символы `_` для индексов (пиши x₁ вместо x_1)

✅ ВСЕГДА используй:
- Unicode-символы: α, β, γ, π, √, ≤, ≥, ≠, ×, ÷, ±, ∞, °
- Надстрочные/подстрочные: x², x³, 10⁸⁰, x₁, a₂
- Для дробей: просто пиши "a/b" или "(a)/(b)" вместо \\frac{a}{b}
- Для списков: цифры "1.", "2." или символы "•", "►"
- Для выделения: эмодзи (📌, ✨, ⚡) вместо жирного текста
- Для разделителей: просто пустые строки
"""

LANGUAGE_RULES = """

ЯЗЫКОВОЕ ПОВЕДЕНИЕ:
- Ты понимаешь ВСЕ языки мира: русский, английский, немецкий, французский, испанский, китайский, японский и любые другие
- ВСЕГДА отвечай на том языке, на котором пишет ученик
- Если ученик попросит перевести — переведи на указанный язык
- Помогай с изучением иностранных языков: перевод, грамматика, практика
"""

PROMPTS = {
    "planner": f"""Ты — умный планировщик подготовки к экзаменам. 

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
{FORMATTING_RULES}
{LANGUAGE_RULES}
Отвечай структурированно, с эмодзи.""",

    "homework": f"""Ты — ИИ-наставник, помогающий с домашкой методом Сократа. 

ВАЖНО: 
- НИКОГДА не давай готовый ответ
- Задавай наводящие вопросы
- Ты помнишь ВЕСЬ разговор с учеником
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "explain": f"""Ты — учитель, объясняющий сложные темы простым языком.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "tests": f"""Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов. В конце напиши правильные ответы.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "motivation": f"""Ты — дружелюбный мотиватор для школьников.

ВАЖНО: 
- Ты помнишь ВЕСЬ разговор с учеником
- Задавай уточняющие вопросы, если контекст неясен
{LANGUAGE_RULES}""",

    "videos": f"""Ты — помощник по поиску видеоуроков. Дай ссылки на поиск видео по теме ученика.

Используй ТОЛЬКО эти форматы поисковых ссылок:
- Поиск на RuTube: https://rutube.ru/search/?q=ТЕМА
- Поиск на VK Видео: https://vk.com/video?q=ТЕМА
- Поиск на YouTube: https://www.youtube.com/results?search_query=ТЕМА
- Поиск на Coursera: https://www.coursera.org/courses?query=ТЕМА

Замени ТЕМА на предмет/тему ученика.
{LANGUAGE_RULES}""",

    "journal": f"""Ты — умный помощник по анализу школьных оценок и успеваемости.

Ты умеешь:
- Анализировать оценки по предметам
- Считать средний балл
- Находить слабые и сильные предметы
- Давать рекомендации по улучшению успеваемости
- Помогать планировать подготовку по проблемным предметам
- Отвечать на вопросы о динамике оценок

ВАЖНО: 
- Используй данные об оценках из контекста разговора
- Если ученик только что добавил оценки через команды — анализируй их
- Отвечай дружелюбно и поддерживающе, но честно
- Предлагай конкретные шаги для улучшения
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "offline": f"""Ты — помощник по оффлайн-обучению. Дай ссылки на проверенные образовательные ресурсы.

Используй ТОЛЬКО эти проверенные сайты:
- Фоксфорд: https://foxford.ru
- Решу ЕГЭ: https://ege.sdamgia.ru
- Решу ОГЭ: https://oge.sdamgia.ru
- Учи.ру: https://uchi.ru
- Библиотека МЭШ: https://uchebnik.mos.ru
- Интернетурок: https://interneturok.ru
- Duolingo: https://www.duolingo.com (для иностранных языков)
{LANGUAGE_RULES}""",

    "context": f"""Ты — дружелюбный ИИ-наставник для школьников.

КРИТИЧЕСКИ ВАЖНО: Ученик задаёт вопрос, который относится к предыдущему сообщению в разговоре.
Внимательно прочитай историю разговора и пойми, о чём именно спрашивает ученик.
{FORMATTING_RULES}
{LANGUAGE_RULES}
Отвечай в контексте предыдущего разговора.""",

    "languages": f"""Ты — эксперт по иностранным языкам: английскому, немецкому, французскому, испанскому, китайскому и другим.

Ты можешь:
- Переводить текст между любыми языками
- Объяснять грамматику простыми словами
- Проверять орфографию и пунктуацию
- Предлагать упражнения для практики
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "general": f"""Ты — дружелюбный ИИ-наставник для школьников.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
{FORMATTING_RULES}
{LANGUAGE_RULES}
Помогай с учёбой.""",
}

MODE_KEYWORDS = {
    "planner": ["план", "расписан", "подготов", "экзамен", "огэ", "егэ", "контрольн", "сколько времени", "plan", "schedule", "exam"],
    "homework": ["домашк", "дз", "задач", "упражнен", "решить", "уравнен", "homework", "task", "exercise"],
    "explain": ["объясни", "что такое", "как работает", "расскажи про", "почему", "explain", "what is", "how"],
    "tests": ["тест", "проверь", "викторин", "квиз", "test", "quiz"],
    "motivation": ["устал", "не хочу", "лень", "мотивац", "скучно", "тяжело", "tired", "bored"],
    "videos": ["видео", "урок", "посмотреть", "ролик", "ютуб", "youtube", "rutube", "ссылк", "video", "lesson"],
    "journal": ["оценк", "журнал", "мэш", "дневник", "четверт", "полугод", "средний балл", "успеваемост", "предмет", "grade", "mark", "average"],
    "offline": ["оффлайн", "скачать", "без интернета", "материал", "сайт", "ресурс", "учебник", "resource"],
    "context": ["почему", "зачем", "что именно", "знаешь", "понимаешь", "объясни", "уточни", "why", "what"],
    "languages": ["перевод", "переведи", "translate", "english", "deutsch", "немецкий", "английский", "французский", "french", "испанский", "spanish", "язык", "grammar", "грамматик", "word"],
}

# Маппинги раскладок
EN_TO_RU = {
    'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е', 'y': 'н', 'u': 'г',
    'i': 'ш', 'o': 'щ', 'p': 'з', '[': 'х', ']': 'ъ', 'a': 'ф', 's': 'ы',
    'd': 'в', 'f': 'а', 'g': 'п', 'h': 'р', 'j': 'о', 'k': 'л', 'l': 'д',
    ';': 'ж', "'": 'э', 'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и',
    'n': 'т', 'm': 'ь', ',': 'б', '.': 'ю', '/': '.', '`': 'ё',
    'Q': 'Й', 'W': 'Ц', 'E': 'У', 'R': 'К', 'T': 'Е', 'Y': 'Н', 'U': 'Г',
    'I': 'Ш', 'O': 'Щ', 'P': 'З', '{': 'Х', '}': 'Ъ', 'A': 'Ф', 'S': 'Ы',
    'D': 'В', 'F': 'А', 'G': 'П', 'H': 'Р', 'J': 'О', 'K': 'Л', 'L': 'Д',
    ':': 'Ж', '"': 'Э', 'Z': 'Я', 'X': 'Ч', 'C': 'С', 'V': 'М', 'B': 'И',
    'N': 'Т', 'M': 'Ь', '<': 'Б', '>': 'Ю', '?': ',', '~': 'Ё', '@': '"',
    '#': '№', '$': ';', '^': ':', '&': '?'
}

RU_TO_EN = {v: k for k, v in EN_TO_RU.items()}

ENGLISH_COMMON_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
    'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
    'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
    'hello', 'hi', 'hey', 'thanks', 'please', 'sorry', 'yes', 'no', 'ok',
    'how', 'are', 'you', 'what', 'where', 'when', 'why', 'which',
    'am', 'is', 'was', 'were', 'been', 'being', 'has', 'had',
    'does', 'did', 'doing', 'done', 'will', 'would', 'should', 'could',
    'math', 'physics', 'chemistry', 'biology', 'history', 'science',
    'english', 'german', 'french', 'spanish', 'russian',
    'translate', 'translation', 'grammar', 'vocabulary', 'word',
    'help', 'thank', 'welcome', 'student', 'school', 'teacher',
    'class', 'lesson', 'homework', 'exam', 'test', 'book',
    'today', 'tomorrow', 'yesterday', 'week', 'month', 'year',
    'big', 'small', 'good', 'bad', 'nice', 'beautiful',
    'love', 'like', 'hate', 'want', 'need', 'have',
    'go', 'going', 'went', 'come', 'see', 'look',
    'think', 'know', 'say', 'tell', 'make', 'do',
    'find', 'give', 'take', 'get', 'very', 'really'
}

RUSSIAN_COMMON_WORDS = {
    'и', 'в', 'не', 'на', 'я', 'быть', 'с', 'он', 'а', 'это',
    'как', 'то', 'что', 'этот', 'по', 'но', 'они', 'к', 'у', 'ты',
    'из', 'мы', 'за', 'вы', 'так', 'же', 'от', 'о', 'весь', 'при',
    'она', 'для', 'один', 'тот', 'когда', 'также', 'или', 'нет',
    'до', 'его', 'себя', 'вот', 'уже', 'да', 'было', 'если', 'ещё',
    'чтобы', 'там', 'через', 'будет', 'ну', 'всё', 'только',
    'привет', 'здравствуй', 'спасибо', 'пожалуйста', 'извини',
    'хорошо', 'плохо', 'отлично', 'замечательно',
    'математика', 'физика', 'химия', 'биология', 'история',
    'русский', 'английский', 'немецкий', 'французский',
    'перевод', 'ученик', 'школа', 'учитель', 'класс', 'урок',
    'домашка', 'экзамен', 'книга', 'задача', 'решение', 'ответ',
    'сегодня', 'завтра', 'вчера', 'неделя', 'месяц', 'год',
    'большой', 'маленький', 'хороший', 'плохой', 'красивый',
    'любить', 'нравиться', 'хотеть', 'мочь', 'должен',
    'идти', 'видеть', 'понимать', 'знать', 'говорить', 'делать'
}


def count_language_matches(text: str, word_set: set) -> int:
    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ]+', text.lower())
    return sum(1 for word in words if word in word_set)


def detect_real_language(text: str) -> Tuple[str, str]:
    text_lower = text.lower()
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    
    if latin_chars > cyrillic_chars and latin_chars > 0:
        en_score_original = count_language_matches(text, ENGLISH_COMMON_WORDS)
        converted_to_ru = ''.join(EN_TO_RU.get(c, c) for c in text)
        ru_score_converted = count_language_matches(converted_to_ru, RUSSIAN_COMMON_WORDS)
        
        if en_score_original > ru_score_converted:
            return text, "english"
        
        if ru_score_converted > en_score_original and ru_score_converted >= 2:
            print(f"⌨️ Исправлена раскладка EN→RU")
            return converted_to_ru, "russian"
        
        return text, "unknown"
    
    elif cyrillic_chars > latin_chars and cyrillic_chars > 0:
        ru_score_original = count_language_matches(text, RUSSIAN_COMMON_WORDS)
        converted_to_en = ''.join(RU_TO_EN.get(c, c) for c in text)
        en_score_converted = count_language_matches(converted_to_en, ENGLISH_COMMON_WORDS)
        
        if ru_score_original >= en_score_converted:
            return text, "russian"
        
        if en_score_converted > ru_score_original and en_score_converted >= 2:
            print(f"⌨️ Исправлена раскладка RU→EN")
            return converted_to_en, "english"
        
        return text, "unknown"
    
    return text, "unknown"


def fix_keyboard_layout(text: str) -> str:
    fixed_text, language = detect_real_language(text)
    return fixed_text


# ============================================
# МОДУЛЬ АНАЛИЗА ОЦЕНОК (МЭШ-подобный дневник)
# ============================================

class GradeAnalyzer:
    """Анализатор школьных оценок (аналог МЭШ-дневника)"""
    
    # Нормализация названий предметов
    SUBJECT_ALIASES = {
        'матем': 'Математика', 'математик': 'Математика', 'алгебр': 'Математика', 
        'геометр': 'Математика', 'math': 'Математика',
        'русск': 'Русский язык', 'русский': 'Русский язык', 'russian': 'Русский язык',
        'литер': 'Литература', 'литра': 'Литература',
        'англ': 'Английский язык', 'английск': 'Английский язык', 'ингл': 'Английский язык',
        'английский': 'Английский язык', 'english': 'Английский язык',
        'нем': 'Немецкий язык', 'немецк': 'Немецкий язык', 'герман': 'Немецкий язык',
        'физ': 'Физика', 'физика': 'Физика', 'physics': 'Физика',
        'хим': 'Химия', 'химия': 'Химия', 'chemistry': 'Химия',
        'биолог': 'Биология', 'био': 'Биология', 'biology': 'Биология',
        'истор': 'История', 'история': 'История', 'history': 'История',
        'географ': 'География', 'гео': 'География', 'geography': 'География',
        'информ': 'Информатика', 'инфа': 'Информатика', 'программир': 'Информатика',
        'компьютер': 'Информатика', 'informatics': 'Информатика',
        'общество': 'Обществознание', 'обществознан': 'Обществознание',
        'физр': 'Физкультура', 'физкультур': 'Физкультура', 'физкультура': 'Физкультура',
        'спорт': 'Физкультура', 'pe': 'Физкультура',
        'музык': 'Музыка', 'музыка': 'Музыка', 'музы': 'Музыка',
        'изобраз': 'ИЗО', 'изо': 'ИЗО', 'рисован': 'ИЗО',
        'технолог': 'Технология', 'труд': 'Технология',
        'экологи': 'Экология', 'экология': 'Экология',
    }
    
    @staticmethod
    def normalize_subject(subject: str) -> str:
        """Нормализует название предмета"""
        subject_lower = subject.lower().strip()
        for alias, canonical in GradeAnalyzer.SUBJECT_ALIASES.items():
            if alias in subject_lower:
                return canonical
        # Если не нашли — возвращаем с заглавной буквы
        return subject.strip().capitalize()
    
    @staticmethod
    def parse_grades(text: str) -> Tuple[Optional[str], List[int]]:
        """Парсит оценки из текста. Возвращает (предмет, список_оценок)"""
        text_lower = text.lower()
        
        # Ищем все числа от 1 до 5 (оценки)
        grades = re.findall(r'\b([1-5])\b', text)
        grades = [int(g) for g in grades if 1 <= int(g) <= 5]
        
        if not grades:
            return None, []
        
        # Ищем название предмета
        subject = None
        for alias, canonical in GradeAnalyzer.SUBJECT_ALIASES.items():
            if alias in text_lower:
                subject = canonical
                break
        
        # Если предмета нет, пытаемся найти первое существительное перед оценками
        if not subject:
            # Ищем паттерн: "предмет оценка" или "предмет: оценка"
            match = re.search(r'([а-яёa-z]+)[\s:]+[1-5]', text_lower)
            if match:
                subject = GradeAnalyzer.normalize_subject(match.group(1))
        
        return subject, grades
    
    @staticmethod
    def add_grades(user_grades: dict, subject: str, new_grades: List[int]) -> str:
        """Добавляет оценки и возвращает сообщение-подтверждение"""
        if subject not in user_grades:
            user_grades[subject] = []
        
        user_grades[subject].extend(new_grades)
        
        grades_str = ", ".join(str(g) for g in new_grades)
        total = len(user_grades[subject])
        avg = sum(user_grades[subject]) / total
        
        emoji = "🎉" if avg >= 4.5 else "👍" if avg >= 3.5 else "💪"
        
        msg = f"{emoji} Оценки добавлены!\n"
        msg += f"📚 {subject}: +{grades_str}\n"
        msg += f"📊 Всего оценок: {total}, средний балл: {avg:.2f}\n\n"
        msg += "Напиши 'мои оценки', чтобы увидеть все."
        
        return msg
    
    @staticmethod
    def format_grades(user_grades: dict) -> str:
        """Форматирует все оценки в красивое сообщение"""
        if not user_grades:
            return "📭 У тебя пока нет оценок.\nДобавь их командой: 'добавь оценку математика 5'"
        
        msg = "📊 ТВОИ ОЦЕНКИ (аналог МЭШ)\n"
        msg += "━" * 25 + "\n\n"
        
        total_sum = 0
        total_count = 0
        
        for subject, grades in sorted(user_grades.items()):
            if not grades:
                continue
            avg = sum(grades) / len(grades)
            total_sum += sum(grades)
            total_count += len(grades)
            
            # Эмодзи в зависимости от среднего балла
            if avg >= 4.5:
                emoji = "🌟"
            elif avg >= 4.0:
                emoji = "✅"
            elif avg >= 3.5:
                emoji = "👌"
            else:
                emoji = "⚠️"
            
            grades_str = " ".join(str(g) for g in grades)
            msg += f"{emoji} {subject}\n"
            msg += f"   Оценки: {grades_str}\n"
            msg += f"   Средний: {avg:.2f}\n\n"
        
        if total_count > 0:
            overall_avg = total_sum / total_count
            msg += "━" * 25 + "\n"
            msg += f"📈 ОБЩИЙ СРЕДНИЙ БАЛЛ: {overall_avg:.2f}\n\n"
            
            # Находим лучший и худший предметы
            subject_avgs = {s: sum(g)/len(g) for s, g in user_grades.items() if g}
            if subject_avgs:
                best = max(subject_avgs, key=subject_avgs.get)
                worst = min(subject_avgs, key=subject_avgs.get)
                msg += f"💪 Лучший предмет: {best} ({subject_avgs[best]:.2f})\n"
                msg += f"📚 Нужно подтянуть: {worst} ({subject_avgs[worst]:.2f})\n"
        
        return msg
    
    @staticmethod
    def get_analysis(user_grades: dict) -> str:
        """Возвращает подробный анализ успеваемости"""
        if not user_grades:
            return "📭 Нет данных для анализа. Добавь оценки командой: 'добавь оценку математика 5'"
        
        msg = "🎓 АНАЛИЗ УСПЕВАЕМОСТИ\n"
        msg += "━" * 25 + "\n\n"
        
        # Считаем средний балл по каждому предмету
        subject_avgs = {}
        for subject, grades in user_grades.items():
            if grades:
                subject_avgs[subject] = sum(grades) / len(grades)
        
        if not subject_avgs:
            return "📭 Нет данных для анализа."
        
        overall_avg = sum(subject_avgs.values()) / len(subject_avgs)
        msg += f"📊 Общий средний балл: {overall_avg:.2f}\n\n"
        
        # Категории предметов
        excellent = [s for s, a in subject_avgs.items() if a >= 4.5]
        good = [s for s, a in subject_avgs.items() if 4.0 <= a < 4.5]
        average = [s for s, a in subject_avgs.items() if 3.5 <= a < 4.0]
        weak = [s for s, a in subject_avgs.items() if a < 3.5]
        
        if excellent:
            msg += f"🌟 Отлично (4.5+): {', '.join(excellent)}\n"
        if good:
            msg += f"✅ Хорошо (4.0-4.5): {', '.join(good)}\n"
        if average:
            msg += f"👌 Нормально (3.5-4.0): {', '.join(average)}\n"
        if weak:
            msg += f"⚠️ Требует внимания (<3.5): {', '.join(weak)}\n"
        
        msg += "\n💡 РЕКОМЕНДАЦИИ:\n"
        
        if weak:
            msg += f"1. Сосредоточься на: {', '.join(weak)}\n"
            msg += "2. Попроси помощи у учителя или одноклассников\n"
            msg += "3. Напиши мне 'план подготовки по [предмет]' — составлю план!\n"
        elif average:
            msg += f"1. Подтяни: {', '.join(average)} до 4.5+\n"
            msg += "2. Решай больше задач и упражнений\n"
        else:
            msg += "1. Так держать! 🎉\n"
            msg += "2. Пробуй задачи повышенной сложности для развития"
        
        return msg
    
    @staticmethod
    def delete_subject(user_grades: dict, subject_query: str) -> str:
        """Удаляет предмет из дневника"""
        subject_query = GradeAnalyzer.normalize_subject(subject_query)
        
        for subject in list(user_grades.keys()):
            if subject.lower() == subject_query.lower():
                del user_grades[subject]
                return f"🗑️ Предмет '{subject}' удалён из дневника."
        
        return f"❓ Предмет '{subject_query}' не найден в твоём дневнике."


# ============================================
# ОСНОВНОЙ СЕРВИС ИИ
# ============================================

def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]
    print("🔑 Получение нового токена GigaChat...")
    for attempt in range(3):
        try:
            response = requests.post(
                url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded", "RqUID": "00000000-0000-0000-0000-000000000000"},
                data="scope=GIGACHAT_API_PERS",
                verify=False,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            _token_cache["token"] = data["access_token"]
            _token_cache["expires_at"] = now + 1700
            print("✅ Токен получен и закэширован")
            return _token_cache["token"]
        except Exception as e:
            print(f"⚠️ Попытка {attempt+1} получения токена не удалась: {e}")
            time.sleep(2)
    raise Exception("Не удалось получить токен GigaChat после 3 попыток")


def detect_mode(text: str, has_history: bool = False) -> str:
    text_lower = text.lower().strip()
    
    if has_history and len(text_lower) < 30:
        context_keywords = ["почему", "зачем", "что", "как", "когда", "где", "знаешь", "понимаешь",
                          "why", "what", "when", "where", "how"]
        if any(kw in text_lower for kw in context_keywords):
            print(f"🎯 Определён контекстный вопрос")
            return "context"
    
    scores = {}
    for mode_id, keywords in MODE_KEYWORDS.items():
        if mode_id == "context":
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[mode_id] = score
    
    if scores:
        best_mode = max(scores, key=scores.get)
        print(f"🎯 Режим: {best_mode}")
        return best_mode
    
    return "general"


class AIService:
    @staticmethod
    def process_message(message: str, feature_id: str = "general", history: list = None, 
                       grades_context: str = "") -> str:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🤖 Запрос к GigaChat (режим: {feature_id}, история: {len(history) if history else 0})")
                token = _get_token()
                system_prompt = PROMPTS.get(feature_id, PROMPTS["general"])
                
                # Если есть данные об оценках — добавляем в контекст
                if grades_context and feature_id == "journal":
                    system_prompt += f"\n\n📊 ТЕКУЩИЕ ОЦЕНКИ УЧЕНИКА:\n{grades_context}"
                
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": message})
                
                response = requests.post(
                    url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "model": "GigaChat:latest",
                        "messages": messages,
                        "max_tokens": 600,
                        "temperature": 0.7
                    },
                    verify=False,
                    timeout=30
                )
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return "Извини, ИИ сейчас недоступен. Попробуй через минуту."
                
                result = response.json()
                
                if isinstance(result, dict) and 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0].get('message', {}).get('content', '')
                    if content:
                        content = format_latex_to_unicode(content)
                        print(f"✅ Ответ получен ({len(content)} символов)")
                        return content
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "Извини, не удалось получить ответ от ИИ."
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"⏱️ Таймаут, пробуем ещё раз...")
                    time.sleep(3)
                    continue
                return "Извини, ИИ не ответил вовремя. Попробуй ещё раз."
            except Exception as e:
                print(f"⚠️ Ошибка GigaChat: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"Извини, произошла ошибка: {str(e)}"
        
        return "Извини, ИИ временно недоступен. Попробуй позже."


class PlannerService:
    @staticmethod
    def generate_plan(available_minutes: int, subjects: list) -> Dict:
        if available_minutes <= 0:
            return {"error": "Время не может быть отрицательным"}
        time_per_subject = available_minutes // len(subjects)
        schedule = [{"subject": subj, "time_allocated": f"{time_per_subject} мин", "advice": "Начни с теории, потом реши 2 задачи."} for subj in subjects]
        return {"total_time": available_minutes, "schedule": schedule}
