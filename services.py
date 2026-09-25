import requests
import re
from requests.auth import HTTPBasicAuth
from typing import Dict
import urllib3
import time
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = os.environ.get("GIGACHAT_CLIENT_ID", "01a0bafa-206f-7e07-a2e7-df9e0acea285")
CLIENT_SECRET = os.environ.get("GIGACHAT_CLIENT_SECRET", "93e085d7-803b-4fe2-b1da-468aff78a450")

_token_cache = {"token": None, "expires_at": 0}

PROMPTS = {
    "planner": """Ты — умный планировщик подготовки к экзаменам. 

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.

ФОРМАТИРОВАНИЕ:
- Используй Unicode-символы вместо LaTeX где возможно: α, β, γ, π, √, ≤, ≥, ≠
- Для степеней пиши просто: 10^80, x^2
- Для индексов пиши: x_i, a_1
- НЕ используй $...$ или $$...$$ для формул

Отвечай структурированно, с эмодзи. На русском.""",

    "homework": """Ты — ИИ-наставник, помогающий с домашкой методом Сократа. 

ВАЖНО: 
- НИКОГДА не давай готовый ответ
- Задавай наводящие вопросы
- Ты помнишь ВЕСЬ разговор с учеником
- Если ученик спрашивает "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте

ФОРМАТИРОВАНИЕ:
- Используй Unicode-символы вместо LaTeX где возможно: α, β, γ, π, √, ≤, ≥, ≠
- Для степеней пиши просто: 10^80, x^2
- Для индексов пиши: x_i, a_1
- НЕ используй $...$ или $$...$$ для формул

На русском.""",

    "explain": """Ты — учитель, объясняющий сложные темы простым языком.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.

ФОРМАТИРОВАНИЕ:
- Используй Unicode-символы вместо LaTeX где возможно: α, β, γ, π, √, ≤, ≥, ≠
- Для степеней пиши просто: 10^80, x^2
- Для индексов пиши: x_i, a_1
- НЕ используй $...$ или $$...$$ для формул

На русском.""",

    "tests": """Ты — генератор тестов. Создай тест из 5 вопросов с вариантами ответов. В конце напиши правильные ответы.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

ФОРМАТИРОВАНИЕ:
- Используй Unicode-символы вместо LaTeX где возможно: α, β, γ, π, √, ≤, ≥, ≠
- Для степеней пиши просто: 10^80, x^2
- Для индексов пиши: x_i, a_1
- НЕ используй $...$ или $$...$$ для формул

На русском.""",

    "motivation": """Ты — дружелюбный мотиватор для школьников.

ВАЖНО: 
- Ты помнишь ВЕСЬ разговор с учеником
- Всегда учитывай контекст предыдущих сообщений
- Если ученик хвалит тебя ("ты молодец", "спасибо") и потом спрашивает "знаешь почему?" — отвечай в контексте его похвалы
- Задавай уточняющие вопросы, если контекст неясен

На русском.""",

    "videos": """Ты — помощник по поиску видеоуроков. Дай ссылки на поиск видео по теме ученика.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

Используй ТОЛЬКО эти форматы поисковых ссылок:
- Поиск на RuTube: https://rutube.ru/search/?q=ТЕМА
- Поиск на VK Видео: https://vk.com/video?q=ТЕМА
- Поиск на YouTube: https://www.youtube.com/results?search_query=ТЕМА

Замени ТЕМА на предмет/тему ученика. На русском языке.""",

    "journal": """Ты — помощник по интеграции с МЭШ. Анализируй оценки.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

На русском.""",

    "offline": """Ты — помощник по оффлайн-обучению. Дай ссылки на проверенные образовательные ресурсы.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Учитывай контекст предыдущих сообщений.

Используй ТОЛЬКО эти проверенные сайты:
- Фоксфорд: https://foxford.ru
- Решу ЕГЭ: https://ege.sdamgia.ru
- Решу ОГЭ: https://oge.sdamgia.ru
- Учи.ру: https://uchi.ru
- Библиотека МЭШ: https://uchebnik.mos.ru
- Интернетурок: https://interneturok.ru

На русском языке.""",

    "context": """Ты — дружелюбный ИИ-наставник для школьников.

КРИТИЧЕСКИ ВАЖНО: Ученик задаёт вопрос, который относится к предыдущему сообщению в разговоре.
Внимательно прочитай историю разговора и пойми, о чём именно спрашивает ученик.

Примеры:
- Если ученик сказал "Ты молодец!" и потом спрашивает "Знаешь почему?" — он спрашивает, почему ты молодец
- Если ученик сказал "Мне не нравится математика" и потом спрашивает "Почему?" — он спрашивает, почему ему не нравится математика
- Если ученик задал вопрос и потом спрашивает "Что именно?" — он просит уточнить

ФОРМАТИРОВАНИЕ:
- Используй Unicode-символы вместо LaTeX где возможно: α, β, γ, π, √, ≤, ≥, ≠
- Для степеней пиши просто: 10^80, x^2
- Для индексов пиши: x_i, a_1
- НЕ используй $...$ или $$...$$ для формул

Отвечай в контексте предыдущего разговора. Задавай уточняющие вопросы, если контекст неясен.

На русском.""",

    "general": """Ты — дружелюбный ИИ-наставник для школьников.

ВАЖНО: Ты помнишь ВЕСЬ разговор с учеником. Всегда учитывай контекст предыдущих сообщений.
Если ученик задаёт короткие вопросы типа "почему?", "зачем?", "что именно?" — смотри на предыдущее сообщение и отвечай в контексте.

ФОРМАТИРОВАНИЕ:
- Используй Unicode-символы вместо LaTeX где возможно: α, β, γ, π, √, ≤, ≥, ≠
- Для степеней пиши просто: 10^80, x^2
- Для индексов пиши: x_i, a_1
- НЕ используй $...$ или $$...$$ для формул

Помогай с учёбой. На русском."""
}

MODE_KEYWORDS = {
    "planner": ["план", "расписан", "подготов", "экзамен", "огэ", "егэ", "контрольн", "сколько времени"],
    "homework": ["домашк", "дз", "задач", "упражнен", "решить"],
    "explain": ["объясни", "что такое", "как работает", "расскажи про", "почему"],
    "tests": ["тест", "проверь", "викторин", "квиз"],
    "motivation": ["устал", "не хочу", "лень", "мотивац", "скучно", "тяжело"],
    "videos": ["видео", "урок", "посмотреть", "ролик", "ютуб", "youtube", "rutube", "ссылк"],
    "journal": ["оценк", "журнал", "мэш", "четверт", "полугод"],
    "offline": ["оффлайн", "скачать", "без интернета", "материал", "сайт", "ресурс", "учебник"],
    "context": ["почему", "зачем", "что именно", "знаешь", "понимаешь", "объясни", "уточни"],
}

# Маппинг для конвертации LaTeX в Unicode
SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'n': 'ⁿ', 'i': 'ⁱ'
}

SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ'
}

GREEK_LETTERS = {
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
    r'\epsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ',
    r'\iota': 'ι', r'\kappa': 'κ', r'\lambda': 'λ', r'\mu': 'μ',
    r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π', r'\rho': 'ρ',
    r'\sigma': 'σ', r'\tau': 'τ', r'\upsilon': 'υ', r'\phi': 'φ',
    r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
    r'\Alpha': 'Α', r'\Beta': 'Β', r'\Gamma': 'Γ', r'\Delta': 'Δ',
    r'\Epsilon': 'Ε', r'\Zeta': 'Ζ', r'\Eta': 'Η', r'\Theta': 'Θ',
    r'\Iota': 'Ι', r'\Kappa': 'Κ', r'\Lambda': 'Λ', r'\Mu': 'Μ',
    r'\Nu': 'Ν', r'\Xi': 'Ξ', r'\Pi': 'Π', r'\Rho': 'Ρ',
    r'\Sigma': 'Σ', r'\Tau': 'Τ', r'\Upsilon': 'Υ', r'\Phi': 'Φ',
    r'\Chi': 'Χ', r'\Psi': 'Ψ', r'\Omega': 'Ω'
}

MATH_SYMBOLS = {
    r'\pm': '±', r'\mp': '∓', r'\times': '×', r'\div': '÷',
    r'\cdot': '·', r'\leq': '≤', r'\geq': '≥', r'\neq': '≠',
    r'\approx': '≈', r'\equiv': '≡', r'\infty': '∞', r'\partial': '∂',
    r'\nabla': '∇', r'\forall': '∀', r'\exists': '∃', r'\in': '∈',
    r'\notin': '∉', r'\subset': '⊂', r'\supset': '⊃', r'\cup': '∪',
    r'\cap': '∩', r'\emptyset': '∅', r'\sqrt': '√', r'\sum': '∑',
    r'\prod': '∏', r'\int': '∫', r'\oint': '∮', r'\rightarrow': '→',
    r'\leftarrow': '←', r'\uparrow': '↑', r'\downarrow': '↓',
    r'\leftrightarrow': '↔'
}


def to_superscript(text: str) -> str:
    """Конвертирует текст в надстрочный формат"""
    result = ""
    for char in text:
        if char in SUPERSCRIPT_MAP:
            result += SUPERSCRIPT_MAP[char]
        else:
            result += char
    return result


def to_subscript(text: str) -> str:
    """Конвертирует текст в подстрочный формат"""
    result = ""
    for char in text:
        if char in SUBSCRIPT_MAP:
            result += SUBSCRIPT_MAP[char]
        else:
            result += char
    return result


def format_latex_to_unicode(text: str) -> str:
    """Конвертирует LaTeX-формулы в читаемый Unicode-формат"""
    
    # Удаляем $...$ и $$...$$
    text = re.sub(r'\$\$(.+?)\$\$', r'\1', text)
    text = re.sub(r'\$(.+?)\$', r'\1', text)
    
    # Конвертируем степени: 10^{80} → 10⁸⁰, x^2 → x²
    def replace_superscript(match):
        base = match.group(1)
        exp = match.group(2)
        return base + to_superscript(exp)
    
    text = re.sub(r'(\w+)\^{([^}]+)}', replace_superscript, text)
    text = re.sub(r'(\w+)\^(\w)', lambda m: m.group(1) + to_superscript(m.group(2)), text)
    
    # Конвертируем индексы: x_{i} → xᵢ, a_1 → a₁
    def replace_subscript(match):
        base = match.group(1)
        sub = match.group(2)
        return base + to_subscript(sub)
    
    text = re.sub(r'(\w+)_{([^}]+)}', replace_subscript, text)
    text = re.sub(r'(\w+)_(\w)', lambda m: m.group(1) + to_subscript(m.group(2)), text)
    
    # Конвертируем греческие буквы
    for latex, unicode in GREEK_LETTERS.items():
        text = text.replace(latex, unicode)
    
    # Конвертируем математические символы
    for latex, unicode in MATH_SYMBOLS.items():
        text = text.replace(latex, unicode)
    
    # Убираем лишние пробелы вокруг операторов
    text = re.sub(r'\s*([+\-×÷=<>≤≥≠≈≡])\s*', r' \1 ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


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
    """Определяет режим работы бота"""
    text_lower = text.lower().strip()
    
    # Если сообщение очень короткое и есть история — скорее всего это контекстный вопрос
    if has_history and len(text_lower) < 30:
        context_keywords = ["почему", "зачем", "что", "как", "когда", "где", "знаешь", "понимаешь"]
        if any(kw in text_lower for kw in context_keywords):
            print(f"🎯 Определён контекстный вопрос (короткое сообщение с историей)")
            return "context"
    
    scores = {}
    for mode_id, keywords in MODE_KEYWORDS.items():
        if mode_id == "context":  # Пропускаем context в обычном поиске
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[mode_id] = score
    
    if scores:
        best_mode = max(scores, key=scores.get)
        print(f"🎯 Режим определён по ключевым словам: {best_mode}")
        return best_mode
    
    return "general"


class AIService:
    @staticmethod
    def process_message(message: str, feature_id: str = "general", history: list = None) -> str:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🤖 Запрос к GigaChat (режим: {feature_id}, история: {len(history) if history else 0} сообщ.)")
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
                        # Конвертируем LaTeX в Unicode
                        content = format_latex_to_unicode(content)
                        print(f"✅ Ответ получен ({len(content)} символов)")
                        return content
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "Извини, не удалось получить ответ от ИИ."
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"⏱️ Таймаут (попытка {attempt+1}), пробуем ещё раз...")
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
