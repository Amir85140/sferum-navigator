from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services import PlannerService, AIService

app = FastAPI(title="Sferum Navigator", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

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

            /* ПРАВАЯ ПАНЕЛЬ - КОЛЕСО ИДЕЙ (как в Яндекс Музыке) */
            .wheel-panel {
                width: 360px;
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
                margin-bottom: 10px;
            }

            .wheel-subtitle {
                font-size: 13px;
                color: var(--text-secondary);
                margin-bottom: 20px;
                text-align: center;
            }

            .wheel-wrapper {
                position: relative;
                width: 320px;
                height: 320px;
            }

            .wheel {
                width: 100%;
                height: 100%;
                border-radius: 50%;
                position: relative;
                cursor: grab;
                transition: transform 0.1s;
                box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            }

            .wheel:active {
                cursor: grabbing;
            }

            .wheel-segment {
                position: absolute;
                width: 50%;
                height: 50%;
                transform-origin: right bottom;
                left: 0;
                top: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: 600;
                color: white;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                overflow: hidden;
            }

            .wheel-segment span {
                transform: rotate(12deg) translate(30px, -20px);
                white-space: nowrap;
            }

            .wheel-center {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 70px;
                height: 70px;
                background: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 28px;
                z-index: 10;
                box-shadow: 0 4px 16px rgba(0,0,0,0.2);
                pointer-events: none;
            }

            .wheel-pointer {
                position: absolute;
                top: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 15px solid transparent;
                border-right: 15px solid transparent;
                border-top: 25px solid var(--primary-color);
                z-index: 20;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
            }

            .selected-idea {
                margin-top: 20px;
                padding: 15px 20px;
                background: var(--primary-color);
                color: white;
                border-radius: 12px;
                font-weight: 600;
                text-align: center;
                min-height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .theme-toggle {
                position: fixed;
                top: 20px;
                right: 380px;
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
                <div class="sidebar-header">📜 История</div>
                <div class="history-list" id="historyList">
                    <div style="padding: 20px; text-align: center; color: var(--text-secondary);">
                        История пуста
                    </div>
                </div>
                <div class="clear-history" onclick="clearHistory()">
                    🗑 Очистить историю
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
                            <div class="idea-chip-icon">📅</div>
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
                            <div class="idea-chip-icon"></div>
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
                <div class="wheel-title">🎡 Колесо идей</div>
                <div class="wheel-subtitle">Крути колесо мышкой или пальцем</div>
                <div class="wheel-wrapper">
                    <div class="wheel-pointer"></div>
                    <div class="wheel" id="wheel"></div>
                    <div class="wheel-center">🎯</div>
                </div>
                <div class="selected-idea" id="selectedIdea">
                    Выбери идею!
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
                { id: 'videos', name: 'Видео', color: '#F7DC6F' },
                { id: 'progress', name: 'Прогресс', color: '#BB8FCE' },
                { id: 'deadlines', name: 'Дедлайны', color: '#F1948A' },
                { id: 'adaptive', name: 'Адаптивность', color: '#82E0AA' },
                { id: 'group', name: 'Группа', color: '#85C1E9' },
                { id: 'journal', name: 'Журнал', color: '#F0B27A' },
                { id: 'gamification', name: 'Геймификация', color: '#D7BDE2' },
                { id: 'personalization', name: 'Персонализация', color: '#A9DFBF' },
                { id: 'offline', name: 'Оффлайн', color: '#FAD7A0' },
                { id: 'export', name: 'Экспорт', color: '#AED6F1' }
            ];

            let currentRotation = 0;
            let isDragging = false;
            let startAngle = 0;
            let lastAngle = 0;
            let velocity = 0;
            let lastTime = 0;
            let animationId = null;

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
                    segment.innerHTML = `<span>${idea.name}</span>`;
                    wheel.appendChild(segment);
                });
            }

            // Получаем угол мыши относительно центра колеса
            function getAngle(e) {
                const wheel = document.getElementById('wheel');
                const rect = wheel.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                
                const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                const clientY = e.touches ? e.touches[0].clientY : e.clientY;
                
                return Math.atan2(clientY - centerY, clientX - centerX) * 180 / Math.PI;
            }

            // Начало вращения
            function startDrag(e) {
                e.preventDefault();
                isDragging = true;
                startAngle = getAngle(e);
                lastAngle = startAngle;
                velocity = 0;
                lastTime = Date.now();
                
                if (animationId) {
                    cancelAnimationFrame(animationId);
                }
                
                document.getElementById('wheel').style.transition = 'none';
            }

            // Вращение
            function drag(e) {
                if (!isDragging) return;
                e.preventDefault();
                
                const currentAngle = getAngle(e);
                const delta = currentAngle - lastAngle;
                
                // Нормализуем угол
                let normalizedDelta = delta;
                if (normalizedDelta > 180) normalizedDelta -= 360;
                if (normalizedDelta < -180) normalizedDelta += 360;
                
                currentRotation += normalizedDelta;
                document.getElementById('wheel').style.transform = `rotate(${currentRotation}deg)`;
                
                // Вычисляем скорость
                const now = Date.now();
                const dt = now - lastTime;
                if (dt > 0) {
                    velocity = normalizedDelta / dt;
                }
                
                lastAngle = currentAngle;
                lastTime = now;
                
                updateSelectedIdea();
            }

            // Конец вращения
            function endDrag() {
                if (!isDragging) return;
                isDragging = false;
                
                // Инерция
                if (Math.abs(velocity) > 0.1) {
                    applyInertia();
                }
            }

            // Применяем инерцию
            function applyInertia() {
                const friction = 0.95;
                
                function animate() {
                    velocity *= friction;
                    currentRotation += velocity * 16;
                    document.getElementById('wheel').style.transform = `rotate(${currentRotation}deg)`;
                    
                    updateSelectedIdea();
                    
                    if (Math.abs(velocity) > 0.01) {
                        animationId = requestAnimationFrame(animate);
                    }
                }
                
                animationId = requestAnimationFrame(animate);
            }

            // Обновляем выбранную идею
            function updateSelectedIdea() {
                const segmentAngle = 360 / allIdeas.length;
                const normalizedRotation = ((currentRotation % 360) + 360) % 360;
                const index = Math.floor((360 - normalizedRotation + segmentAngle / 2) / segmentAngle) % allIdeas.length;
                const selectedIdea = allIdeas[index];
                
                document.getElementById('selectedIdea').textContent = `${selectedIdea.name}`;
                document.getElementById('selectedIdea').style.background = selectedIdea.color;
            }

            // Обработчики событий
            const wheel = document.getElementById('wheel');
            wheel.addEventListener('mousedown', startDrag);
            wheel.addEventListener('mousemove', drag);
            wheel.addEventListener('mouseup', endDrag);
            wheel.addEventListener('mouseleave', endDrag);
            
            wheel.addEventListener('touchstart', startDrag);
            wheel.addEventListener('touchmove', drag);
            wheel.addEventListener('touchend', endDrag);

            function quickAction(id) {
                const idea = allIdeas.find(i => i.id === id);
                document.getElementById('searchInput').value = idea.name;
                addToHistory(idea.name);
            }

            async function handleSearch() {
                const input = document.getElementById('searchInput');
                const query = input.value.trim();
                if (!query) return;

                addToHistory(query);
                alert('Поиск: ' + query);
            }

            function addToHistory(query) {
                const historyList = document.getElementById('historyList');
                const time = new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'});
                
                if (historyList.children.length === 1 && historyList.children[0].textContent.includes('История пуста')) {
                    historyList.innerHTML = '';
                }
                
                const item = document.createElement('div');
                item.className = 'history-item';
                item.innerHTML = `<div>${query}</div><div class="history-time">${time}</div>`;
                item.onclick = () => { document.getElementById('searchInput').value = query; };
                
                historyList.insertBefore(item, historyList.firstChild);
                
                if (historyList.children.length > 20) {
                    historyList.removeChild(historyList.lastChild);
                }
            }

            function clearHistory() {
                document.getElementById('historyList').innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">История пуста</div>';
            }

            function toggleTheme() {
                document.body.classList.toggle('dark-theme');
                const isDark = document.body.classList.contains('dark-theme');
                document.querySelector('.theme-toggle').textContent = isDark ? '☀️' : '🌙';
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
            }

            if (localStorage.getItem('theme') === 'dark') {
                document.body.classList.add('dark-theme');
                document.querySelector('.theme-toggle').textContent = '☀️';
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
