from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services import PlannerService, AIService

app = FastAPI(title="Sferum Navigator", version="5.0")

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
                --bg-color: #0a0a0a;
                --sidebar-bg: #121212;
                --text-color: #FFFFFF;
                --text-secondary: #8E8E93;
                --primary-color: #FFCC00;
                --border-color: #1E1E1E;
                --card-bg: #1A1A1A;
                --hover-bg: #252525;
            }

            body.light-theme {
                --bg-color: #F0F2F5;
                --sidebar-bg: #FFFFFF;
                --text-color: #000000;
                --text-secondary: #818C99;
                --primary-color: #0077FF;
                --border-color: #E1E3E6;
                --card-bg: #FFFFFF;
                --hover-bg: #F5F6F8;
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
                width: 260px;
                background: var(--sidebar-bg);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .sidebar-header {
                padding: 20px;
                border-bottom: 1px solid var(--border-color);
                font-size: 16px;
                font-weight: 700;
                color: var(--primary-color);
            }

            .history-list {
                flex: 1;
                overflow-y: auto;
                padding: 10px;
            }

            .history-item {
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: background 0.2s;
                color: var(--text-secondary);
            }

            .history-item:hover {
                background: var(--hover-bg);
                color: var(--text-color);
            }

            .history-time {
                font-size: 11px;
                color: var(--text-secondary);
                margin-top: 3px;
                opacity: 0.7;
            }

            .clear-history {
                padding: 12px;
                border-top: 1px solid var(--border-color);
                text-align: center;
                color: var(--text-secondary);
                cursor: pointer;
                font-size: 13px;
            }

            .clear-history:hover {
                color: var(--text-color);
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
                margin-bottom: 40px;
            }

            .search-input {
                width: 100%;
                padding: 18px 60px 18px 24px;
                font-size: 17px;
                border: none;
                border-radius: 16px;
                background: var(--card-bg);
                color: var(--text-color);
                outline: none;
                box-shadow: 0 2px 12px rgba(0,0,0,0.3);
            }

            .search-input::placeholder {
                color: var(--text-secondary);
            }

            .search-button {
                position: absolute;
                right: 8px;
                top: 50%;
                transform: translateY(-50%);
                background: var(--primary-color);
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                color: #000;
                cursor: pointer;
                font-weight: 700;
                font-size: 14px;
            }

            .quick-ideas {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 12px;
                width: 100%;
            }

            .idea-chip {
                padding: 16px;
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 14px;
                text-align: center;
                cursor: pointer;
                transition: all 0.2s;
            }

            .idea-chip:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                border-color: var(--primary-color);
            }

            .idea-chip-icon {
                font-size: 28px;
                margin-bottom: 8px;
            }

            .idea-chip-title {
                font-size: 13px;
                font-weight: 600;
            }

            /* ПРАВАЯ ПАНЕЛЬ - ЛЕНТА ИДЕЙ (как в Яндекс Музыке) */
            .ideas-panel {
                width: 380px;
                background: var(--bg-color);
                border-left: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .ideas-header {
                padding: 24px 20px 16px;
                font-size: 22px;
                font-weight: 800;
                color: var(--primary-color);
            }

            .ideas-subheader {
                padding: 0 20px 16px;
                font-size: 13px;
                color: var(--text-secondary);
            }

            .ideas-list {
                flex: 1;
                overflow-y: auto;
                padding: 0 10px 20px;
            }

            .idea-item {
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 16px 12px;
                border-radius: 16px;
                cursor: pointer;
                transition: all 0.25s;
                margin-bottom: 4px;
            }

            .idea-item:hover {
                background: var(--hover-bg);
                transform: scale(1.02);
            }

            .idea-item:active {
                transform: scale(0.98);
            }

            .idea-item.selected {
                background: var(--hover-bg);
                border: 1px solid var(--primary-color);
            }

            /* Иконка-пазл как в Яндекс Музыке */
            .idea-icon-wrap {
                width: 64px;
                height: 64px;
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                position: relative;
                overflow: hidden;
                box-shadow: 0 4px 16px rgba(0,0,0,0.4);
            }

            .idea-icon-wrap svg {
                width: 40px;
                height: 40px;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
            }

            .idea-info {
                flex: 1;
                min-width: 0;
            }

            .idea-label {
                font-size: 11px;
                color: var(--text-secondary);
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .idea-name {
                font-size: 16px;
                font-weight: 700;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .idea-arrow {
                color: var(--text-secondary);
                font-size: 20px;
                opacity: 0;
                transition: opacity 0.2s;
            }

            .idea-item:hover .idea-arrow {
                opacity: 1;
            }

            /* Выбранная идея внизу */
            .selected-display {
                padding: 16px 20px;
                border-top: 1px solid var(--border-color);
                background: var(--sidebar-bg);
                min-height: 70px;
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .selected-display-icon {
                width: 40px;
                height: 40px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .selected-display-text {
                flex: 1;
            }

            .selected-display-label {
                font-size: 11px;
                color: var(--text-secondary);
            }

            .selected-display-name {
                font-size: 15px;
                font-weight: 700;
            }

            .selected-display-btn {
                padding: 8px 16px;
                background: var(--primary-color);
                color: #000;
                border: none;
                border-radius: 20px;
                font-weight: 700;
                font-size: 13px;
                cursor: pointer;
            }

            .theme-toggle {
                position: fixed;
                top: 16px;
                right: 400px;
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 50%;
                width: 40px;
                height: 40px;
                font-size: 18px;
                cursor: pointer;
                z-index: 100;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .hidden { display: none !important; }

            /* Скроллбар */
            .ideas-list::-webkit-scrollbar,
            .history-list::-webkit-scrollbar {
                width: 6px;
            }
            .ideas-list::-webkit-scrollbar-thumb,
            .history-list::-webkit-scrollbar-thumb {
                background: var(--border-color);
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn">☀️</button>
        
        <div class="container">
            <!-- ЛЕВАЯ ПАНЕЛЬ - ИСТОРИЯ -->
            <div class="sidebar">
                <div class="sidebar-header"> История</div>
                <div class="history-list" id="historyList">
                    <div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                        История пуста
                    </div>
                </div>
                <div class="clear-history" onclick="clearHistory()">
                    🗑 Очистить
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
                            <div class="idea-chip-icon"></div>
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
                            <div class="idea-chip-icon"></div>
                            <div class="idea-chip-title">Видеоуроки</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ПРАВАЯ ПАНЕЛЬ - ЛЕНТА ИДЕЙ -->
            <div class="ideas-panel">
                <div class="ideas-header">Идеи для тебя</div>
                <div class="ideas-subheader">Выбери, что хочешь попробовать</div>
                <div class="ideas-list" id="ideasList"></div>
                <div class="selected-display" id="selectedDisplay">
                    <div class="selected-display-icon" id="selIcon" style="background:#333;"></div>
                    <div class="selected-display-text">
                        <div class="selected-display-label">Выбрано</div>
                        <div class="selected-display-name" id="selName">Ничего не выбрано</div>
                    </div>
                    <button class="selected-display-btn" onclick="useSelected()">Открыть</button>
                </div>
            </div>
        </div>

        <script>
            const allIdeas = [
                { id: 'planner', name: 'Умный планировщик', label: 'Рекомендуем', color: '#FF6B6B', icon: 'puzzle' },
                { id: 'homework', name: 'Помощь с ДЗ', label: 'Метод Сократа', color: '#4ECDC4', icon: 'star' },
                { id: 'explain', name: 'Объяснение тем', label: 'Контекстный ИИ', color: '#45B7D1', icon: 'puzzle' },
                { id: 'tests', name: 'Тесты и проверка', label: 'Проверь себя', color: '#FFA07A', icon: 'star' },
                { id: 'motivation', name: 'Мотивация', label: 'Поддержка', color: '#98D8C8', icon: 'heart' },
                { id: 'videos', name: 'Видеоуроки', label: 'RuTube и VK', color: '#F7DC6F', icon: 'play' },
                { id: 'progress', name: 'Прогресс обучения', label: 'Твоя статистика', color: '#BB8FCE', icon: 'chart' },
                { id: 'deadlines', name: 'Дедлайны', label: 'Не забудь!', color: '#F1948A', icon: 'clock' },
                { id: 'adaptive', name: 'Адаптивное обучение', label: 'Под твой темп', color: '#82E0AA', icon: 'target' },
                { id: 'group', name: 'Групповая работа', label: 'Вместе веселее', color: '#85C1E9', icon: 'people' },
                { id: 'journal', name: 'Интеграция с журналом', label: 'Синхронизация', color: '#F0B27A', icon: 'book' },
                { id: 'gamification', name: 'Геймификация', label: 'Достижения', color: '#D7BDE2', icon: 'trophy' },
                { id: 'personalization', name: 'Персонализация', label: 'Только для тебя', color: '#A9DFBF', icon: 'user' },
                { id: 'offline', name: 'Оффлайн режим', label: 'Без интернета', color: '#FAD7A0', icon: 'download' },
                { id: 'export', name: 'Экспорт данных', label: 'Выгрузка', color: '#AED6F1', icon: 'export' }
            ];

            let selectedIdea = null;

            // SVG иконки (пазлы, звёзды и т.д.)
            const icons = {
                puzzle: `<svg viewBox="0 0 24 24" fill="white"><path d="M20.5 11H19V7c0-1.1-.9-2-2-2h-4V3.5C13 2.12 11.88 1 10.5 1S8 2.12 8 3.5V5H4c-1.1 0-1.99.9-1.99 2v3.8H3.5c1.49 0 2.7 1.21 2.7 2.7s-1.21 2.7-2.7 2.7H2V20c0 1.1.9 2 2 2h3.8v-1.5c0-1.49 1.21-2.7 2.7-2.7s2.7 1.21 2.7 2.7V22H17c1.1 0 2-.9 2-2v-4h1.5c1.38 0 2.5-1.12 2.5-2.5S21.88 11 20.5 11z"/></svg>`,
                star: `<svg viewBox="0 0 24 24" fill="white"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>`,
                heart: `<svg viewBox="0 0 24 24" fill="white"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>`,
                play: `<svg viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>`,
                chart: `<svg viewBox="0 0 24 24" fill="white"><path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/></svg>`,
                clock: `<svg viewBox="0 0 24 24" fill="white"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>`,
                target: `<svg viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5.5-2.5l7.51-3.49L17.5 6.5 9.99 9.99 6.5 17.5zm5.5-6.6c.61 0 1.1.49 1.1 1.1s-.49 1.1-1.1 1.1-1.1-.49-1.1-1.1.49-1.1 1.1-1.1z"/></svg>`,
                people: `<svg viewBox="0 0 24 24" fill="white"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>`,
                book: `<svg viewBox="0 0 24 24" fill="white"><path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/></svg>`,
                trophy: `<svg viewBox="0 0 24 24" fill="white"><path d="M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.55 1.92 4.63 4.39 4.94.63 1.5 1.98 2.63 3.61 2.96V19H7v2h10v-2h-4v-3.1c1.63-.33 2.98-1.46 3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2zM5 8V7h2v3.82C5.84 10.4 5 9.3 5 8zm14 0c0 1.3-.84 2.4-2 2.82V7h2v1z"/></svg>`,
                user: `<svg viewBox="0 0 24 24" fill="white"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`,
                download: `<svg viewBox="0 0 24 24" fill="white"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>`,
                export: `<svg viewBox="0 0 24 24" fill="white"><path d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2v9.67z"/></svg>`
            };

            function renderIdeas() {
                const list = document.getElementById('ideasList');
                list.innerHTML = allIdeas.map(idea => `
                    <div class="idea-item" id="idea-${idea.id}" onclick="selectIdea('${idea.id}')">
                        <div class="idea-icon-wrap" style="background:${idea.color};">
                            ${icons[idea.icon] || icons.puzzle}
                        </div>
                        <div class="idea-info">
                            <div class="idea-label">${idea.label}</div>
                            <div class="idea-name">${idea.name}</div>
                        </div>
                        <div class="idea-arrow">›</div>
                    </div>
                `).join('');
            }

            function selectIdea(id) {
                // Убираем выделение со всех
                document.querySelectorAll('.idea-item').forEach(el => el.classList.remove('selected'));
                
                // Выделяем выбранную
                document.getElementById(`idea-${id}`).classList.add('selected');
                
                selectedIdea = allIdeas.find(i => i.id === id);
                
                // Обновляем нижнюю панель
                document.getElementById('selIcon').style.background = selectedIdea.color;
                document.getElementById('selIcon').innerHTML = icons[selectedIdea.icon] || icons.puzzle;
                document.getElementById('selName').textContent = selectedIdea.name;
            }

            function useSelected() {
                if (!selectedIdea) return;
                document.getElementById('searchInput').value = selectedIdea.name;
                addToHistory(selectedIdea.name);
                handleSearch();
            }

            function quickAction(id) {
                const idea = allIdeas.find(i => i.id === id);
                document.getElementById('searchInput').value = idea.name;
                addToHistory(idea.name);
                selectIdea(id);
            }

            async function handleSearch() {
                const input = document.getElementById('searchInput');
                const query = input.value.trim();
                if (!query) return;

                addToHistory(query);
                
                // Показываем ответ ИИ
                try {
                    const res = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: query})
                    });
                    const data = await res.json();
                    alert(data.response);
                } catch(e) {
                    alert('Ошибка: ' + e.message);
                }
            }

            function addToHistory(query) {
                const list = document.getElementById('historyList');
                const time = new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'});
                
                if (list.children.length === 1 && list.children[0].textContent.includes('История пуста')) {
                    list.innerHTML = '';
                }
                
                const item = document.createElement('div');
                item.className = 'history-item';
                item.innerHTML = `<div>${query}</div><div class="history-time">${time}</div>`;
                item.onclick = () => { document.getElementById('searchInput').value = query; };
                
                list.insertBefore(item, list.firstChild);
                
                if (list.children.length > 30) {
                    list.removeChild(list.lastChild);
                }
            }

            function clearHistory() {
                document.getElementById('historyList').innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">История пуста</div>';
            }

            function toggleTheme() {
                document.body.classList.toggle('light-theme');
                const isLight = document.body.classList.contains('light-theme');
                document.getElementById('themeBtn').textContent = isLight ? '🌙' : '☀️';
                localStorage.setItem('theme', isLight ? 'light' : 'dark');
            }

            if (localStorage.getItem('theme') === 'light') {
                document.body.classList.add('light-theme');
                document.getElementById('themeBtn').textContent = '🌙';
            }

            renderIdeas();
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
