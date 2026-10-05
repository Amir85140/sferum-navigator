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
CHANNEL = 'main'
USER_DATA_FILE = Path('user_data.json')

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
        messages.append({'role': 'user', 'content': prompt})
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

# ===== ПОИСК ВИДЕО: ТОЛЬКО VK + RuTube =====
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
    body = getattr(m, 'body', None)
    if body:
        text = getattr(body, 'text', None)
        if isinstance(text, str):
            return text.strip()
    for attr in ('body', 'text'):
        v = getattr(m, attr, None)
        if isinstance(v, str):
            return v.strip()
        if v is not None:
            t = getattr(v, 'text', None)
            if isinstance(t, str):
                return t.strip()
    return ''

def get_photo_url(event):
    """Получить URL фото из сообщения (структура maxapi)"""
    m = getattr(event, 'message', None)
    if m is None:
        return None
    body = getattr(m, 'body', None)
    if body is None:
        return None
    attachments = getattr(body, 'attachments', None)
    if not attachments:
        return None
    for att in attachments:
        att_type = getattr(att, 'type', '')
        if att_type == 'image':
            payload = getattr(att, 'payload', None)
            if payload:
                url = getattr(payload, 'url', None)
                if url and str(url).startswith('http'):
                    return url
    return None

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
    await reply(event,
        "✅ Тренажёр\n\nНапиши тему ТОЧНО (например: «дроби 6 класс», «квадратные уравнения») — "
        "дам одно задание строго по ней и объясню решение.",
        keyboard=make_menu_keyboard())

async def act_video(event, uid):
    u = ensure(uid)
    u['state'] = {'mode': 'video_topic'}
    await reply(event,
        " Видеоуроки\n\nНапиши тему ТОЧНО (например: «фотосинтез 6 класс», «теорема Пифагора») — "
        "объясню её и дам прямые ссылки на уроки в VK и RuTube именно по этой теме.",
        keyboard=make_menu_keyboard())

async def act_motivation(event, uid):
    u = ensure(uid)
    u['state'] = {'mode': 'motivation_mood'}
    await reply(event,
        "💪 Мотивация\n\nКак ты сейчас? Напиши одним словом или фразой:\n"
        "• устал\n• переживаю\n• лень\n• нормально\n\nИли опиши ситуацию — отвечу по делу.",
        keyboard=make_menu_keyboard())

async def act_plan(event, uid):
    u = ensure(uid)
    plan = u.get('plan')
    if plan:
        lines = [f"{s.get('day','')}: {s.get('subject','')} — {s.get('topic','')}" for s in plan.get('schedule', [])]
        goal = plan.get('goal', '')
        header = f"🎯 Цель: {goal}\n\n" if goal else ""
        await reply(event, "📅 Твой план на неделю:\n" + header + "\n".join(lines) +
                    "\n\nНапиши «новый план», чтобы составить заново.",
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
        await reply(event, "📚 Дневник пуст.\n\nНапиши про оценки словами — сам запишу:\n• «математика 5 4»\n• «получил 3 по физике»",
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

ACTIONS = {
    'menu': act_menu, 'quiz': act_quiz, 'video': act_video,
    'motivation': act_motivation, 'plan': act_plan, 'grades': act_grades,
}
TEXT_ALIASES = {
    'menu': ['меню', '🏠 меню'],
    'quiz': ['тренажёр', 'тренажер', 'тест', '✅ тренажёр'],
    'video': ['видео', ' видео'],
    'motivation': ['мотивация', 'поддержи', '💪 мотивация'],
    'plan': ['план', '📅 план', 'новый план'],
    'grades': ['дневник', 'оценки мои', ' дневник'],
}

def detect_text_action(text):
    low = text.lower().strip()
    for cmd, aliases in TEXT_ALIASES.items():
        if low in aliases:
            return cmd
    return None

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
            f'1) summary — 2 предложения сути темы простыми словами + один пример.\n'
            f'2) query — ТОЧНЫЙ поисковый запрос для обучающего видео: назови тему словами ученика '
            f'и добавь слово "урок" или "объяснение"; 2-6 слов, без кавычек и знаков препинания.\n'
            f'Верни СТРОГО JSON: {{"summary":"...","query":"..."}}',
            'Ты — методист. Верни только валидный JSON.' + NO_LATEX, 500)
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

        lines = [f"🎓 {summary}", ""]
        if rt:
            lines.append("📺 RuTube:")
            for i, v in enumerate(rt, 1):
                lines.append(f"{i}. {v['title']}\n   {v['url']}")
        if vk:
            lines.append("🎬 VK:")
            for i, v in enumerate(vk, 1):
                lines.append(f"{i}. {v['url']}")
        if not rt and not vk:
            lines.append("😕 Не нашёл готовое видео по этой теме в VK/RuTube.")
            lines.append("Объяснение выше — по сути. Уточни тему (добавь класс) и попробуй ещё раз.")
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
        u['plan'] = plan
        save_user_data()
        lines = [f"{s.get('day','')}: {s.get('subject','')} — {s.get('topic','')}" for s in plan.get('schedule', [])]
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
    ensure(user_id)

    # ===== ФОТО: КАК В МИНИ-АППЕ (base64 с префиксом data:image/png;base64,) =====
    photo_url = get_photo_url(event)
    
    if photo_url:
        logger.info(f"Найдено фото: {photo_url}")
        try:
            # 1. Скачиваем фото
            img_data = requests.get(photo_url, timeout=15, verify=False).content
            
            # 2. Определяем тип (PNG или JPEG)
            content_type = 'image/png'
            if img_data[:2] == b'\xff\xd8':
                content_type = 'image/jpeg'
            
            # 3. Кодируем в base64 с префиксом (КАК В МИНИ-АППЕ!)
            image_b64 = f"data:{content_type};base64," + base64.b64encode(img_data).decode('utf-8')
            
            # 4. Отправляем JSON-запрос на /vision (точно как мини-апп)
            r = requests.post(
                f"{PROXY_BASE}/vision",
                json={
                    "image": image_b64,
                    "prompt": "Реши задачу на фото пошагово, объясни каждый шаг. Формулы оформляй в LaTeX: инлайн в $...$, блочные в $$...$$.",
                    "latex": True
                },
                timeout=30,
                verify=False
            )
            
            if r.ok:
                result = r.json()
                ocr_text = result.get('ocr', '')
                solution = result.get('solution', '')
                mode = result.get('mode', '')
                
                if ocr_text or solution:
                    logger.info(f"OCR: {ocr_text[:100]}")
                    response_text = f"📸 Решение{' (через OCR)' if mode == 'ocr' else ''}\n"
                    if ocr_text:
                        response_text += f"🔤 {ocr_text}\n\n"
                    response_text += solution
                    await reply(event, response_text, keyboard=make_menu_keyboard())
                    return
                else:
                    logger.warning("OCR вернул пустой результат")
            else:
                logger.error(f"OCR вернул статус {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"photo vision error: {e}")
        
        if not text:
            await reply(event, "❌ Не смог распознать текст на фото. Напиши задачу текстом — решу.")
            return

    # ===== ОБЫЧНАЯ ОБРАБОТКА ТЕКСТА =====
    if text == '/start':
        await reply(event,
            " Привет! Я Sferum Navigator — твой ИИ-наставник.\n\n"
            "🔄 Наш чат ОБЩИЙ с мини-приложением.\n"
            "📚 Пиши про оценки — сам запишу в дневник\n"
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
            "/история — последние сообщения общего чата\n"
            "/очистить — очистить общий чат\n\n"
            "Разделы (словами или кнопками):\n"
            "✅ Тренажёр — одно задание строго по теме + объяснение\n"
            "🎥 Видео — суть темы + прямые ссылки на уроки VK и RuTube\n"
            "💪 Мотивация — поддержка по твоему состоянию\n"
            " План — неделя подготовки под твою цель\n"
            "📚 Дневник — оценки, средний балл, анализ\n"
            "🏠 Меню — показать меню\n\n"
            "Совет: пиши тему ТОЧНО (с классом) — так ссылки и задания попадут в цель.")
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

    if text.lower().strip() in ('разбери', 'анализ', 'разбери оценки'):
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

    if await handle_state(event, user_id, text):
        return

    grade_triggers = ['оценк', 'получил', 'получила', 'поставили', 'поставил', 'заработал', 'балл', 'отметк']
    if any(t in text.lower() for t in grade_triggers) and re.search(r'\b[1-5]\b', text):
        try:
            resp = ask_gigachat(
                f'Ученик написал про оценки: «{text}». Определи ВСЕ предметы и оценки ТОЛЬКО из текста. '
                f'Верни СТРОГО JSON-массив: [{{"subject":"...","grades":[5,4]}}]',
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

    response = ask_gigachat(text, SYS_CHAT, 800, history)
    history.append({'role': 'assistant', 'content': response, 'timestamp': now_ms(), 'source': 'max'})
    save_chat_to_server(history)

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
