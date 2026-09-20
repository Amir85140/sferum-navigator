from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
from services import PlannerService, AIService

app = FastAPI(title="Sferum Navigator", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    feature_id: str = "general"

class PlanRequest(BaseModel):
    time: int
    subjects: List[str]

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Sferum Navigator</title>
        <style>
            :root {
                /* Светлая тема (стиль MAX) */
                --bg-color: #F0F2F5;
                --header-bg: #FFFFFF;
                --text-color: #000000;
                --text-secondary: #818C99;
                --card-bg: #FFFFFF;
                --primary-color: #0077FF;
                --primary-hover: #005bb5;
                --user-msg-bg: #CCE4FF;
                --user-msg-text: #000000;
                --bot-msg-bg: #FFFFFF;
                --bot-msg-text: #000000;
                --border-color: #E1E3E6;
                --input-bg: #F0F2F5;
                --shadow: 0 1px 2px rgba(0,0,0,0.08);
            }

            body.dark-theme {
                /* Тёмная тема */
                --bg-color: #121212;
                --header-bg: #1C1C1E;
                --text-color: #FFFFFF;
                --text-secondary: #8E8E93;
                --card-bg: #1C1C1E;
                --primary-color: #71AAEB;
                --primary-hover: #5A92D6;
                --user-msg-bg: #2B5278;
                --user-msg-text: #FFFFFF;
                --bot-msg-bg: #2C2D2E;
                --bot-msg-text: #FFFFFF;
                --border-color: #2C2D2E;
                --input-bg: #2C2D2E;
                --shadow: 0 1px 2px rgba(0,0,0,0.3);
            }

            * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
                background: var(--bg-color);
                color: var(--text-color);
                min-height: 100vh;
                transition: background 0.3s, color 0.3s;
            }

            /* Шапка в стиле MAX */
            .header {
                position: sticky;
                top: 0;
                background: var(--header-bg);
                padding: 12px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border-color);
                z-index: 100;
                box-shadow: var(--shadow);
            }
            .header-title {
                font-size: 18px;
                font-weight: 600;
            }
            .theme-toggle {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 5px;
                color: var(--text-color);
            }

            /* Контейнер как мобильное приложение */
            .app-container {
                max-width: 480px;
                margin: 0 auto;
                padding: 16px;
                min-height: calc(100vh - 57px);
            }

            /* Сетка идей */
            .ideas-grid {
                display: grid;
                grid-template-columns: 1fr;
                gap: 12px;
            }
            .idea-card {
                background: var(--card-bg);
                border-radius: 12px;
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
                box-shadow: var(--shadow);
                cursor: pointer;
                transition: transform 0.1s;
            }
            .idea-card:active { transform: scale(0.98); }
            .idea-icon { font-size: 28px; }
            .idea-info { flex: 1; }
            .idea-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
            .idea-desc { font-size: 13px; color: var(--text-secondary); }
            .idea-arrow { color: var(--text-secondary); font-size: 20px; }

            /* Экран функции (чат) */
            .feature-screen { display: none; flex-direction: column; height: calc(100vh - 57px); }
            .feature-screen.active { display: flex; }
            
            .chat-header {
                display: flex;
                align-items: center;
                gap: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid var(--border-color);
                margin-bottom: 12px;
            }
            .back-btn {
                background: none;
                border: none;
                font-size: 24px;
                color: var(--primary-color);
                cursor: pointer;
            }

            .chat-box { 
                flex: 1;
                overflow-y: auto; 
                padding: 10px 0;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .message { 
                padding: 10px 14px; 
                border-radius: 18px; 
                max-width: 80%; 
                font-size: 15px;
                line-height: 1.4;
                word-wrap: break-word;
            }
            .bot { 
                background: var(--bot-msg-bg); 
                color: var(--bot-msg-text);
                align-self: flex-start;
                border-bottom-left-radius: 4px;
            }
            .user { 
                background: var(--user-msg-bg); 
                color: var(--user-msg-text);
                align-self: flex-end;
                border-bottom-right-radius: 4px;
            }

            .input-area {
                display: flex;
                gap: 8px;
                padding-top: 12px;
                border-top: 1px solid var(--border-color);
            }
            .chat-input {
                flex: 1;
                padding: 12px 16px;
                border-radius: 20px;
                border: none;
                background: var(--input-bg);
                color: var(--text-color);
                font-size: 15px;
                outline: none;
            }
            .send-btn {
                background: var(--primary-color);
                color: white;
                border: none;
                border-radius: 50%;
                width: 44px;
                height: 44px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                cursor: pointer;
                flex-shrink: 0;
            }
            .send-btn:active { background: var(--primary-hover); }
            
            .hidden { display: none !important; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-title" id="headerTitle">Sferum Navigator</div>
            <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()">🌙</button>
        </div>

        <div class="app-container">
            <!-- Главная сетка -->
            <div id="ideasGrid" class="ideas-grid"></div>

            <!-- Экраны функций -->
            <div id="featureScreens"></div>
        </div>

        <script>
            // Темы
            function toggleTheme() {
                document.body.classList.toggle('dark-theme');
                const isDark = document.body.classList.contains('dark-theme');
                document.getElementById('themeToggle').textContent = isDark ? '☀️' : '🌙';
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
            }

            // Загрузка темы
            if (localStorage.getItem('theme') === 'dark') {
                document.body.classList.add('dark-theme');
                document.getElementById('themeToggle').textContent = '☀️';
            }

            const ideas = [
                { id: 'planner', icon: '', title: 'Умный планировщик', desc: 'Составление расписания' },
                { id: 'homework', icon: '📝', title: 'Помощь с ДЗ', desc: 'Метод Сократа' },
                { id: 'explain', icon: '🎓', title: 'Объяснение тем', desc: 'Контекстный ИИ' },
                { id: 'videos', icon: '🎥', title: 'Видеоуроки', desc: 'RuTube и VK Видео' },
                { id: 'tests', icon: '✅', title: 'Тесты', desc: 'Проверка знаний' },
                { id: 'motivation', icon: '💪', title: 'Мотивация', desc: 'Поддержка и советы' },
                { id: 'progress', icon: '📊', title: 'Прогресс', desc: 'Статистика обучения' },
                { id: 'deadlines', icon: '', title: 'Дедлайны', desc: 'Напоминания' },
                { id: 'adaptive', icon: '🎯', title: 'Адаптивность', desc: 'Подстройка под темп' },
                { id: 'group', icon: '👥', title: 'Групповая работа', desc: 'Совместное обучение' },
                { id: 'journal', icon: '📚', title: 'Интеграция с журналом', desc: 'Синхронизация оценок' },
                { id: 'gamification', icon: '', title: 'Геймификация', desc: 'Достижения и баллы' },
                { id: 'personalization', icon: '', title: 'Персонализация', desc: 'Рекомендации' },
                { id: 'offline', icon: '📱', title: 'Оффлайн режим', desc: 'Работа без интернета' },
                { id: 'export', icon: '📤', title: 'Экспорт данных', desc: 'Выгрузка результатов' }
            ];

            function renderGrid() {
                document.getElementById('ideasGrid').innerHTML = ideas.map(idea => `
                    <div class="idea-card" onclick="openFeature('${idea.id}')">
                        <div class="idea-icon">${idea.icon}</div>
                        <div class="idea-info">
                            <div class="idea-title">${idea.title}</div>
                            <div class="idea-desc">${idea.desc}</div>
                        </div>
                        <div class="idea-arrow">›</div>
                    </div>
                `).join('');
            }

            function openFeature(id) {
                document.getElementById('ideasGrid').classList.add('hidden');
                document.getElementById('headerTitle').textContent = ideas.find(i => i.id === id).title;
                document.getElementById(`screen-${id}`).classList.add('active');
            }

            function closeFeature(id) {
                document.getElementById(`screen-${id}`).classList.remove('active');
                document.getElementById('ideasGrid').classList.remove('hidden');
                document.getElementById('headerTitle').textContent = 'Sferum Navigator';
            }

            function renderScreens() {
                document.getElementById('featureScreens').innerHTML = ideas.map(idea => `
                    <div id="screen-${idea.id}" class="feature-screen">
                        <div class="chat-header">
                            <button class="back-btn" onclick="closeFeature('${idea.id}')">‹</button>
                            <div style="font-weight:600">${idea.title}</div>
                        </div>
                        <div class="chat-box" id="chat-${idea.id}">
                            <div class="message bot">Привет! Я готов помочь. Напиши свой вопрос.</div>
                        </div>
                        <div class="input-area">
                            <input type="text" class="chat-input" id="input-${idea.id}" placeholder="Напиши сообщение..." onkeypress="if(event.key==='Enter') sendMessage('${idea.id}')">
                            <button class="send-btn" onclick="sendMessage('${idea.id}')"></button>
                        </div>
                    </div>
                `).join('');
            }

            async function sendMessage(id) {
                const input = document.getElementById(`input-${id}`);
                const chat = document.getElementById(`chat-${id}`);
                const text = input.value.trim();
                if (!text) return;

                chat.innerHTML += `<div class="message user">${text}</div>`;
                input.value = '';
                chat.scrollTop = chat.scrollHeight;

                try {
                    const res = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: text, feature_id: id})
                    });
                    const data = await res.json();
                    chat.innerHTML += `<div class="message bot">${data.response}</div>`;
                } catch (e) {
                    chat.innerHTML += `<div class="message bot">Ошибка сети. Попробуй ещё раз.</div>`;
                }
                chat.scrollTop = chat.scrollHeight;
            }

            renderGrid();
            renderScreens();
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
