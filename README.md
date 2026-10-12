# 🤖 Sferum Navigator — ИИ-наставник в MAX на базе GigaChat


**Sferum Navigator** — мини-апп и бот в мессенджере MAX, который помогает школьникам готовиться к ОГЭ и ЕГЭ и не только: объясняет темы, генерирует тренажёры, составляет персональный план, ведёт дневник оценок и поддерживает мотивацию. Всё — на базе **GigaChat от Сбера**.


###Быстрый старт или как запустить бота в MAX

Шаг 1. Зайдите в codespace проекта (sferum-navigator) и после загрузки откройте терминал и введите туда эту команду, чтобы загрузить все нужные библиотеки
```
pip install -r requirements.txt
```
Шаг 2. После этого, когда все библиотеки загрузятся, введите эти команды:
```
pkill -9 -f proxy_server.py; pkill -9 -f max_bot.py
nohup python proxy_server.py > proxy.log 2>&1 &
nohup python max_bot.py > bot.log 2>&1 &
sleep 2
curl -s http://localhost:8000/health
tail -3 bot.log
```
Шаг 3. После того, как вам покажут эти строки
```
{"status":"ok","chat_sync":true,"ocr":true}INFO:__main__:Bot starting...
INFO:dispatcher:Бот: @sferumnavigator_bot first_name=Sferum-навигатор id=484364316
INFO:dispatcher:Зарегистрировано 2 обработчиков событий
```
Шаг 4. Вы должны будете перейти в бота в MAX по данной ссылке
```
https://max.ru/sferumnavigator_bot
```
Шаг 5. На этом инструкция заканчивается, теперь вы можете проверять бота, самое главное, чтобы сервера не выключились, иначе прейдется выполнить шаг 2
