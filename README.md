# 🤖 Sferum Navigator — полная инструкция по запуску (для новичков)

Учебный мини-апп и бот для мессенджера MAX на базе GigaChat:
план подготовки к ОГЭ/ЕГЭ, тренажёры, целые варианты ФИПИ, дневник оценок, чат с ИИ,
решение задач по фото, видеоуроки, магазин скинов.

Эта инструкция рассчитана на человека БЕЗ опыта программирования.
Выполняй шаги сверху вниз, копируй команды как есть.

---

## 📑 Содержание
1. Что понадобится
2. Запуск через GitHub Codespaces (рекомендуется)
3. Запуск на своём компьютере
4. Где взять ключи
5. Файлы проекта
6. Библиотеки (requirements.txt)
7. Частые проблемы
8. Остановка и безопасность

---

## 1️⃣ Что понадобится

| Вещь | Зачем | Где взять |
|---|---|---|
| Аккаунт GitHub | Хостинг кода + бесплатная среда запуска | github.com |
| Ключи GigaChat | Чтобы ИИ отвечал | developers.sber.ru |
| Токен бота MAX | Чтобы бот жил в мессенджере | dev.max.ru |
| 15 минут времени | Первый запуск | — |

---

## 2️⃣ ЗАПУСК ЧЕРЕЗ GITHUB CODESPACES (ничего не ставим на компьютер)

### Шаг 1. Создай среду
1. Открой страницу этого репозитория на GitHub
2. Зелёная кнопка **Code** → вкладка **Codespaces** → **New codespace**
3. Подожди 1–3 минуты — откроется редактор, похожий на VS Code

### Шаг 2. Создай файл ключей `keys.sh`
В терминале (меню **Terminal → New Terminal**) выполни ОДНИМ блоком:
```bash
cat > keys.sh <<'EOF'
export GIGACHAT_CLIENT_ID="ВСТАВЬ_CLIENT_ID"
export GIGACHAT_CLIENT_SECRET="ВСТАВЬ_CLIENT_SECRET"
export MAX_BOT_TOKEN="ВСТАВЬ_ТОКЕН_MAX"
EOF
echo "keys.sh" >> .gitignore
nano keys.sh
```
Замени три значения в кавычках на свои (раздел 4). Сохрани: **Ctrl+O**, Enter, выход **Ctrl+X**.
Команда с `.gitignore` не даст случайно выложить ключи в GitHub.

### Шаг 3. Создай скрипт запуска `start_all.sh`
```bash
cat > start_all.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
[ -f keys.sh ] && source keys.sh
pkill -f proxy_server.py 2>/dev/null
pkill -f main.py 2>/dev/null
pkill -f max_bot.py 2>/dev/null
sleep 1
nohup python proxy_server.py > proxy.log 2>&1 &
nohup python main.py > bot.log 2>&1 &
sleep 3
echo "--- проверка сервера ---"
curl -s http://localhost:8000/health
echo
echo "--- проверка страницы ---"
curl -s http://localhost:8000/ | head -c 80
echo
echo "✅ Запущено. Логи: proxy.log и bot.log"
EOF
chmod +x start_all.sh
```

### Шаг 4. Установи библиотеки
```bash
pip install -r requirements.txt
```
В `requirements.txt` уже есть ВСЁ нужное (раздел 6). Команда просто доставит недостающее.

### Шаг 5. Запусти всё ОДНОЙ командой
```bash
bash start_all.sh
```
Успех = увидел `{"status":"ok"...}` и кусок HTML `<!DOCTYPE html>`.

### Шаг 6. Открой мини-апп
1. Внизу редактора вкладка **PORTS** → строка с портом **8000**
2. Наведи → иконка глобуса/стрелки → **Open in Browser**
3. Откроется главная аппа 🎉 Адрес вида `https://<имя-codespace>-8000.app.github.dev`

### Шаг 7. Привяжи апп к боту MAX
1. Зайди на **dev.max.ru** → твой бот → настройки мини-аппа
2. В поле URL вставь адрес из шага 6 (корень, без путей)
3. Сохрани → открой чат бота в MAX → апп доступен внутри мессенджера

---

## 3️⃣ ЗАПУСК НА СВОЁМ КОМПЬЮТЕРЕ (Windows / macOS / Linux)

### Шаг 1. Установи Python и Git
- Python 3.10+: python.org → Downloads → Install
  (Windows: обязательно галочка **Add Python to PATH**)
- Git: git-scm.com → Install
- Проверка:
  ```bash
  python --version
  git --version
  ```

### Шаг 2. Скачай проект
```bash
git clone https://github.com/ТВОЙ_НИК/sferum-navigator.git
cd sferum-navigator
```
(или кнопка **Code → Download ZIP** и распакуй)

### Шаг 3. Окружение и библиотеки
Windows:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Шаг 4. Ключи
Создай `keys.sh` как в шаге 2.2 и подключи:
```bash
source keys.sh
```
Windows (cmd) вместо файла:
```bat
set GIGACHAT_CLIENT_ID=твой_id
set GIGACHAT_CLIENT_SECRET=твой_secret
set MAX_BOT_TOKEN=твой_токен
```

### Шаг 5. Запусти ДВА окна терминала
Окно 1 — сервер и апп:
```bash
python proxy_server.py
```
Окно 2 — бот MAX:
```bash
python main.py
```
(если окно 2 ругается — попробуй `python max_bot.py`)

### Шаг 6. Открой апп
Браузер: `http://localhost:8000`
⚠️ Для работы внутри MAX нужен публичный адрес — поэтому основной способ всё же Codespaces (раздел 2).

---

## 4️⃣ Где взять ключи

### GigaChat (Client_ID / Client_Secret)
1. developers.sber.ru → войти → личный кабинет
2. Создать проект → включить **GigaChat API** (тариф PERS)
3. Создать credentials → получишь Client_ID и Client_Secret
4. Вставить в `keys.sh`

### Токен бота MAX
1. dev.max.ru → войти через MAX
2. Создать бота → скопировать **токен доступа**
3. Вставить в `keys.sh` в `MAX_BOT_TOKEN`

---

## 5️⃣ Файлы проекта

| Файл | Назначение |
|---|---|
| `index.html` | Мини-апп (весь интерфейс) |
| `proxy_server.py` | Сервер: чат GigaChat, фото-решалка, поиск видео, история, раздача аппа |
| `main.py` / `max_bot.py` | Бот для мессенджера MAX |
| `services.py`, `db.py` | Внутренние сервисы и база данных |
| `navigator.db`, `user_data.json` | Данные пользователей (оценки, прогресс) |
| `requirements.txt` | Список библиотек Python |
| `keys.sh` | Твои секретные ключи (НЕ должен попадать в GitHub) |
| `start_all.sh` | Запуск всего одной командой |
| `terms.html`, `privacy.html` | Юридические страницы аппа |

---

## 6️⃣ Библиотеки (requirements.txt)

Все зависимости проекта лежат в файле **requirements.txt**. Установка одной командой:
```bash
pip install -r requirements.txt
```

Если нужно ДОБАВИТЬ библиотеку (появилась ошибка `ModuleNotFoundError: No module named 'имя'`):
```bash
pip install имя_библиотеки
pip freeze > requirements.txt
```

Если requirements.txt пуст или потерян — восстанови из рабочего окружения:
```bash
pip freeze > requirements.txt
```
Эта команда запишет ВСЕ реально установленные и работающие библиотеки с точными версиями.

---

## 7️⃣ Частые проблемы

| Симптом | Решение |
|---|---|
| `{"detail":"Not Found"}` по адресу | Обнови страницу Ctrl+Shift+R; проверь, что прокси запущен: `bash start_all.sh` |
| `Address already in use` | `pkill -f proxy_server.py` и запусти снова |
| Ошибки 401/403 от ИИ | Неверные ключи GigaChat: проверь `keys.sh`, выполни `source keys.sh` |
| Бот молчит в MAX | Проверь токен; посмотри лог: `tail -30 bot.log` |
| `ModuleNotFoundError` | `pip install имя_модуля` и добавь в requirements.txt (раздел 6) |
| Codespace «уснул» | github.com/codespaces → Start |
| Вечное «Setting up codespace» | githubstatus.com — авария у GitHub; подожди и пересоздай |
| Что запущено? | Логи: `tail -30 proxy.log` и `tail -30 bot.log` |

---

## 8️⃣ Остановка и безопасность

Остановить всё:
```bash
pkill -f proxy_server.py
pkill -f main.py
pkill -f max_bot.py
```

Безопасность:
- Никогда не коммить `keys.sh` (он уже добавлен в `.gitignore` шагом 2.2)
- Не показывай ключи на скриншотах
- Потерял ключи — отзови и создай новые в кабинете Sber / dev.max.ru
