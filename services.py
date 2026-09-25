import requests
import re
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Tuple, Optional
import urllib3
import time
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = os.environ.get("GIGACHAT_CLIENT_ID", "01a0bafa-206f-7e07-a2e7-df9e0acea285")
CLIENT_SECRET = os.environ.get("GIGACHAT_CLIENT_SECRET", "93e085d7-803b-4fe2-b1da-468aff78a450")

_token_cache = {"token": None, "expires_at": 0}

FORMATTING_RULES = """

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА ФОРМАТИРОВАНИЯ:
- НЕ используй LaTeX ($...$, $$...$$, \\frac, \\sqrt, \\alpha)
- НЕ используй Markdown (**жирный**, ### заголовки, --- разделители)
- Для степеней пиши: x², x³, 10⁸⁰ (Unicode)
- Для индексов пиши: x₁, a₂ (Unicode)
- Для дробей пиши: a/b или (a)/(b)
- Для списков: цифры "1.", "2." или символы "•", "►"
- Для выделения: эмодзи (📌, ✨, ⚡)
"""

LANGUAGE_RULES = """

ЯЗЫКОВОЕ ПОВЕДЕНИЕ:
- Ты понимаешь ВСЕ языки мира
- ВСЕГДА отвечай на том языке, на котором пишет ученик
- Помогай с изучением иностранных языков: перевод, грамматика, практика
"""

PROMPTS = {
    "planner": f"""Ты — умный планировщик подготовки к экзаменам. 
ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "homework": f"""Ты — ИИ-наставник, помогающий с домашкой методом Сократа. 
ВАЖНО: НИКОГДА не давай готовый ответ. Задавай наводящие вопросы.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "explain": f"""Ты — учитель, объясняющий сложные темы простым языком.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "tests": f"""Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "motivation": f"""Ты — дружелюбный мотиватор для школьников.
{LANGUAGE_RULES}""",

    "videos": f"""Ты — помощник по поиску видеоуроков.
Используй ТОЛЬКО эти форматы:
- https://rutube.ru/search/?q=ТЕМА
- https://vk.com/video?q=ТЕМА
- https://www.youtube.com/results?search_query=ТЕМА
{LANGUAGE_RULES}""",

    "journal": f"""Ты — умный помощник по анализу школьных оценок.
Ты умеешь: анализировать оценки, считать средний балл, давать рекомендации.
ВАЖНО: Используй данные об оценках из контекста разговора.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "offline": f"""Ты — помощник по оффлайн-обучению.
Используй ТОЛЬКО эти сайты:
- https://foxford.ru
- https://ege.sdamgia.ru
- https://oge.sdamgia.ru
- https://uchi.ru
{LANGUAGE_RULES}""",

    "context": f"""Ты — дружелюбный ИИ-наставник.
КРИТИЧЕСКИ ВАЖНО: Ученик задаёт вопрос о предыдущем сообщении. Прочитай историю.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "languages": f"""Ты — эксперт по иностранным языкам.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",

    "general": f"""Ты — дружелюбный ИИ-наставник для школьников.
ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником.
{FORMATTING_RULES}
{LANGUAGE_RULES}""",
}

MODE_KEYWORDS = {
    "planner": ["план", "расписан", "подготов", "экзамен", "огэ", "егэ", "контрольн", "сколько времени"],
    "homework": ["домашк", "дз", "задач", "упражнен", "решить", "уравнен"],
    "explain": ["объясни", "что такое", "как работает", "расскажи про"],
    "tests": ["тест", "проверь", "викторин", "квиз"],
    "motivation": ["устал", "не хочу", "лень", "мотивац", "скучно", "тяжело"],
    "videos": ["видео", "урок", "посмотреть", "ролик", "ютуб", "ссылк"],
    "journal": ["оценк", "журнал", "мэш", "дневник", "четверт", "полугод", "средний балл", "успеваемост"],
    "offline": ["оффлайн", "скачать", "без интернета", "материал", "сайт", "ресурс"],
    "context": ["почему", "зачем", "что именно", "знаешь", "понимаешь", "уточни"],
    "languages": ["перевод", "переведи", "translate", "английский", "немецкий", "французский", "грамматик"],
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
    'N': 'Т', 'M': 'Ь', '<': 'Б', '>': 'Ю', '?': ',', '~': 'Ё'
}

RU_TO_EN = {v: k for k, v in EN_TO_RU.items()}

ENGLISH_COMMON_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'hello', 'hi', 'hey', 'thanks', 'please', 'sorry', 'yes', 'no', 'ok',
    'how', 'are', 'you', 'what', 'where', 'when', 'why', 'which',
    'am', 'is', 'was', 'were', 'been', 'has', 'had',
    'does', 'did', 'will', 'would', 'should', 'could',
    'math', 'physics', 'chemistry', 'biology', 'history',
    'english', 'german', 'french', 'russian',
    'translate', 'grammar', 'word', 'help', 'student', 'school',
    'today', 'tomorrow', 'week', 'month', 'year',
    'big', 'small', 'good', 'bad', 'nice',
    'love', 'like', 'want', 'need', 'go', 'come', 'see', 'think', 'know'
}

RUSSIAN_COMMON_WORDS = {
    'и', 'в', 'не', 'на', 'я', 'быть', 'с', 'он', 'а', 'это',
    'как', 'то', 'что', 'этот', 'по', 'но', 'они', 'к', 'у', 'ты',
    'из', 'мы', 'за', 'вы', 'так', 'же', 'от', 'о', 'весь', 'при',
    'она', 'для', 'один', 'тот', 'когда', 'или', 'нет',
    'привет', 'спасибо', 'пожалуйста', 'хорошо', 'плохо',
    'математика', 'физика', 'химия', 'биология', 'история',
    'русский', 'английский', 'школа', 'учитель', 'класс', 'урок'
}


def count_language_matches(text: str, word_set: set) -> int:
    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ]+', text.lower())
    return sum(1 for word in words if word in word_set)


def detect_real_language(text: str) -> Tuple[str, str]:
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
# КОНВЕРТАЦИЯ LATEX В UNICODE
# ============================================

SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', 'n': 'ⁿ'
}

SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    'i': 'ᵢ', 'n': 'ₙ'
}

GREEK_LETTERS = {
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
    r'\epsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ',
    r'\iota': 'ι', r'\kappa': 'κ', r'\lambda': 'λ', r'\mu': 'μ',
    r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π', r'\rho': 'ρ',
    r'\sigma': 'σ', r'\tau': 'τ', r'\phi': 'φ', r'\omega': 'ω'
}

MATH_SYMBOLS = {
    r'\pm': '±', r'\times': '×', r'\div': '÷', r'\cdot': '·',
    r'\leq': '≤', r'\le': '≤', r'\geq': '≥', r'\ge': '≥',
    r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\infty': '∞',
    r'\rightarrow': '→', r'\to': '→', r'\sqrt': '√',
    r'\degree': '°', r'\circ': '°'
}


def to_superscript(text: str) -> str:
    result = ""
    for char in text:
        result += SUPERSCRIPT_MAP.get(char, char)
    return result


def to_subscript(text: str) -> str:
    result = ""
    for char in text:
        result += SUBSCRIPT_MAP.get(char, char)
    return result


def format_latex_to_unicode(text: str) -> str:
    """Конвертирует LaTeX и Markdown в читаемый Unicode-формат"""
    
    # Убираем Markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    text = re.sub(r'^#{1,3}\s*(.+)$', r'📌 \1', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*]{3,}$', '', text, flags=re.MULTILINE)
    
    # Убираем $...$ и $$...$$
    text = re.sub(r'\$\$(.+?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$', r'\1', text)
    
    # \frac{a}{b} → (a)/(b)
    for _ in range(5):
        new_text = re.sub(
            r'\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
            lambda m: f"({m.group(1).strip()})/({m.group(2).strip()})",
            text
        )
        if new_text == text:
            break
        text = new_text
    
    # \sqrt{...} → √(...)
    for _ in range(3):
        new_text = re.sub(r'\\sqrt\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', 
                         lambda m: f"√({m.group(1)})", text)
        if new_text == text:
            break
        text = new_text
    
    # Степени: (x+1)^{2} → (x+1)², x^2 → x²
    text = re.sub(r'(\([^)]+\))\^\{([^}]+)\}', 
                 lambda m: m.group(1) + to_superscript(m.group(2)), text)
    text = re.sub(r'([a-zA-Z0-9]+)\^\{([^}]+)\}', 
                 lambda m: m.group(1) + to_superscript(m.group(2)), text)
    text = re.sub(r'([a-zA-Z0-9]+)\^([0-9a-zA-Z])', 
                 lambda m: m.group(1) + to_superscript(m.group(2)), text)
    
    # Индексы: x_{i} → xᵢ
    text = re.sub(r'([a-zA-Z]+)_\{([^}]+)\}', 
                 lambda m: m.group(1) + to_subscript(m.group(2)), text)
    text = re.sub(r'([a-zA-Z]+)_([0-9a-zA-Z])', 
                 lambda m: m.group(1) + to_subscript(m.group(2)), text)
    
    # Греческие буквы и символы
    for latex in sorted(GREEK_LETTERS.keys(), key=len, reverse=True):
        text = text.replace(latex, GREEK_LETTERS[latex])
    
    for latex in sorted(MATH_SYMBOLS.keys(), key=len, reverse=True):
        text = text.replace(latex, MATH_SYMBOLS[latex])
    
    # Убираем оставшиеся обратные слеши
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
        context_keywords = ["почему", "зачем", "что", "как", "когда", "где", "знаешь", "понимаешь"]
        if any(kw in text_lower for kw in context_keywords):
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


# ============================================
# АНАЛИЗАТОР ОЦЕНОК
# ============================================

class GradeAnalyzer:
    SUBJECT_ALIASES = {
        'матем': 'Математика', 'алгебр': 'Математика', 'геометр': 'Математика',
        'русск': 'Русский язык', 'литер': 'Литература',
        'англ': 'Английский язык', 'ингл': 'Английский язык',
        'нем': 'Немецкий язык', 'физ': 'Физика', 'хим': 'Химия',
        'биолог': 'Биология', 'био': 'Биология', 'истор': 'История',
        'географ': 'География', 'гео': 'География',
        'информ': 'Информатика', 'инфа': 'Информатика',
        'общество': 'Обществознание', 'физр': 'Физкультура',
        'музык': 'Музыка', 'изо': 'ИЗО', 'изобраз': 'ИЗО',
        'технолог': 'Технология', 'труд': 'Технология',
        'экологи': 'Экология'
    }
    
    @staticmethod
    def normalize_subject(subject: str) -> str:
        subject_lower = subject.lower().strip()
        for alias, canonical in GradeAnalyzer.SUBJECT_ALIASES.items():
            if alias in subject_lower:
                return canonical
        return subject.strip().capitalize()
    
    @staticmethod
    def parse_grades(text: str) -> Tuple[Optional[str], List[int]]:
        text_lower = text.lower()
        grades = re.findall(r'\b([1-5])\b', text)
        grades = [int(g) for g in grades if 1 <= int(g) <= 5]
        
        if not grades:
            return None, []
        
        subject = None
        for alias, canonical in GradeAnalyzer.SUBJECT_ALIASES.items():
            if alias in text_lower:
                subject = canonical
                break
        
        if not subject:
            match = re.search(r'([а-яёa-z]+)[\s:]+[1-5]', text_lower)
            if match:
                subject = GradeAnalyzer.normalize_subject(match.group(1))
        
        return subject, grades
    
    @staticmethod
    def add_grades(user_grades: dict, subject: str, new_grades: List[int]) -> str:
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
            
            emoji = "🌟" if avg >= 4.5 else "✅" if avg >= 4.0 else "👌" if avg >= 3.5 else "⚠️"
            grades_str = " ".join(str(g) for g in grades)
            msg += f"{emoji} {subject}\n"
            msg += f"   Оценки: {grades_str}\n"
            msg += f"   Средний: {avg:.2f}\n\n"
        
        if total_count > 0:
            overall_avg = total_sum / total_count
            msg += "━" * 25 + "\n"
            msg += f"📈 ОБЩИЙ СРЕДНИЙ БАЛЛ: {overall_avg:.2f}\n\n"
            
            subject_avgs = {s: sum(g)/len(g) for s, g in user_grades.items() if g}
            if subject_avgs:
                best = max(subject_avgs, key=subject_avgs.get)
                worst = min(subject_avgs, key=subject_avgs.get)
                msg += f"💪 Лучший предмет: {best} ({subject_avgs[best]:.2f})\n"
                msg += f"📚 Нужно подтянуть: {worst} ({subject_avgs[worst]:.2f})\n"
        
        return msg
    
    @staticmethod
    def get_analysis(user_grades: dict) -> str:
        if not user_grades:
            return "📭 Нет данных для анализа."
        
        msg = "🎓 АНАЛИЗ УСПЕВАЕМОСТИ\n"
        msg += "━" * 25 + "\n\n"
        
        subject_avgs = {}
        for subject, grades in user_grades.items():
            if grades:
                subject_avgs[subject] = sum(grades) / len(grades)
        
        if not subject_avgs:
            return "📭 Нет данных для анализа."
        
        overall_avg = sum(subject_avgs.values()) / len(subject_avgs)
        msg += f"📊 Общий средний балл: {overall_avg:.2f}\n\n"
        
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
            msg += "2. Попроси помощи у учителя\n"
            msg += "3. Напиши 'план подготовки по [предмет]' — составлю план!\n"
        elif average:
            msg += f"1. Подтяни: {', '.join(average)} до 4.5+\n"
            msg += "2. Решай больше задач и упражнений\n"
        else:
            msg += "1. Так держать! 🎉\n"
            msg += "2. Пробуй задачи повышенной сложности"
        
        return msg
    
    @staticmethod
    def delete_subject(user_grades: dict, subject_query: str) -> str:
        subject_query = GradeAnalyzer.normalize_subject(subject_query)
        
        for subject in list(user_grades.keys()):
            if subject.lower() == subject_query.lower():
                del user_grades[subject]
                return f"🗑️ Предмет '{subject}' удалён из дневника."
        
        return f"❓ Предмет '{subject_query}' не найден в твоём дневнике."


# ============================================
# ОСНОВНОЙ СЕРВИС ИИ
# ============================================

class AIService:
    @staticmethod
    def process_message(message: str, feature_id: str = "general", history: list = None, 
                       grades_context: str = "") -> str:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🤖 Запрос к GigaChat (режим: {feature_id})")
                token = _get_token()
                system_prompt = PROMPTS.get(feature_id, PROMPTS["general"])
                
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
                        # КРИТИЧЕСКИ ВАЖНО: конвертируем LaTeX в Unicode
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
