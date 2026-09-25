import requests
import re
from requests.auth import HTTPBasicAuth
from typing import Dict, Tuple
import urllib3
import time
import os

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

ПРИМЕРЫ:
❌ Плохо: $x^2 + \\frac{y}{2} = 0$, ### Заголовок, **жирный**
✅ Хорошо: x² + y/2 = 0, 📌 Заголовок, важный текст
"""

LANGUAGE_RULES = """

ЯЗЫКОВОЕ ПОВЕДЕНИЕ:
- Ты понимаешь ВСЕ языки мира: русский, английский, немецкий, французский, испанский, китайский, японский и любые другие
- ВСЕГДА отвечай на том языке, на котором пишет ученик
- Если ученик пишет на английском — отвечай на английском
- Если ученик пишет на русском — отвечай на русском
- Если ученик пишет на нескольких языках — отвечай на основном языке сообщения
- Если ученик попросит перевести — переведи на указанный язык
- Помогай с изучением иностранных языков: перевод, грамматика, практика
"""

PROMPTS = {
    "planner": f"""Ты — умный планировщик подготовки к экзаменам. 

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.
{FORMATTING_RULES}
{LANGUAGE_RULES}
Отвечай структурированно, с эмодзи.""",

    "homework": f"""Ты — ИИ-наставник, помогающий с домашкой методом Сократа. 

ВАЖНО: 
- НИКОГДА не давай готовый ответ
- Задавай наводящие вопросы
- Ты помнишь ВЕСЬ разговор с учеником
- Если ученик спрашивает "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте
- Помогай с иностранными языками: перевод, грамматика, упражнения
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "explain": f"""Ты — учитель, объясняющий сложные темы простым языком.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "tests": f"""Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов. В конце напиши правильные ответы.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "motivation": f"""Ты — дружелюбный мотиватор для школьников.

ВАЖНО: 
- Ты помнишь ВЕСЬ разговор с учеником
- Всегда учитывай контекст предыдущих сообщений
- Если ученик хвалит тебя ("ты молодец", "спасибо") и потом спрашивает "знаешь почему?" — отвечай в контексте его похвалы
- Задавай уточняющие вопросы, если контекст неясен
{LANGUAGE_RULES}""",

    "videos": f"""Ты — помощник по поиску видеоуроков. Дай ссылки на поиск видео по теме ученика.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

Используй ТОЛЬКО эти форматы поисковых ссылок:
- Поиск на RuTube: https://rutube.ru/search/?q=ТЕМА
- Поиск на VK Видео: https://vk.com/video?q=ТЕМА
- Поиск на YouTube: https://www.youtube.com/results?search_query=ТЕМА
- Поиск на Coursera: https://www.coursera.org/courses?query=ТЕМА

Замени ТЕМА на предмет/тему ученика.
{LANGUAGE_RULES}""",

    "journal": f"""Ты — помощник по интеграции с МЭШ. Анализируй оценки.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.
{LANGUAGE_RULES}""",

    "offline": f"""Ты — помощник по оффлайн-обучению. Дай ссылки на проверенные образовательные ресурсы.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

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

Примеры:
- Если ученик сказал "Ты молодец!" и потом спрашивает "Знаешь почему?" — он спрашивает, почему ты молодец
- Если ученик сказал "Мне не нравится математика" и потом спрашивает "Почему?" — он спрашивает, почему ему не нравится математика
- Если ученик задал вопрос и потом спрашивает "Что именно?" — он просит уточнить
{FORMATTING_RULES}
{LANGUAGE_RULES}
Отвечай в контексте предыдущего разговора. Задавай уточняющие вопросы, если контекст неясен.""",

    "languages": f"""Ты — эксперт по иностранным языкам: английскому, немецкому, французскому, испанскому, китайскому и другим.

Ты можешь:
- Переводить текст между любыми языками
- Объяснять грамматику простыми словами
- Проверять орфографию и пунктуацию
- Предлагать упражнения для практики
- Объяснять идиомы и сленг
- Помогать с произношением (писать транслитерацию)
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "general": f"""Ты — дружелюбный ИИ-наставник для школьников.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.
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
    "journal": ["оценк", "журнал", "мэш", "четверт", "полугод", "grade", "mark"],
    "offline": ["оффлайн", "скачать", "без интернета", "материал", "сайт", "ресурс", "учебник", "resource"],
    "context": ["почему", "зачем", "что именно", "знаешь", "понимаешь", "объясни", "уточни", "why", "what"],
    "languages": ["перевод", "переведи", "translate", "english", "deutsch", "немецкий", "английский", "французский", "french", "испанский", "spanish", "язык", "grammar", "грамматик", "word"],
}

# Маппинги раскладок клавиатуры
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

# Словари частых слов для распознавания языка
ENGLISH_COMMON_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
    'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
    'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
    'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
    'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
    'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
    'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us',
    'hello', 'hi', 'hey', 'thanks', 'please', 'sorry', 'yes', 'no', 'ok',
    'how', 'are', 'you', 'what', 'where', 'when', 'why', 'which', 'whose', 'whom',
    'am', 'is', 'was', 'were', 'been', 'being', 'has', 'had', 'having',
    'does', 'did', 'doing', 'done', 'will', 'would', 'should', 'could', 'might',
    'must', 'shall', 'can', 'may', 'need', 'dare', 'ought', 'used',
    'math', 'maths', 'mathematics', 'physics', 'chemistry', 'biology', 'history', 'science',
    'english', 'german', 'french', 'spanish', 'russian', 'chinese', 'japanese',
    'translate', 'translation', 'grammar', 'vocabulary', 'word', 'sentence', 'text',
    'help', 'please', 'thank', 'sorry', 'excuse', 'welcome',
    'student', 'school', 'teacher', 'class', 'lesson', 'homework', 'exam', 'test',
    'book', 'page', 'chapter', 'exercise', 'problem', 'solution', 'answer', 'question',
    'today', 'tomorrow', 'yesterday', 'week', 'month', 'year', 'hour', 'minute',
    'big', 'small', 'good', 'bad', 'nice', 'beautiful', 'ugly', 'fast', 'slow',
    'love', 'like', 'hate', 'want', 'need', 'have', 'has', 'had',
    'go', 'going', 'went', 'gone', 'come', 'coming', 'came',
    'see', 'seeing', 'saw', 'seen', 'look', 'looking', 'looked',
    'think', 'thinking', 'thought', 'know', 'knowing', 'knew', 'known',
    'say', 'saying', 'said', 'tell', 'telling', 'told',
    'make', 'making', 'made', 'do', 'doing', 'did', 'done',
    'find', 'finding', 'found', 'give', 'giving', 'gave', 'given',
    'take', 'taking', 'took', 'taken', 'get', 'getting', 'got', 'gotten',
    'very', 'really', 'quite', 'rather', 'pretty', 'fairly', 'extremely',
    'always', 'never', 'sometimes', 'often', 'usually', 'rarely', 'seldom',
    'here', 'there', 'everywhere', 'nowhere', 'somewhere', 'anywhere',
    'much', 'many', 'few', 'little', 'some', 'any', 'all', 'none',
    'more', 'less', 'most', 'least', 'better', 'worse', 'best', 'worst'
}

RUSSIAN_COMMON_WORDS = {
    'и', 'в', 'не', 'на', 'я', 'быть', 'с', 'он', 'а', 'это',
    'как', 'то', 'что', 'этот', 'по', 'но', 'они', 'к', 'у', 'ты',
    'из', 'мы', 'за', 'вы', 'так', 'же', 'от', 'о', 'весь', 'при',
    'она', 'для', 'один', 'тот', 'когда', 'также', 'или', 'нет', 'бы', 'был',
    'до', 'его', 'себя', 'вот', 'уже', 'да', 'было', 'если', 'ещё', 'были',
    'чтобы', 'там', 'через', 'будет', 'ну', 'всё', 'только', 'была', 'быть', 'были',
    'тебя', 'их', 'кто', 'даже', 'под', 'была', 'мне', 'так', 'все', 'наш',
    'тут', 'время', 'теперь', 'потом', 'очень', 'можно', 'после', 'более', 'над',
    'при', 'эти', 'между', 'надо', 'лишь', 'них', 'перед', 'того', 'ли', 'раз',
    'здесь', 'куда', 'почему', 'зато', 'потому', 'чуть', 'разве', 'тоже',
    'привет', 'здравствуй', 'спасибо', 'пожалуйста', 'извини', 'да', 'нет',
    'как', 'дела', 'ты', 'я', 'он', 'она', 'мы', 'вы', 'они',
    'хорошо', 'плохо', 'отлично', 'замечательно', 'ужасно',
    'математика', 'физика', 'химия', 'биология', 'история', 'география',
    'русский', 'английский', 'немецкий', 'французский', 'испанский',
    'перевод', 'переведи', 'графика', 'слово', 'предложение', 'текст',
    'ученик', 'школа', 'учитель', 'класс', 'урок', 'домашка', 'экзамен',
    'книга', 'страница', 'глава', 'упражнение', 'задача', 'решение', 'ответ',
    'сегодня', 'завтра', 'вчера', 'неделя', 'месяц', 'год', 'час', 'минута',
    'большой', 'маленький', 'хороший', 'плохой', 'красивый',
    'любить', 'нравиться', 'хотеть', 'мочь', 'должен',
    'идти', 'ходить', 'приходить', 'уходить',
    'видеть', 'смотреть', 'понимать', 'знать',
    'говорить', 'рассказывать', 'спрашивать',
    'делать', 'сделать', 'решать', 'решить',
    'находить', 'давать', 'брать', 'получать'
}


def count_language_matches(text: str, word_set: set) -> int:
    """Считает сколько слов из текста есть в словаре языка"""
    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ]+', text.lower())
    return sum(1 for word in words if word in word_set)


def detect_real_language(text: str) -> Tuple[str, str]:
    """
    Определяет настоящий язык текста.
    Возвращает: (исправленный_текст, язык)
    """
    text_lower = text.lower()
    
    # Считаем латиницу и кириллицу
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    
    # Если в основном латиница
    if latin_chars > cyrillic_chars and latin_chars > 0:
        # Считаем сколько английских слов есть в оригинале
        en_score_original = count_language_matches(text, ENGLISH_COMMON_WORDS)
        
        # Пробуем конвертировать в русский
        converted_to_ru = ''.join(EN_TO_RU.get(c, c) for c in text)
        ru_score_converted = count_language_matches(converted_to_ru, RUSSIAN_COMMON_WORDS)
        
        # Если английский имеет больше совпадений — оставляем как есть
        if en_score_original > ru_score_converted:
            print(f"🌍 Определён язык: английский ({en_score_original} совпадений)")
            return text, "english"
        
        # Если русский после конвертации имеет больше — значит это неправильная раскладка
        if ru_score_converted > en_score_original and ru_score_converted >= 2:
            print(f"⌨️ Исправлена раскладка EN→RU ({ru_score_converted} совпадений)")
            return converted_to_ru, "russian"
        
        # Не можем определить — оставляем как есть
        return text, "unknown"
    
    # Если в основном кириллица
    elif cyrillic_chars > latin_chars and cyrillic_chars > 0:
        # Считаем сколько русских слов есть в оригинале
        ru_score_original = count_language_matches(text, RUSSIAN_COMMON_WORDS)
        
        # Пробуем конвертировать в английский
        converted_to_en = ''.join(RU_TO_EN.get(c, c) for c in text)
        en_score_converted = count_language_matches(converted_to_en, ENGLISH_COMMON_WORDS)
        
        # Если русский имеет больше совпадений — оставляем
        if ru_score_original >= en_score_converted:
            return text, "russian"
        
        # Если английский после конвертации имеет больше — это неправильная раскладка
        if en_score_converted > ru_score_original and en_score_converted >= 2:
            print(f"⌨️ Исправлена раскладка RU→EN ({en_score_converted} совпадений)")
            return converted_to_en, "english"
        
        return text, "unknown"
    
    # Нет букв — возвращаем как есть
    return text, "unknown"


def fix_keyboard_layout(text: str) -> str:
    """Умное исправление раскладки клавиатуры с определением языка"""
    fixed_text, language = detect_real_language(text)
    return fixed_text


SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'n': 'ⁿ', 'i': 'ⁱ', 'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ',
    'x': 'ˣ', 'y': 'ʸ'
}

SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'i': 'ᵢ', 'n': 'ₙ'
}

GREEK_LETTERS = {
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
    r'\epsilon': 'ε', r'\varepsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η',
    r'\theta': 'θ', r'\vartheta': 'ϑ', r'\iota': 'ι', r'\kappa': 'κ',
    r'\lambda': 'λ', r'\mu': 'μ', r'\nu': 'ν', r'\xi': 'ξ',
    r'\pi': 'π', r'\rho': 'ρ', r'\sigma': 'σ', r'\tau': 'τ',
    r'\upsilon': 'υ', r'\phi': 'φ', r'\varphi': 'φ', r'\chi': 'χ',
    r'\psi': 'ψ', r'\omega': 'ω',
}

MATH_SYMBOLS = {
    r'\pm': '±', r'\mp': '∓', r'\times': '×', r'\div': '÷',
    r'\cdot': '·', r'\leq': '≤', r'\le': '≤', r'\geq': '≥', r'\ge': '≥',
    r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\equiv': '≡',
    r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇',
    r'\forall': '∀', r'\exists': '∃', r'\in': '∈', r'\notin': '∉',
    r'\subset': '⊂', r'\supset': '⊃', r'\cup': '∪', r'\cap': '∩',
    r'\emptyset': '∅', r'\sum': '∑', r'\prod': '∏',
    r'\int': '∫', r'\oint': '∮',
    r'\rightarrow': '→', r'\to': '→', r'\leftarrow': '←',
    r'\uparrow': '↑', r'\downarrow': '↓', r'\leftrightarrow': '↔',
    r'\degree': '°', r'\circ': '°', r'\bullet': '•',
    r'\ldots': '...', r'\cdots': '...', r'\dots': '...'
}


def to_superscript(text: str) -> str:
    result = ""
    for char in text:
        if char in SUPERSCRIPT_MAP:
            result += SUPERSCRIPT_MAP[char]
        else:
            result += char
    return result


def to_subscript(text: str) -> str:
    result = ""
    for char in text:
        if char in SUBSCRIPT_MAP:
            result += SUBSCRIPT_MAP[char]
        else:
            result += char
    return result


def format_latex_to_unicode(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    text = re.sub(r'^#{1,3}\s*(.+)$', r'📌 \1', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*]{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    text = re.sub(r'\$\$(.+?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$', r'\1', text)
    text = re.sub(r'\\left([(\[{|])', r'\1', text)
    text = re.sub(r'\\right([)\]}|])', r'\1', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    
    def replace_frac(match):
        num = match.group(1).strip()
        den = match.group(2).strip()
        num = format_latex_to_unicode(num)
        den = format_latex_to_unicode(den)
        if re.match(r'^[a-zA-Z0-9α-ωΑ-Ω]+$', num) and re.match(r'^[a-zA-Z0-9α-ωΑ-Ω]+$', den):
            return f"{num}/{den}"
        return f"({num})/({den})"
    
    for _ in range(5):
        new_text = re.sub(r'\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', replace_frac, text)
        if new_text == text:
            break
        text = new_text
    
    for _ in range(3):
        new_text = re.sub(r'\\sqrt\[([^\]]+)\]\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', 
                         lambda m: f"{to_superscript(m.group(1))}√({format_latex_to_unicode(m.group(2))})", text)
        new_text = re.sub(r'\\sqrt\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', 
                         lambda m: f"√({format_latex_to_unicode(m.group(1))})", new_text)
        if new_text == text:
            break
        text = new_text
    
    def replace_superscript_braces(match):
        return match.group(1) + to_superscript(match.group(2))
    
    text = re.sub(r'(\([^)]+\))\^\{([^}]+)\}', replace_superscript_braces, text)
    text = re.sub(r'([a-zA-Z0-9α-ωΑ-Ω]+)\^\{([^}]+)\}', replace_superscript_braces, text)
    text = re.sub(r'([a-zA-Z0-9α-ωΑ-Ω]+)\^([0-9a-zA-Z])', 
                 lambda m: m.group(1) + to_superscript(m.group(2)), text)
    text = re.sub(r'(\([^)]+\))\^([0-9a-zA-Z])', 
                 lambda m: m.group(1) + to_superscript(m.group(2)), text)
    
    def replace_subscript_braces(match):
        return match.group(1) + to_subscript(match.group(2))
    
    text = re.sub(r'([a-zA-Zα-ωΑ-Ω]+)_\{([^}]+)\}', replace_subscript_braces, text)
    text = re.sub(r'([a-zA-Zα-ωΑ-Ω]+)_([0-9a-zA-Z])', 
                 lambda m: m.group(1) + to_subscript(m.group(2)), text)
    
    for latex in sorted(GREEK_LETTERS.keys(), key=len, reverse=True):
        text = text.replace(latex, GREEK_LETTERS[latex])
    
    for latex in sorted(MATH_SYMBOLS.keys(), key=len, reverse=True):
        text = text.replace(latex, MATH_SYMBOLS[latex])
    
    text = re.sub(r'\\(?![nrt])', '', text)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


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
    def process_message(message: str, feature_id: str = "general", history: list = None) -> str:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🤖 Запрос к GigaChat (режим: {feature_id}, история: {len(history) if history else 0})")
                token = _get_token()
                system_prompt = PROMPTS.get(feature_id, PROMPTS["general"])
                
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
