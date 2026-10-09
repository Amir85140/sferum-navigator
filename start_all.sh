#!/bin/bash
cd "$(dirname "$0")"
pkill -f proxy_server.py 2>/dev/null
pkill -f max_bot.py 2>/dev/null
pkill -f main.py 2>/dev/null
sleep 1
nohup python max_bot.py > bot.log 2>&1 &
nohup python proxy_server.py > proxy.log 2>&1 &
sleep 3
echo "=== ПРОВЕРКА ==="
curl -s http://localhost:8000/health && echo
curl -s http://localhost:8000/ | head -c 60 && echo
echo "процессов бота: $(ps aux | grep -c '[m]ax_bot.py')"
echo "✅ Готово: PORTS -> 8000 -> Open in Browser"
