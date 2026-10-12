# 🤖 Sferum Navigator — ИИ-наставник в MAX на базе GigaChat

**Sferum Navigator** — мини-апп и бот в мессенджере MAX, который помогает школьникам готовиться к ОГЭ и ЕГЭ: объясняет темы, генерирует тренажёры, составляет персональный план, ведёт дневник оценок и поддерживает мотивацию. Всё — на базе **GigaChat (Сбер)**.

🏆 Проект-участник хакатона Sferum (платформа MAX).

---

## 🚀 Быстрый старт
1. Зайдите в codespace проекта (sferum-navigator) и после загрузки откройте терминал и введите туда эти команды
```
pkill -9 -f proxy_server.py; pkill -9 -f max_bot.py
nohup python proxy_server.py > proxy.log 2>&1 &
nohup python max_bot.py > bot.log 2>&1 &
sleep 2
curl -s http://localhost:8000/health
tail -3 bot.log
```
