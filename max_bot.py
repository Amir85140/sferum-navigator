import os
import asyncio
import logging
import json
import time
import base64
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List
import requests
import urllib3
from maxapi import Bot, Dispatcher

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'f9LHodD0cOLAk1Ry-yn7J-4F5oi3mZW9vlXyawwC4SxvVwTZ3DILUsVm6QJhFo2e3ReJ-0ucg1NORcMQ_FNI')
GIGA_ID = os.environ.get('GIGA_ID', '01a0bafa-206f-7e07-a2e7-df9e0acea285')
GIGA_SECRET = os.environ.get('GIGA_SECRET', '93e085d7-803b-4fe2-b1da-468aff78a450')
CODESPACE_NAME = os.environ.get('CODESPACE_NAME', 'automatic-system-p7gg76p4wqqwf99rj')
PROXY_BASE = f"https://{CODESPACE_NAME}-8000.app.github.dev"
MINI_APP_URL = "https://amir85140.github.io/sferum-navigator/"
CHANNEL = 'main'
USER_DATA_FILE = Path('user_data.json')

# Запрет LaTeX/Markdown для MAX (там формулы не рендерятся)
NO_LATEX = (' СТРОГО ЗАПРЕЩЕНО использовать LaTeX (знаки $, $$, \\frac, \\sqrt и любые бэкслэши) '
            'и Markdown (**, #, `). Все формулы пиши ПРОСТЫМ текстом в одну строку, '
            'например: a = F / m, S = v * t, x^2.')

user_data: Dict[int, Dict[str, Any]] = {}

def load_user_data():
    global user_data
    if USER_DATA_FILE.exists():
        try:
            raw = json.loads(USER_DATA_FILE.read_text(encoding='utf-8'))
            user_data = {int(k): v for k, v in raw.items()}
        except Exception as e:
            logger.error(f"load user_data: {e}")
            user_data = {}

def save_user_data():
    try:
        USER_DATA_FILE.write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.error(f"save user_data: {e}")

load_user_data()

def now_ms():
    return int(time.time() * 1000)

# ===== ОБЩИЙ ЧАТ-КАНАЛ НА СЕРВЕРЕ =====
def load_chat_from_server(channel=CHANNEL):
    try:
        r = requests.get(f"{PROXY_BASE}/chat_history?user_id={channel}", timeout=5, verify=False)
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.error(f"load chat: {e}")
    return []

def save_chat_to_server(history, channel=CHANNEL):
    try:
        requests.post(f"{PROXY_BASE}/chat_history?user_id={channel}",
                      json=history[-50:], timeout=5, verify=False)
    except Exception as e:
        logger.error(f"save chat: {e}")

# ===== ПРЕОБРАЗОВАНИЕ LATEX -> ОБЫЧНЫЙ ТЕКСТ =====
def latex_to_plain(t):
    if not t:
        return t
    s = t
    for _ in range(3):
        s = re.sub(r'\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'(\1) / (\2)', s)
    s = s.replace('\\cdot', '*').replace('\\times', '*').replace('\\div', '/')
    s = s.replace('\\left', '').replace('\\right', '')
    s = re.sub(r'\\sqrt\s*\{([^{}]*)\}', r'sqrt(\1)', s)
    s = s.replace('\\pi', 'пи').replace('\\infty', 'бесконечность')
    s = s.replace('\\pm', '+-').replace('\\le', '<=').replace('\\ge', '>=').replace('\\ne', '!=')
    s = s.replace('\\approx', '~').replace('\\degree', '°')
    s = re.sub(r'_\{([^{}]*)\}', r'\1', s)
    s = re.sub(r'\^\{([^{}]*)\}', r'^\1', s)
    s = re.sub(r'_(\w)', r'\1', s)
    s = re.sub(r'\\([a-zA-Z]+)', r'\1', s)
    s = s.replace('$$', ' ').replace('$', '')
    s = s.replace('**', '').replace('`', '')
    s = re.sub(r'[ \t]+\n', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

# ===== GIGACHAT =====
giga_token = None
giga_exp = 0

def get_giga_token():
    global giga_token, giga_exp
    if giga_token and time.time() < giga_exp:
        return giga_token
    try:
        auth_b64 = base64.b64encode(f"{GIGA_ID}:{GIGA_SECRET}".encode()).decode()
        r = requests.post(
            'https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
            headers={'Authorization': f'Basic {auth_b64}',
                     'Content-Type': 'application/x-www-form-urlencoded',
                     'RqUID': str(uuid.uuid4())},
            data={'scope': 'GIGACHAT_API_PERS'},
            verify=False, timeout=30)
        if r.ok:
            giga_token = r.json()['access_token']
            giga_exp = time.time() + 1700
            return giga_token
    except Exception as e:
        logger.error(f"token: {e}")
    return None

def ask_gigachat(prompt, system_prompt=None, max_tokens=800, history=None):
    token = get_giga_token()
    if not token:
        return "❌ Не удалось подключиться к GigaChat"
    try:
        messages = [{'role': 'system',
                     'content': (system_prompt or
                                 'Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно.') + NO_LATEX}]
        if history:
            messages.extend(history[-16:])
        messages.append({'role': 'user', 'content': prompt})
        r = requests.post(
            'https://gigachat.devices.sberbank.ru/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'model': 'GigaChat:latest', 'messages': messages,
                  'max_tokens': max_tokens, 'temperature': 0.7},
            verify=False, timeout=60)
        if r.ok:
            _t = r.json()['choices'][0]['message']['content']
            _t = latex_to_plain(_t)
            return _t
    except Exception as e:
        logger.error(f"giga: {e}")
    return "❌ Ошибка при обращении к GigaChat"

# ===== БОТ =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== КЛАВИАТУРА (защитное построение; если классы недоступны — кнопки отключаются) =====
MENU_ROWS = [
    [("✅ Тренажёр", "quiz"), ("🎥 Видео", "video")],
    [("💪 Мотивация", "motivation"), ("📅 План", "plan")],
    [("📚 Дневник", "grades"), ("🏠 Меню", "menu")],
]

def make_menu_keyboard():
    try:
        from maxapi.types import Keyboard, CallbackButton
        rows = [[CallbackButton(text=t, payload={"cmd": c}) for t, c in row] for row in MENU_ROWS]
        kb = Keyboard(rows)
        fn = getattr(kb, 'as_markup', None)
        return fn() if callable(fn) else kb
    except Exception as e:
        logger.error(f"kb1: {e}")
    try:
        from maxapi.types import Keyboard, Button
        rows = [[Button(text=t, payload={"cmd": c}) for t, c in row] for row in MENU_ROWS]
        kb = Keyboard(rows)
        fn = getattr(kb, 'as_markup', None)
        return fn() if callable(fn) else kb
    except Exception as e:
        logger.error(f"kb2: {e}")
    # dict не имеет model_dump -> reply() его проигнорирует, бот не упадёт
    return {
        "type": "inline_keyboard",
        "payload": {"buttons": [[{"type": "callback", "text": t, "payload": {"cmd": c}} for t, c in row] for row in MENU_ROWS]},
    }

# ===== ХЕЛПЕРЫ СОБЫТИЙ =====
def get_uid(event):
    for src in (getattr(event, 'from_user', None), getattr(event, 'user', None),
                getattr(getattr(event, 'message', None), 'sender', None)):
        if src is None:
            continue
        for attr in ('user_id', 'id'):
            v = getattr(src, attr, None)
            if v is not None:
                try:
                    return int(v)
                except Exception:
                    pass
    return 0

def get_chat_id(event):
    v = getattr(event, 'chat_id', None)
    if v is None:
        v = getattr(getattr(event, 'message', None), 'chat_id', None)
    return v

def get_text(event):
    m = getattr(event, 'message', None)
    if m is None:
        return ''
    for attr in ('body', 'text'):
        v = getattr(m, attr, None)
        if isinstance(v, str):
            return v.strip()
        if v is not None:
            t = getattr(v, 'text', None)
            if isinstance(t, str):
                return t.strip()
    return ''

async def reply(event, text, keyboard=None):
    atts = None
    if keyboard is not None and hasattr(keyboard, 'model_dump'):
        atts = [keyboard]
    cid = get_chat_id(event)
    uid = get_uid(event)
    variants = []
    if cid:
        variants.append({'chat_id': cid})
    if uid:
        variants.append({'user_id': uid})
    last_err = None
    for kw in variants:
        for with_att in ((True, False) if atts else (False,)):
            try:
                if with_att:
                    return await bot.send_message(text=text, attachments=atts, **kw)
                return await bot.send_message(text=text, **kw)
            except Exception as e:
                last_err = e
    m = getattr(event, 'message', None)
    fn = getattr(m, 'answer', None)
    if callable(fn):
        try:
            return await fn(text)
        except Exception as e:
            last_err = e
    if last_err:
        raise last_err
    raise Exception('send failed')

async def delete_msg(msg):
    if msg is None:
        return
    fn = getattr(msg, 'delete', None)
    if callable(fn):
        try:
            await fn()
            return
        except Exception:
            pass

def get_callback_cmd(event):
    for attr in ('payload', 'data'):
        v = getattr(event, attr, None)
        if isinstance(v, dict) and 'cmd' in v:
            return v['cmd']
        if isinstance(v, str):
            try:
                d = json.loads(v)
                if isinstance(d, dict) and 'cmd' in d:
                    return d['cmd']
            except Exception:
                pass
    cb = getattr(event, 'callback', None)
    if cb is not None:
        p = getattr(cb, 'payload', None)
        if isinstance(p, dict) and 'cmd' in p:
            return p['cmd']
    return None

# ===== РАЗДЕЛЫ =====
def norm(s):
    return re.sub(r'[.,!?;:"\'\s]', '', str(s).lower().replace('ё', 'е'))

def ensure(uid):
    if uid not in user_data:
        user_data[uid] = {'grades': {}, 'state': None}
    user_data[uid].setdefault('grades', {})
    user_data[uid].setdefault('state', None)
    return user_data[uid]

async def send_menu(event):
    await reply(event, "🏠 Меню — выбери раздел (или напиши словами):", keyboard=make_menu_keyboard())

async def act_menu(event, uid):
    ensure(uid)['state'] = None
    await send_menu(event)

async def act_quiz(event, uid):
    u = ensure(uid)
    u['state'] = {'mode': 'quiz_topic'}
    await reply(event, "✅ Тренажёр\nНапиши тему (например: дроби, столица России):", keyboard=make_menu_keyboard())

async def act_video(event, uid):
    u = ensure(uid)
    u['state'] = {'mode': 'video_topic'}
    await reply(event, "🎥 Видеоуроки\nНапиши тему — объясню и дам ссылки:", keyboard=make_menu_keyboard())

async def act_motivation(event, uid):
    ensure(uid)['state'] = None
    r = ask_gigachat('Школьник устал и переживает перед экзаменами. Поддержи 2-3 тёплыми предложениями как старший друг.',
                     'Ты — поддерживающий наставник.')
    await reply(event, f"💪 {r}", keyboard=make_menu_keyboard())

async def act_plan(event, uid):
    u = ensure(uid)
    plan = u.get('plan')
    if plan:
        lines = [f"{s.get('day','')}: {s.get('subject','')} — {s.get('topic','')}" for s in plan.get('schedule', [])]
        await reply(event, "📅 Твой план на неделю:\n" + "\n".join(lines), keyboard=make_menu_keyboard())
    else:
        u['state'] = {'mode': 'plan_wizard'}
        await reply(event, "📅 План\nНапиши одной строкой: класс и что сдаёшь\n(например: 9, ОГЭ математика):", keyboard=make_menu_keyboard())

async def act_grades(event, uid):
    ensure(uid)['state'] = None
    g = user_data[uid].get('grades', {})
    if not g:
        await reply(event, "📚 Дневник пуст.\nНапиши про оценки словами — сам запишу, например: «математика 5 4».", keyboard=make_menu_keyboard())
        return
    out, allg = [], []
    for s, arr in g.items():
        allg += arr
        out.append(f"{s}: {', '.join(map(str, arr))} (ср. {sum(arr)/len(arr):.2f})")
    avg = sum(allg) / len(allg) if allg else 0
    await reply(event, "📚 Твой дневник:\n" + "\n".join(out) + f"\n\nОбщий средний: {avg:.2f}", keyboard=make_menu_keyboard())

ACTIONS = {
    'menu': act_menu, 'quiz': act_quiz, 'video': act_video,
    'motivation': act_motivation, 'plan': act_plan, 'grades': act_grades,
}
TEXT_ALIASES = {
    'menu': ['меню', '🏠 меню'],
    'quiz': ['тренажёр', 'тренажер', 'тест', '✅ тренажёр'],
    'video': ['видео', '🎥 видео'],
    'motivation': ['мотивация', 'поддержи', '💪 мотивация'],
    'plan': ['план', '📅 план'],
    'grades': ['дневник', 'оценки мои', '📚 дневник'],
}

def detect_text_action(text):
    low = text.lower().strip()
    for cmd, aliases in TEXT_ALIASES.items():
        if low in aliases:
            return cmd
    return None

# ===== ОБРАБОТКА СОСТОЯНИЙ =====
async def handle_state(event, uid, text):
    u = ensure(uid)
    st = u.get('state')
    if not st:
        return False
    mode = st.get('mode')

    if mode == 'quiz_topic':
        q = ask_gigachat(
            f'Придумай ОДНО задание для школьника по теме «{text}». Без вариантов ответа.' + NO_LATEX +
            '\nФормат СТРОГО JSON: {"question":"...","answer":"...","hint":"..."}',
            'Верни только валидный JSON.' + NO_LATEX, 400)
        m = re.search(r'\{[\s\S]*\}', q)
        if not m:
            u['state'] = None
            await reply(event, "Не смог составить задание. Попробуй другую тему.", keyboard=make_menu_keyboard())
            return True
        try:
            task = json.loads(m.group())
        except Exception:
            u['state'] = None
            await reply(event, "Не смог составить задание. Попробуй другую тему.", keyboard=make_menu_keyboard())
            return True
        u['state'] = {'mode': 'quiz_answer', 'answer': task.get('answer', ''), 'topic': text}
        hint = task.get('hint')
        await reply(event, f"🎯 Задание:\n{task.get('question','')}\n\nНапиши свой ответ." + (f"\n💡 {hint}" if hint else ""))
        return True

    if mode == 'quiz_answer':
        correct = st.get('answer', '')
        ok = norm(text) == norm(correct) or (norm(correct) and norm(correct) in norm(text)) or (norm(text) and norm(text) in norm(correct))
        if not ok:
            chk = ask_gigachat(f'Вопрос был с ответом «{correct}». Ученик ответил «{text}». Верно ли по смыслу? Верни СТРОГО JSON: {{"correct": true|false}}', 'Верни только JSON.', 60)
            mm = re.search(r'(true|false)', chk.lower())
            ok = bool(mm and mm.group(1) == 'true')
        u['state'] = None
        if ok:
            await reply(event, f"✅ Верно! Отлично!\nПравильный ответ: {correct}", keyboard=make_menu_keyboard())
        else:
            await reply(event, f"❌ Неверно.\nПравильный ответ: {correct}", keyboard=make_menu_keyboard())
        return True

    if mode == 'video_topic':
        u['state'] = None
        expl = ask_gigachat(f'Кратко (2-3 предложения) объясни школьнику тему «{text}» с примером.', None, 400)
        t = requests.utils.quote(text)
        links = (f"▶ YouTube: https://www.youtube.com/results?search_query={t}\n"
                 f"▶ VK: https://vk.com/video?q={t}\n"
                 f"▶ RuTube: https://rutube.ru/search/?q={t}")
        await reply(event, f"🎓 {expl}\n\n📺 Смотри уроки:\n{links}", keyboard=make_menu_keyboard())
        return True

    if mode == 'plan_wizard':
        u['state'] = None
        m = re.search(r'(\d{1,2})', text)
        grade = m.group(1) if m else '9'
        resp = ask_gigachat(
            f'Ученик {grade} класса сдаёт: {text}. Составь расписание на неделю Пн-Вс: учебные дни чередуй с отдыхом, укажи конкретную тему каждого дня.' + NO_LATEX +
            '\nВерни СТРОГО JSON: {"schedule":[{"day":"Пн","subject":"...","topic":"..."}, ...7 элементов]}',
            'Верни только валидный JSON.' + NO_LATEX, 1500)
        mm = re.search(r'\{[\s\S]*\}', resp)
        if not mm:
            await reply(event, "Не смог составить план. Попробуй ещё раз.", keyboard=make_menu_keyboard())
            return True
        try:
            plan = json.loads(mm.group())
        except Exception:
            await reply(event, "Не смог составить план. Попробуй ещё раз.", keyboard=make_menu_keyboard())
            return True
        u['plan'] = plan
        save_user_data()
        lines = [f"{s.get('day','')}: {s.get('subject','')} — {s.get('topic','')}" for s in plan.get('schedule', [])]
        await reply(event, "📅 План готов:\n" + "\n".join(lines), keyboard=make_menu_keyboard())
        return True

    return False

# ===== CALLBACK (нажатия кнопок, если клавиатура заведётся) =====
_cb_reg = None
for _name in ('bot_callback', 'callback_created', 'message_callback'):
    _r = getattr(dp, _name, None)
    if callable(_r):
        _cb_reg = _r
        break

if _cb_reg:
    @_cb_reg()
    async def handle_callback(event):
        cmd = get_callback_cmd(event)
        uid = get_uid(event)
        ensure(uid)
        ack = getattr(event, 'answer', None)
        if callable(ack):
            try:
                await ack()
            except Exception:
                pass
        if not cmd:
            return
        act = ACTIONS.get(cmd)
        if act:
            await act(event, uid)
else:
    logger.warning("callback registration not found in this maxapi version")

# ===== ОБЫЧНЫЕ СООБЩЕНИЯ =====
@dp.message_created()
async def handle_message(event):
    user_id = get_uid(event)
    text = get_text(event)
    ensure(user_id)

    if text == '/start':
        await reply(event,
            "👋 Привет! Я Sferum Navigator — твой ИИ-наставник.\n\n"
            "🔄 Наш чат ОБЩИЙ с мини-приложением.\n"
            "📚 Пиши про оценки — сам запишу в дневник\n"
            "📱 /мини — открыть приложение\n"
            "📜 /история — общий чат\n"
            "🗑 /очистить — очистить общий чат\n\n"
            "Разделы (кнопками или словами): Тренажёр, Видео, Мотивация, План, Дневник, Меню",
            keyboard=make_menu_keyboard())
        return

    if text in ('/мини', '/mini'):
        await reply(event, f"📱 Мини-приложение:\n{MINI_APP_URL}")
        return

    if text == '/история':
        hist = load_chat_from_server()
        if not hist:
            await reply(event, "Общий чат пока пуст.")
            return
        lines = []
        for m in hist[-10:]:
            who = '🧑' if m.get('role') == 'user' else '🤖'
            src = ' (сайт)' if m.get('source') == 'web' else (' (MAX)' if m.get('source') == 'max' else '')
            lines.append(f"{who}{src}: {m.get('content','')[:120]}")
        await reply(event, "📜 Последние сообщения:\n" + "\n".join(lines))
        return

    if text == '/очистить':
        save_chat_to_server([])
        await reply(event, "🗑 Общий чат очищен.")
        return

    tcmd = detect_text_action(text)
    if tcmd:
        await ACTIONS[tcmd](event, user_id)
        return

    if await handle_state(event, user_id, text):
        return

    grade_triggers = ['оценк', 'получил', 'получила', 'поставили', 'поставил', 'заработал', 'балл', 'отметк']
    if any(t in text.lower() for t in grade_triggers) and re.search(r'\b[1-5]\b', text):
        try:
            resp = ask_gigachat(
                f'Ученик написал про оценки: «{text}». Определи ВСЕ предметы и оценки. Верни СТРОГО JSON-массив: [{{"subject":"...","grades":[5,4]}}]',
                'Верни только валидный JSON-массив.', 500)
            m = re.search(r'\[[\s\S]*\]', resp)
            if m:
                for item in json.loads(m.group()):
                    subj = item.get('subject')
                    grades = [g for g in item.get('grades', []) if isinstance(g, int) and 1 <= g <= 5]
                    if subj and grades:
                        user_data[user_id]['grades'].setdefault(subj, []).extend(grades)
                        await reply(event, f"📚 Записал в дневник: {subj} → {', '.join(map(str, grades))}")
                save_user_data()
        except Exception as e:
            logger.error(f"grades parse: {e}")

    history = load_chat_from_server()
    history.append({'role': 'user', 'content': text, 'timestamp': now_ms(), 'source': 'max'})

    thinking = None
    response = ask_gigachat(
        text,
        'Ты — дружелюбный ИИ-наставник для школьников. Отвечай коротко и понятно. Помни ВЕСЬ предыдущий разговор, включая сообщения с сайта. Если ученик рассказывает про оценки — порадуйся или поддержи.' + NO_LATEX,
        800, history)
    history.append({'role': 'assistant', 'content': response, 'timestamp': now_ms(), 'source': 'max'})
    save_chat_to_server(history)

    await delete_msg(thinking)
    await reply(event, response, keyboard=make_menu_keyboard())

if __name__ == '__main__':
    logger.info("Bot starting...")
    try:
        asyncio.run(dp.start_polling(bot))
    except AttributeError:
        try:
            dp.run(bot)
        except AttributeError:
            bot.run()
