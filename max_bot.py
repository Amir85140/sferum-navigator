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

import db as navigator_db

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'f9LHodD0cOLAk1Ry-yn7J-4F5oi3mZW9vlXyawwC4SxvVwTZ3DILUsVm6QJhFo2e3ReJ-0ucg1NORcMQ_FNI')
GIGA_ID = os.environ.get('GIGA_ID', '01a0bafa-206f-7e07-a2e7-df9e0acea285')
GIGA_SECRET = os.environ.get('GIGA_SECRET', '93e085d7-803b-4fe2-b1da-468aff78a450')
CODESPACE_NAME = os.environ.get('CODESPACE_NAME', 'automatic-system-p7gg76p4wqqwf99rj')
PROXY_BASE = f"https://{CODESPACE_NAME}-8000.app.github.dev"
CHANNEL = 'main'
USER_DATA_FILE = Path('user_data.json')
BANK_FILE = Path('bank.json')

NO_LATEX = (' СТРОГО ЗАПРЕЩЕНО использовать LaTeX (знаки $, $$, \\frac, \\sqrt и любые бэкслэши) '
            'и Markdown (**, #, `). Все формулы пиши ПРОСТЫМ текстом в одну строку, '
            'например: a = F / m, S = v * t, x^2.')

SYS_CHAT = ('Ты — Sferum Navigator, ИИ-наставник для школьников 5-11 классов. Правила:\n'
            '1) Отвечай СТРОГО на вопрос ученика, не уходи в сторону.\n'
            '2) Учебная тема — дай краткое объяснение сути + один пример.\n'
            '3) Просят конспект/материал/объяснение темы — дай 3-6 коротких пунктов по теме.\n'
            '4) Формулы пиши простым текстом (a = F / m).\n'
            '5) Отвечай коротко, до 10 строк.\n'
            '6) Не уверен — честно скажи и предложи, как уточнить.\n'
            'Помни весь предыдущий разговор.')

WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

SUBJ_ALIAS = {
    'матан': 'Математика', 'матем': 'Математика', 'мат-ка': 'Математика', 'математ': 'Математика',
    'алгебр': 'Алгебра', 'геом': 'Геометрия',
    'рус': 'Русский язык', 'русский': 'Русский язык', 'рус яз': 'Русский язык',
    'лит': 'Литература', 'литра': 'Литература', 'лит-ра': 'Литература',
    'англ': 'Английский язык', 'ин яз': 'Английский язык', 'ин я': 'Английский язык', 'английский': 'Английский язык',
    'физра': 'Физкультура', 'физ-ра': 'Физкультура', 'физкультура': 'Физкультура',
    'физ': 'Физика', 'физика': 'Физика',
    'хим': 'Химия', 'химия': 'Химия',
    'биол': 'Биология', 'биолог': 'Биология', 'биология': 'Биология',
    'гео': 'География', 'географ': 'География',
    'ист': 'История', 'истор': 'История',
    'общ': 'Обществознание', 'общество': 'Обществознание',
    'инф': 'Информатика', 'информ': 'Информатика', 'информатика': 'Информатика',
}

def expand_subject(name):
    low = str(name or '').lower().strip()
    if not low:
        return name
    if low in SUBJ_ALIAS:
        return SUBJ_ALIAS[low]
    for k, v in SUBJ_ALIAS.items():
        if low.startswith(k):
            return v
    return str(name).strip().title()

user_data: Dict[int, Dict[str, Any]] = {}

def load_user_data():
    global user_data
    user_data = {}

def save_user_data(uid=None):
    if uid is None:
        return
    d = user_data.get(uid)
    if not d:
        return
    try:
        navigator_db.set_state(uid, {'grades': d.get('grades'), 'plan': d.get('plan')})
    except Exception as e:
        logger.error(f"save state: {e}")

def now_ms():
    return int(time.time() * 1000)

def cur_week():
    return time.strftime('%G-W%V')

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
    sysp = (system_prompt or SYS_CHAT) + NO_LATEX
    hist = history or []
    for base in ('http://localhost:8000', PROXY_BASE):
        try:
            r = requests.post(base + '/chat',
                              json={'prompt': prompt, 'system': sysp,
                                    'max_tokens': max_tokens, 'history': hist},
                              timeout=75, verify=False)
            if r.ok:
                txt = r.json().get('reply', '')
                if txt:
                    return latex_to_plain(txt)
        except Exception as e:
            logger.error(f"chat via {base}: {e}")
    token = get_giga_token()
    if not token:
        return "❌ Не удалось подключиться к GigaChat"
    try:
        messages = [{'role': 'system', 'content': sysp}]
        if hist:
            messages.extend(hist[-16:])
        messages.append([{'role': 'user', 'content': prompt}])
        r = requests.post(
            'https://gigachat.devices.sberbank.ru/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'model': 'GigaChat:latest', 'messages': messages,
                  'max_tokens': max_tokens, 'temperature': 0.7},
            verify=False, timeout=60)
        if r.ok:
            return latex_to_plain(r.json()['choices'][0]['message']['content'])
    except Exception as e:
        logger.error(f"giga direct: {e}")
    return "❌ Ошибка при обращении к GigaChat"

# ===== ПОИСК ВИДЕО: VK + RuTube =====
def _words(query):
    return [w for w in re.split(r'\s+', query.lower()) if len(w) > 3]

def search_rutube(query, size=3):
    try:
        r = requests.get(
            'https://rutube.ru/api/video/',
            params={'query': query, 'page': 1, 'per_page': size * 2},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10, verify=False)
        if r.ok:
            raw = (r.json().get('results') or [])
            ws = _words(query)
            out = []
            for v in raw:
                title = re.sub(r'<[^>]+>', '', v.get('title', '') or '')
                tl = title.lower()
                if ws and not any(w in tl for w in ws):
                    continue
                url = v.get('video_url') or f"https://rutube.ru/video/{v.get('id','')}/"
                out.append({'title': title[:80], 'url': url})
                if len(out) >= size:
                    break
            return out
    except Exception as e:
        logger.error(f"rutube: {e}")
    return []

def search_vk(query, size=2):
    try:
        r = requests.get(
            'https://vk.com/video',
            params={'q': query},
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                     'Accept-Language': 'ru-RU,ru;q=0.9'},
            timeout=10, verify=False)
        if r.ok:
            pairs = re.findall(r'video(-?\d+_\d+)', r.text)
            seen, out = set(), []
            for p in pairs:
                if p in seen:
                    continue
                seen.add(p)
                out.append({'url': f'https://vk.com/video{p}'})
                if len(out) >= size:
                    break
            return out
    except Exception as e:
        logger.error(f"vk: {e}")
    return []

def load_bank():
    try:
        return json.loads(BANK_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}

# ===== БОТ =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
        logger.debug(f"kb1: {e}")
    try:
        from maxapi.types import Keyboard, Button
        rows = [[Button(text=t, payload={"cmd": c}) for t, c in row] for row in MENU_ROWS]
        kb = Keyboard(rows)
        fn = getattr(kb, 'as_markup', None)
        return fn() if callable(fn) else kb
    except Exception as e:
        logger.debug(f"kb2: {e}")
    return {
        "type": "inline_keyboard",
        "payload": {"buttons": [[{"type": "callback", "text": t, "payload": {"cmd": c}} for t, c in row] for row in MENU_ROWS]},
    }

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

def norm(s):
    return re.sub(r'[.,!?;:"\'\s]', '', str(s).lower().replace('ё', 'е'))

def ensure(uid):
    if uid not in user_data:
        try:
            st = navigator_db.get_state(uid)
        except Exception:
            st = {}
        user_data[uid] = {'grades': st.get('grades') or {}, 'state': None, 'plan': st.get('plan')}
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
    await reply(event,
        "✅ Тренажёр\n\nНапиши тему ТОЧНО (например: «дроби 6 класс», «квадратные уравнения») — "
        "дам одно задание строго по ней и объясню решение.",
        keyboard=make_menu_keyboard())

async def act_video(event, uid):
    u = ensure(uid)
    u['state'] = {'mode': 'video_topic'}
    await reply(event,
        "🎥 Видеоуроки\n\nНапиши тему ТОЧНО (например: «фотосинтез 6 класс», «теорема Пифагора») — "
        "дам ссылки на уроки VK/RuTube и подробное объяснение темы.",
        keyboard=make_menu_keyboard())

async def act_motivation(event, uid):
    u = ensure(uid)
    u['state'] = {'mode': 'motivation_mood'}
    await reply(event,
        "💪 Мотивация\n\nКак ты сейчас? Напиши одним словом или фразой:\n"
        "• устал\n• переживаю\n• лень\n• нормально\n\nИли опиши ситуацию — отвечу по делу.",
        keyboard=make_menu_keyboard())

def rebuild_plan(uid, old_plan):
    done = old_plan.get('done', []) or []
    pending = [x for x in old_plan.get('schedule', []) if x.get('topic') not in done]
    resp = ask_gigachat(
        f'Началась новая учебная неделя. Цель: {old_plan.get("goal","")}.\n'
        f'Непройденные темы с прошлой недели (ОБЯЗАТЕЛЬНО включи их): ' +
        '; '.join(f"{x.get('day')} {x.get('subject')}: {x.get('topic')}" for x in pending) +
        f'\nСоставь план на новую неделю Пн-Вс РОВНО 7 элементов (4-5 учебных + отдых), включив ВСЕ непройденные темы и добавив новые по цели.\n'
        f'Верни СТРОГО JSON: {{"goal":"...","schedule":[{{"day":"Пн","subject":"...","topic":"..."}}, ...7]}}',
        'Ты — эксперт по подготовке. Верни только валидный JSON.' + NO_LATEX, 1500)
    mm = re.search(r'\{[\s\S]*\}', resp)
    if not mm:
        return None
    try:
        plan = json.loads(mm.group())
    except Exception:
        return None
    plan['week'] = cur_week()
    plan['done'] = []
    return plan

async def act_plan(event, uid):
    u = ensure(uid)
    plan = u.get('plan')
    if plan and plan.get('week') != cur_week():
        newp = rebuild_plan(uid, plan)
        if newp:
            plan = newp
            u['plan'] = plan
            save_user_data(uid)
            await reply(event, "🔄 Неделя обновилась! Непройденные темы перенесены на эту неделю.\nНапиши «план», чтобы посмотреть.", keyboard=make_menu_keyboard())
            return
    if plan:
        lines = [f"{s2.get('day','')}: {s2.get('subject','')} — {s2.get('topic','')}" + (" ✅" if s2.get('topic') in (plan.get('done') or []) else "") for s2 in plan.get('schedule', [])]
        goal = plan.get('goal', '')
        header = f"🎯 Цель: {goal}\n\n" if goal else ""
        await reply(event, "📅 План на эту неделю:\n" + header + "\n".join(lines) +
                    "\n\nОтметить тему: напиши «пройдено <тема>».\nНовый план: «новый план».",
                    keyboard=make_menu_keyboard())
    else:
        u['state'] = {'mode': 'plan_wizard'}
        await reply(event,
            "📅 План\n\nНапиши одной строкой: класс, экзамен, цель\n"
            "Примеры:\n• 9, ОГЭ математика, сдать на 5\n• 11, ЕГЭ русский, 90+\n• 7, подтянуть физику",
            keyboard=make_menu_keyboard())

async def act_grades(event, uid):
    ensure(uid)['state'] = None
    g = user_data[uid].get('grades', {})
    if not g:
        await reply(event, "📚 Дневник пуст.\n\nНапиши про оценки словами — сам запишу:\n• «матан 5 4»\n• «получил 3 по физре»",
                    keyboard=make_menu_keyboard())
        return
    out, allg = [], []
    weak, strong = [], []
    for s, arr in g.items():
        allg += arr
        avg = sum(arr)/len(arr)
        out.append(f"{s}: {', '.join(map(str, arr))} (ср. {avg:.2f})")
        if avg < 3.5:
            weak.append(s)
        elif avg >= 4.5:
            strong.append(s)
    avg = sum(allg) / len(allg) if allg else 0
    txt = "📚 Твой дневник:\n" + "\n".join(out) + f"\n\nОбщий средний: {avg:.2f}"
    if strong:
        txt += "\n\n✅ Сильные: " + ", ".join(strong)
    if weak:
        txt += "\n⚠️ Подтянуть: " + ", ".join(weak) + "\nНапиши «разбери» — сделаю полный анализ."
    await reply(event, txt, keyboard=make_menu_keyboard())

async def act_bank(event, uid):
    u = ensure(uid)
    bank = load_bank()
    u['state'] = {'mode': 'bank_subject'}
    lines = ["📚 Банк заданий (ФИПИ-формат). Выбери предмет:"]
    for i, (k, v) in enumerate(bank.items(), 1):
        lines.append(f"{i}. {v.get('title', k)}")
    lines.append("\nНапиши номер или название.")
    await reply(event, "\n".join(lines), keyboard=make_menu_keyboard())

ACTIONS = {
    'menu': act_menu, 'quiz': act_quiz, 'video': act_video,
    'motivation': act_motivation, 'plan': act_plan, 'grades': act_grades, 'bank': act_bank,
}
TEXT_ALIASES = {
    'menu': ['меню', '🏠 меню'],
    'quiz': ['тренажёр', 'тренажер', 'тест', '✅ тренажёр'],
    'video': ['видео', '🎥 видео'],
    'motivation': ['мотивация', 'поддержи', '💪 мотивация'],
    'plan': ['план', '📅 план', 'новый план'],
    'grades': ['дневник', 'оценки мои', '📚 дневник'],
    'bank': ['банк', 'банк заданий'],
}

def detect_text_action(text):
    low = text.lower().strip()
    for cmd, aliases in TEXT_ALIASES.items():
        if low in aliases:
            return cmd
    return None

async def show_bank_task(event, uid):
    u = ensure(uid)
    st = u.get('state') or {}
    bank = load_bank()
    subj, topic, idx = st.get('subject'), st.get('topic'), st.get('idx', 0)
    tasks = []
    for t in bank.get(subj, {}).get('topics', []):
        if t.get('id') == topic:
            tasks = t.get('tasks', [])
    if idx >= len(tasks):
        u['state'] = None
        await reply(event, f"🏁 Итог: {st.get('correct',0)}/{st.get('total',0)}.", keyboard=make_menu_keyboard())
        return True
    task = tasks[idx]
    lines = [f"🎯 Задание {idx+1}/{len(tasks)}: {task.get('q','')}"]
    for i, o in enumerate(task.get('opts') or [], 1):
        lines.append(f"{i}) {o}")
    lines.append("\nНапиши номер варианта или ответ текстом.")
    await reply(event, "\n".join(lines), keyboard=make_menu_keyboard())
    return True

async def handle_bank_state(event, uid, text):
    u = ensure(uid)
    st = u.get('state') or {}
    mode = st.get('mode', '')
    bank = load_bank()
    low = text.lower().strip()

    if mode == 'bank_subject':
        keys = list(bank.keys())
        idx = None
        if low.isdigit() and 1 <= int(low) <= len(keys):
            idx = int(low) - 1
        else:
            for i, k in enumerate(keys):
                if low in bank[k].get('title', '').lower() or low == k:
                    idx = i
                    break
        if idx is None:
            await reply(event, "Не понял предмет. Напиши номер из списка.")
            return True
        subj = keys[idx]
        u['state'] = {'mode': 'bank_topic', 'subject': subj}
        lines = [f"📖 Темы: {bank[subj].get('title','')}"]
        for i, t in enumerate(bank[subj].get('topics', []), 1):
            lines.append(f"{i}. {t.get('title')} ({len(t.get('tasks', []))} зад.)")
        lines.append("\nНапиши номер темы.")
        await reply(event, "\n".join(lines), keyboard=make_menu_keyboard())
        return True

    if mode == 'bank_topic':
        subj = st.get('subject')
        topics = bank.get(subj, {}).get('topics', [])
        idx = None
        if low.isdigit() and 1 <= int(low) <= len(topics):
            idx = int(low) - 1
        else:
            for i, t in enumerate(topics):
                if low in t.get('title', '').lower():
                    idx = i
                    break
        if idx is None:
            await reply(event, "Не понял тему. Напиши номер из списка.")
            return True
        u['state'] = {'mode': 'bank_task', 'subject': subj, 'topic': topics[idx].get('id'), 'idx': 0, 'correct': 0, 'total': 0}
        return await show_bank_task(event, uid)

    if mode == 'bank_task':
        subj, topic, idx = st.get('subject'), st.get('topic'), st.get('idx', 0)
        tasks = []
        for t in bank.get(subj, {}).get('topics', []):
            if t.get('id') == topic:
                tasks = t.get('tasks', [])
        if idx >= len(tasks):
            u['state'] = None
            await reply(event, "Задания закончились.", keyboard=make_menu_keyboard())
            return True
        task = tasks[idx]
        opts = task.get('opts') or []
        correct = task.get('a', '')
        ok = False
        if opts and low.isdigit() and 1 <= int(low) <= len(opts):
            ok = norm(opts[int(low) - 1]) == norm(correct)
        else:
            ok = norm(low) == norm(correct) or (norm(correct) and norm(correct) in norm(low))
        st['correct'] = st.get('correct', 0) + (1 if ok else 0)
        st['total'] = st.get('total', 0) + 1
        try:
            navigator_db.save_progress(uid, topic, idx, ok)
        except Exception:
            pass
        st['idx'] = idx + 1
        u['state'] = st
        head = "✅ Верно!" if ok else f"❌ Неверно. Правильно: {correct}"
        if st['idx'] >= len(tasks):
            u['state'] = None
            await reply(event, f"{head}\n\n🏁 Итог: {st['correct']}/{st['total']}. Отличная работа!", keyboard=make_menu_keyboard())
        else:
            await reply(event, head)
            await show_bank_task(event, uid)
        return True

    return False

async def handle_state(event, uid, text):
    u = ensure(uid)
    st = u.get('state')
    if not st:
        return False
    mode = st.get('mode')

    if mode == 'quiz_topic':
        q = ask_gigachat(
            f'Составь ОДНО учебное задание СТРОГО по теме «{text}» для школьника. Требования: '
            f'question — короткий однозначный вопрос в рамках темы; '
            f'answer — одно слово, число или короткая формула простым текстом; '
            f'hint — одна подсказка; explanation — одно предложение, почему ответ такой. '
            f'Не выходи за рамки темы.\n'
            f'Верни СТРОГО JSON: {{"question":"...","answer":"...","hint":"...","explanation":"..."}}',
            'Ты — учитель-предметник. Верни только валидный JSON.' + NO_LATEX, 500)
        m = re.search(r'\{[\s\S]*\}', q)
        if not m:
            u['state'] = None
            await reply(event, "Не смог составить задание по этой теме. Уточни тему.", keyboard=make_menu_keyboard())
            return True
        try:
            task = json.loads(m.group())
        except Exception:
            u['state'] = None
            await reply(event, "Не смог составить задание по этой теме. Уточни тему.", keyboard=make_menu_keyboard())
            return True
        u['state'] = {'mode': 'quiz_answer', 'answer': task.get('answer', ''), 'topic': text,
                      'explanation': task.get('explanation', '')}
        hint = task.get('hint')
        await reply(event, f"🎯 Задание по теме «{text}»:\n{task.get('question','')}\n\nНапиши свой ответ." + (f"\n💡 {hint}" if hint else ""))
        return True

    if mode == 'quiz_answer':
        correct = st.get('answer', '')
        expl = st.get('explanation', '')
        ok = norm(text) == norm(correct) or (norm(correct) and norm(correct) in norm(text)) or (norm(text) and norm(text) in norm(correct))
        if not ok:
            chk = ask_gigachat(f'Вопрос был с ответом «{correct}». Ученик ответил «{text}». Верно ли по смыслу? Верни СТРОГО JSON: {{"correct": true|false}}', 'Верни только JSON.', 60)
            mm = re.search(r'(true|false)', chk.lower())
            ok = bool(mm and mm.group(1) == 'true')
        u['state'] = None
        expl_txt = f"\n\n💡 {expl}" if expl else ""
        if ok:
            await reply(event, f"✅ Верно! Отлично!{expl_txt}", keyboard=make_menu_keyboard())
        else:
            await reply(event, f"❌ Неверно.\nПравильный ответ: {correct}{expl_txt}", keyboard=make_menu_keyboard())
        return True

    if mode == 'video_topic':
        u['state'] = None
        r = ask_gigachat(
            f'Тема запроса ученика: «{text}».\n'
            f'1) query — ТОЧНЫЙ поисковый запрос для обучающего видео: тема словами ученика + слово "урок" или "объяснение"; 2-6 слов.\n'
            f'2) summary — ПОДРОБНОЕ объяснение темы для школьника: 5-8 предложений, с примером, определением и мини-выводом.\n'
            f'Верни СТРОГО JSON: {{"summary":"...","query":"..."}}',
            'Ты — методист и учитель. Верни только валидный JSON.' + NO_LATEX, 900)
        mm = re.search(r'\{[\s\S]*\}', r)
        summary, query = f"Тема: {text}", text
        if mm:
            try:
                obj = json.loads(mm.group())
                summary = obj.get('summary', summary)
                query = obj.get('query', text) or text
            except Exception:
                pass

        rt = search_rutube(query, 3)
        if not rt:
            rt = search_rutube(text, 3)
        vk = search_vk(query, 2)
        if not vk:
            vk = search_vk(text, 2)

        lines = []
        if rt:
            lines.append("📺 Смотри уроки (RuTube):")
            for i, v in enumerate(rt, 1):
                lines.append(f"{i}. {v['title']}\n   {v['url']}")
        if vk:
            lines.append("🎬 VK:")
            for i, v in enumerate(vk, 1):
                lines.append(f"{i}. {v['url']}")
        if not rt and not vk:
            lines.append("😕 Не нашёл готовое видео по этой теме в VK/RuTube — ниже объяснение текстом.")
        lines.append("")
        lines.append(f"🎓 Подробное объяснение:\n{summary}")
        await reply(event, "\n".join(lines), keyboard=make_menu_keyboard())
        return True

    if mode == 'motivation_mood':
        u['state'] = None
        r = ask_gigachat(
            f'Школьник написал о своём состоянии: «{text}».\n'
            f'Ответь как старший друг: 3-4 тёплых предложения БЕЗ банальностей. '
            f'Отреагируй на конкретику его слов и дай ОДИН выполнимый совет прямо сейчас (маленький шаг).',
            'Ты — тёплый наставник. Пиши живо, по делу, без шаблонов.' + NO_LATEX, 400)
        await reply(event, f"💪 {r}", keyboard=make_menu_keyboard())
        return True

    if mode == 'plan_wizard':
        u['state'] = None
        m = re.search(r'(\d{1,2})', text)
        grade = m.group(1) if m else '9'
        resp = ask_gigachat(
            f'Ученик {grade} класса. Запрос: «{text}».\n'
            f'1) goal — короткая цель (экзамен + результат).\n'
            f'2) schedule — расписание Пн-Вс РОВНО 7 элементов: 4-5 учебных дней и 2-3 дня отдыха (subject="отдых"). '
            f'Учебные дни: конкретный предмет и конкретная тема ИЗ запроса ученика, чередуй сложное/лёгкое.\n'
            f'Верни СТРОГО JSON: {{"goal":"...","schedule":[{{"day":"Пн","subject":"...","topic":"..."}}, ...7]}}',
            'Ты — эксперт по подготовке к экзаменам. Верни только валидный JSON.' + NO_LATEX, 1500)
        mm = re.search(r'\{[\s\S]*\}', resp)
        if not mm:
            await reply(event, "Не смог составить план. Напиши ещё раз: класс, экзамен, цель.", keyboard=make_menu_keyboard())
            return True
        try:
            plan = json.loads(mm.group())
        except Exception:
            await reply(event, "Не смог составить план. Напиши ещё раз: класс, экзамен, цель.", keyboard=make_menu_keyboard())
            return True
        plan.setdefault('goal', text)
        plan['week'] = cur_week()
        plan['done'] = []
        u['plan'] = plan
        save_user_data(uid)
        lines = [f"{s2.get('day','')}: {s2.get('subject','')} — {s2.get('topic','')}" for s2 in plan.get('schedule', [])]
        await reply(event, f"🎯 Цель: {plan.get('goal','')}\n\n📅 План готов:\n" + "\n".join(lines),
                    keyboard=make_menu_keyboard())
        return True

    if mode == 'grades_analyze':
        u['state'] = None
        g = user_data[uid].get('grades', {})
        desc = '\n'.join(f"{s}: {arr} (ср. {sum(arr)/len(arr):.2f})" for s, arr in g.items())
        r = ask_gigachat(
            f'Оценки ученика:\n{desc}\n\nКак педагог-эксперт дай:\n'
            f'1) 2 сильные стороны\n2) 2-3 слабых предмета и ЧТО именно подтянуть\n3) 3 конкретных шага на неделю.',
            'Пиши конкретно, по оценкам ученика, без воды.' + NO_LATEX, 600)
        await reply(event, f"🤖 Анализ:\n{r}", keyboard=make_menu_keyboard())
        return True

    return False

# ===== УВЕДОМЛЕНИЯ =====
async def scheduler():
    sent_day = None
    sent_week = None
    while True:
        try:
            now = time.localtime()
            today = time.strftime('%Y-%m-%d')
            week = time.strftime('%G-W%V')
            if now.tm_hour == 8 and now.tm_min < 5 and sent_day != today:
                sent_day = today
                day_name = WEEKDAYS[now.tm_wday]
                for u in navigator_db.all_users():
                    uid = u['user_id']
                    try:
                        st = navigator_db.get_state(uid)
                        plan = st.get('plan') or {}
                        item = next((x for x in plan.get('schedule', []) if x.get('day') == day_name), None)
                        if item:
                            await bot.send_message(chat_id=int(uid),
                                text=f"☀️ Доброе утро! Сегодня по плану: {item.get('subject','')} — {item.get('topic','')}.\nНапиши «начать», и я помогу!")
                    except Exception:
                        pass
            if now.tm_wday == 6 and now.tm_hour == 18 and sent_week != week:
                sent_week = week
                for u in navigator_db.all_users():
                    uid = u['user_id']
                    try:
                        st = navigator_db.get_state(uid)
                        prog = navigator_db.get_progress(uid)
                        done = sum(1 for p in prog if p.get('correct'))
                        grades = st.get('grades') or {}
                        allg = [g for arr in grades.values() for g in arr]
                        avg = sum(allg) / len(allg) if allg else 0
                        await bot.send_message(chat_id=int(uid),
                            text=f"📊 Недельный отчёт:\n• заданий решено верно: {done}\n• средний балл: {avg:.2f}\n\nТак держать! На следующей неделе продолжим 💪")
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"sched: {e}")
        await asyncio.sleep(30)

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

@dp.message_created()
async def handle_message(event):
    user_id = get_uid(event)
    text = get_text(event)
    low_txt = text.lower().strip()
    ensure(user_id)

    if text == '/start':
        await reply(event,
            "👋 Привет! Я Sferum Navigator — твой ИИ-наставник.\n\n"
            "🔄 Наш чат ОБЩИЙ с мини-приложением.\n"
            "📚 Пиши про оценки — сам запишу в дневник (понимаю сокращения: матан, физра, ин яз)\n"
            "📚 /банк — банк заданий ФИПИ\n"
            "📜 /история — общий чат\n"
            "🗑 /очистить — очистить общий чат\n"
            "❓ /help — справка\n\n"
            "Разделы: Тренажёр, Видео, Мотивация, План, Дневник, Меню",
            keyboard=make_menu_keyboard())
        return

    if text in ('/help', '/помощь', '/помоги'):
        await reply(event,
            "❓ Справка Sferum Navigator\n\n"
            "Команды:\n"
            "/start — приветствие и меню\n"
            "/help — эта справка\n"
            "/банк — банк заданий ФИПИ\n"
            "/история — последние сообщения общего чата\n"
            "/очистить — очистить общий чат\n\n"
            "Разделы (словами или кнопками):\n"
            "✅ Тренажёр — одно задание строго по теме + объяснение\n"
            "🎥 Видео — ссылки на уроки VK/RuTube + подробное объяснение\n"
            "💪 Мотивация — поддержка по твоему состоянию\n"
            "📅 План — неделя подготовки; непройденные темы переносятся\n"
            "📚 Дневник — оценки, средний балл, анализ\n"
            "🏠 Меню — показать меню\n\n"
            "Отметить тему: «пройдено <тема>».\n"
            "Совет: пиши тему ТОЧНО (с классом) — так ссылки и задания попадут в цель.")
        return

    if text in ('/банк', '/bank'):
        await act_bank(event, user_id)
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

    if low_txt.startswith('пройдено') or low_txt.startswith('я прошёл') or low_txt.startswith('я прошел'):
        u2 = ensure(user_id)
        p = u2.get('plan')
        if p:
            topic_name = text.split(' ', 1)[1].strip() if ' ' in text else ''
            p.setdefault('done', [])
            if topic_name and topic_name not in p['done']:
                p['done'].append(topic_name)
                save_user_data(user_id)
                await reply(event, f"✅ Отметил как пройденное: {topic_name}")
            else:
                await reply(event, "Напиши: пройдено <название темы>")
        else:
            await reply(event, "Сначала составь план: напиши «план».")
        return

    if low_txt in ('разбери', 'анализ', 'разбери оценки'):
        g = user_data[user_id].get('grades', {})
        if not g:
            await reply(event, "Сначала добавь оценки.")
            return
        ensure(user_id)['state'] = {'mode': 'grades_analyze'}
        await handle_state(event, user_id, 'анализ')
        return

    tcmd = detect_text_action(text)
    if tcmd:
        await ACTIONS[tcmd](event, user_id)
        return

    if await handle_bank_state(event, user_id, text):
        return

    if await handle_state(event, user_id, text):
        return

    grade_triggers = ['оценк', 'получил', 'получила', 'поставили', 'поставил', 'заработал', 'балл', 'отметк']
    if any(t in low_txt for t in grade_triggers) and re.search(r'\b[1-5]\b', text):
        try:
            resp = ask_gigachat(
                f'Ученик написал про оценки: «{text}». Определи ВСЕ предметы и оценки ТОЛЬКО из текста. '
                f'Верни СТРОГО JSON-массив: [{{"subject":"...","grades":[5,4]}}]',
                'Верни только валидный JSON-массив.', 500)
            m = re.search(r'\[[\s\S]*\]', resp)
            if m:
                for item in json.loads(m.group()):
                    subj = expand_subject(item.get('subject'))
                    grades = [g for g in item.get('grades', []) if isinstance(g, int) and 1 <= g <= 5]
                    if subj and grades:
                        user_data[user_id]['grades'].setdefault(subj, []).extend(grades)
                        await reply(event, f"📚 Записал в дневник: {subj} → {', '.join(map(str, grades))}")
                save_user_data(user_id)
        except Exception as e:
            logger.error(f"grades parse: {e}")

    history = load_chat_from_server()
    history.append({'role': 'user', 'content': text, 'timestamp': now_ms(), 'source': 'max'})

    thinking = None
    response = ask_gigachat(text, SYS_CHAT, 800, history)
    history.append({'role': 'assistant', 'content': response, 'timestamp': now_ms(), 'source': 'max'})
    save_chat_to_server(history)

    await delete_msg(thinking)
    await reply(event, response, keyboard=make_menu_keyboard())

async def run_all():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == '__main__':
    logger.info("Bot starting...")
    try:
        asyncio.run(run_all())
    except AttributeError:
        try:
            dp.run(bot)
        except AttributeError:
            bot.run()
