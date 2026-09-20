from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from services import PlannerService, AIService
from datetime import datetime

app = FastAPI(title="Sferum Navigator", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# Хранилище истории
history = []

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sferum Navigator</title>
        <style>
            :root {
                --bg-color: #F0F2F5;
                --sidebar-bg: #FFFFFF;
                --text-color: #000000;
                --text-secondary: #818C99;
                --primary-color: #0077FF;
                --border-color: #E1E3E6;
                --card-bg: #FFFFFF;
                --hover-bg: #F5F6F8;
            }

            body.dark-theme {
                --bg-color: #121212;
                --sidebar-bg: #1C1C1E;
                --text-color: #FFFFFF;
                --text-secondary: #8E8E93;
                --primary-color: #71AAEB;
                --border-color: #2C2D2E;
                --card-bg: #1C1C1E;
                --hover-bg: #2C2D2E;
            }

            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--bg-color);
                color: var(--text-color);
                height: 100vh;
                overflow: hidden;
            }

            .container {
                display: flex;
                height: 100vh;
            }

            /* ЛЕВАЯ ПАНЕЛЬ - ИСТОРИЯ */
            .sidebar {
                width: 280px;
                background: var(--sidebar-bg);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .sidebar-header {
                padding: 20px;
                border-bottom: 1px solid var(--border-color);
                font-size: 18px;
                font-weight: 600;
            }

            .history-list {
                flex: 1;
                overflow-y: auto;
                padding: 10px;
            }

            .history-item {
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 8px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.2s;
            }

            .history-item:hover {
                background: var(--hover-bg);
            }

            .history-time {
                font-size: 12px;
                color: var(--text-secondary);
                margin-top: 4px;
            }

            .clear-history {
                padding: 12px;
                border-top: 1px solid var(--border-color);
                text-align: center;
                color: var(--primary-color);
                cursor: pointer;
                font-size: 14px;
            }

            /* ЦЕНТРАЛЬНАЯ ЧАСТЬ - ПОИСК */
            .main-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
            }

            .search-container {
                width: 100%;
                max-width: 600px;
            }

            .search-box {
                position: relative;
                margin-bottom: 30px;
            }

            .search-input {
                width: 100%;
                padding: 16px 50px 16px 20px;
                font-size: 16px;
                border: 2px solid var(--border-color);
                border-radius: 12px;
                background: var(--card-bg);
                color: var(--text-color);
                outline: none;
                transition: border-color 0.2s;
            }

            .search-input:focus {
                border-color: var(--primary-color);
            }

            .search-button {
                position: absolute;
                right: 10px;
                top: 50%;
                transform: translateY(-50%);
                background: var(--primary-color);
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                color: white;
                cursor: pointer;
                font-weight: 600;
            }

            .quick-ideas {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                width: 100%;
            }

            .idea-chip {
                padding: 15px;
                background: var(--card-bg);
                border: 2px solid var(--border-color);
                border-radius: 12px;
                text-align: center;
                cursor: pointer;
                transition: all 0.2s;
            }

            .idea-chip:hover {
                border-color: var(--primary-color);
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,119,255,0.15);
            }

            .idea-chip-icon {
                font-size: 32px;
                margin-bottom: 8px;
            }

            .idea-chip-title {
                font-size: 14px;
                font-weight: 600;
            }

            /* ПРАВАЯ ПАНЕЛЬ - КОЛЕСО ИДЕЙ */
            .wheel-panel {
                width: 320px;
                background: var(--sidebar-bg);
                border-left: 1px solid var(--border-color);
                padding: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }

            .wheel-title {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 20px;
            }

            .wheel-container {
                position: relative;
                width: 280px;
                height: 280px;
            }

            .wheel {
                width: 100%;
                height: 100%;
                border-radius: 50%;
                position: relative;
                transition: transform 3s cubic-bezier(0.17, 0.67, 0.83, 0.67);
            }

            .wheel-segment {
                position: absolute;
                width: 50%;
                height: 50%;
                transform-origin: right bottom;
                left: 0;
                top: 0;
                border: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                font-weight: 600;
                cursor: pointer;
                transition: opacity 0.2s;
            }

            .wheel-segment:hover {
                opacity: 0.8;
            }

            .wheel-center {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 60px;
                height: 60px;
                background: var(--primary-color);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                cursor: pointer;
                z-index: 10;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }

            .wheel-center:active {
                transform: translate(-50%, -50%) scale(0.95);
            }

            .theme-toggle {
                position: fixed;
                top: 20px;
                right: 340px;
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 50%;
                width: 44px;
                height: 44px;
                font-size: 20px;
                cursor: pointer;
                z-index: 100;
            }

            .hidden { display: none !important; }
        </style>
    </head>
    <body>
        <button class="theme-toggle" onclick="toggleTheme()">🌙</button>
        
        <div class="container">
            <!-- ЛЕВАЯ ПАНЕЛЬ - ИСТОРИЯ -->
            <div class="sidebar">
                <div class="sidebar-header"> История</div>
                <div class="history-list" id="historyList">
                    <div style="padding: 20px; text-align: center; color: var(--text-secondary);">
                        История пуста
                    </div>
                </div>
                <div class="clear-history" onclick="clearHistory()">
                    Очистить историю
                </div>
            </div>

            <!-- ЦЕНТРАЛЬНАЯ ЧАСТЬ - ПОИСК -->
            <div class="main-content">
                <div class="search-container">
                    <div class="search-box">
                        <input type="text" class="search-input" id="searchInput" 
                               placeholder="Что тебя интересует?" 
                               onkeypress="if(event.key==='Enter') handleSearch()">
                        <button class="search-button" onclick="handleSearch()">Найти</button>
                    </div>
                    
                    <div class="quick-ideas">
                        <div class="idea-chip" onclick="quickAction('planner')">
                            <div class="idea-chip-icon"></div>
                            <div class="idea-chip-title">Планировщик</div>
                        </div>
                        <div class="idea-chip" onclick="quickAction('homework')">
                            <div class="idea-chip-icon">📝</div>
                            <div class="idea-chip-title">Помощь с ДЗ</div>
                        </div>
                        <div class="idea-chip" onclick="quickAction('explain')">
                            <div class="idea-chip-icon">🎓</div>
                            <div class="idea-chip-title">Объяснить тему</div>
                        </div>
                        <div class="idea-chip" onclick="quickAction('tests')">
                            <div class="idea-chip-icon">✅</div>
                            <div class="idea-chip-title">Тесты</div>
                        </div>
                        <div class="idea-chip" onclick="quickAction('motivation')">
                            <div class="idea-chip-icon">💪</div>
                            <div class="idea-chip-title">Мотивация</div>
                        </div>
                        <div class="idea-chip" onclick="quickAction('videos')">
                            <div class="idea-chip-icon">🎥</div>
                            <div class="idea-chip-title">Видеоуроки</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ПРАВАЯ ПАНЕЛЬ - КОЛЕСО ИДЕЙ -->
            <div class="wheel-panel">
                <div class="wheel-title"> Колесо идей</div>
                <div class="wheel-container">
                    <div class="wheel" id="wheel"></div>
                    <div class="wheel-center" onclick="spinWheel()">🎲</div>
                </div>
            </div>
        </div>

        <script>
            const allIdeas = [
                { id: 'planner', name: 'Планировщик', color: '#FF6B6B' },
                { id: 'homework', name: 'Помощь с ДЗ', color: '#4ECDC4' },
                { id: 'explain', name: 'Объяснение', color: '#45B7D1' },
                { id: 'tests', name: 'Тесты', color: '#FFA07A' },
                { id: 'motivation', name: 'Мотивация', color: '#98D8C8' },
                { id: 'videos', name: 'Видео', color: '#F7DC6F' }
            ];

            let currentRotation = 0;

            // Создаем колесо
            function createWheel() {
                const wheel = document.getElementById('wheel');
                const segmentAngle = 360 / allIdeas.length;
                
                allIdeas.forEach((idea, index) => {
                    const segment = document.createElement('div');
                    segment.className = 'wheel-segment';
                    segment.style.background = idea.color;
                    segment.style.transform = `rotate(${index * segmentAngle}deg)`;
                    segment.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%)';
                    segment.innerHTML = `<span style="transform: rotate(${segmentAngle/2}deg) translate(20px, -10px);">${idea.name}</span>`;
                    segment.onclick = () => selectIdea(idea.id);
                    wheel.appendChild(segment);
                });
            }

            function spinWheel() {
                currentRotation += 720 + Math.random() * 360;
                document.getElementById('wheel').style.transform = `rotate(${currentRotation}deg)`;
                
                setTimeout(() => {
                    const randomIdea = allIdeas[Math.floor(Math.random() * allIdeas.length)];
                    selectIdea(randomIdea.id);
                }, 3000);
            }

            function selectIdea(id) {
                const idea = allIdeas.find(i => i.id === id);
                document.getElementById('searchInput').value = idea.name;
                addToHistory(idea.name);
            }

            function quickAction(id) {
                const idea = allIdeas.find(i => i.id === id);
                document.getElementById('searchInput').value = idea.name;
                handleSearch();
            }

            async function handleSearch() {
                const input = document.getElementById('searchInput');
                const query = input.value.trim();
                if (!query) return;

                addToHistory(query);
                
                // Здесь можно добавить обработку поиска
                alert('Поиск: ' + query);
            }

            function addToHistory(query) {
                history.unshift({
                    query: query,
                    time: new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'})
                });
                if (history.length > 20) history.pop();
                renderHistory();
            }

            function renderHistory() {
                const list = document.getElementById('historyList');
                if (history.length === 0) {
                    list.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">История пуста</div>';
                    return;
                }
                
                list.innerHTML = history.map(item => `
                    <div class="history-item" onclick="document.getElementById('searchInput').value='${item.query}'">
                        <div>${item.query}</div>
                        <div class="history-time">${item.time}</div>
                    </div>
                `).join('');
            }

            function clearHistory() {
                history = [];
                renderHistory();
            }

            function toggleTheme() {
                document.body.classList.toggle('dark-theme');
                const isDark = document.body.classList.contains('dark-theme');
                document.querySelector('.theme-toggle').textContent = isDark ? '☀️' : '';
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
            }

            if (localStorage.getItem('theme') === 'dark') {
                document.body.classList.add('dark-theme');
                document.querySelector('.theme-toggle').textContent = '️';
            }

            createWheel();
        </script>
    </body>
    </html>
    """

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = AIService.process_message(request.message)
    return {"response": response}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
