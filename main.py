from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
from services import PlannerService, AIService
import json

app = FastAPI(title="Sferum Navigator", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели данных
class ChatRequest(BaseModel):
    message: str
    feature_id: str = "general"

class PlanRequest(BaseModel):
    time: int
    subjects: List[str]

class TestRequest(BaseModel):
    topic: str
    difficulty: str = "medium"

# Хранилище данных пользователя
user_data = {
    "progress": {},
    "achievements": [],
    "deadlines": [],
    "study_stats": {
        "total_time": 0,
        "tasks_completed": 0,
        "tests_passed": 0
    }
}

# Главная страница с навигацией по 15 идеям
@app.get("/", response_class=HTMLResponse)
async def main_page():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sferum Navigator - 15 идей</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 30px;
                padding: 20px;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            .ideas-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .idea-card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s, box-shadow 0.3s;
                cursor: pointer;
                position: relative;
                overflow: hidden;
            }
            .idea-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0,0,0,0.3);
            }
            .idea-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 5px;
                background: linear-gradient(90deg, #667eea, #764ba2);
            }
            .idea-number {
                position: absolute;
                top: 15px;
                right: 15px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 1.2em;
            }
            .idea-icon {
                font-size: 3em;
                margin-bottom: 15px;
            }
            .idea-title {
                font-size: 1.3em;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
            .idea-description {
                color: #666;
                font-size: 0.95em;
                line-height: 1.5;
            }
            .idea-button {
                margin-top: 15px;
                padding: 12px 20px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1em;
                font-weight: bold;
                width: 100%;
                transition: opacity 0.3s;
            }
            .idea-button:hover {
                opacity: 0.9;
            }
            .feature-section {
                display: none;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                margin-bottom: 20px;
            }
            .feature-section.active {
                display: block;
            }
            .back-button {
                padding: 12px 25px;
                background: #666;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                margin-bottom: 20px;
                font-size: 1em;
            }
            .back-button:hover {
                background: #555;
            }
            .chat-box { 
                height: 400px; 
                overflow-y: auto; 
                border: 2px solid #e0e0e0; 
                border-radius: 10px; 
                padding: 15px; 
                margin-bottom: 15px; 
                background: #fafafa; 
            }
            .message { 
                margin: 10px 0; 
                padding: 12px 15px; 
                border-radius: 10px; 
                max-width: 85%; 
                word-wrap: break-word;
                animation: fadeIn 0.3s;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .bot { 
                background: #e3f2fd; 
                color: #333;
                border-left: 4px solid #2196F3;
            }
            .user { 
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white; 
                margin-left: auto; 
                text-align: right;
                border-right: 4px solid #764ba2;
            }
            input, button, textarea, select { 
                width: 100%; 
                padding: 12px; 
                margin: 5px 0; 
                border-radius: 8px; 
                border: 2px solid #e0e0e0; 
                box-sizing: border-box; 
                font-size: 16px; 
                font-family: inherit;
            }
            input:focus, textarea:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            button { 
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white; 
                border: none; 
                cursor: pointer; 
                font-weight: bold;
                transition: transform 0.2s, opacity 0.2s;
            }
            button:hover {
                transform: scale(1.02);
                opacity: 0.9;
            }
            button:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-number {
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .stat-label {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .achievement {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
            }
            .deadline {
                background: #f8d7da;
                border-left: 4px solid #dc3545;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
            }
            .loading {
                text-align: center;
                padding: 20px;
                color: #666;
            }
            .hidden {
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Sferum Navigator</h1>
                <p>15 идей для улучшения обучения с ИИ</p>
            </div>

            <!-- Главная сетка с 15 идеями -->
            <div id="ideasGrid" class="ideas-grid">
                <!-- Карточки генерируются JavaScript -->
            </div>

            <!-- Секции для каждой идеи -->
            <div id="featureSections"></div>
        </div>

        <script>
            // Данные о 15 идеях
            const ideas = [
                {
                    id: 'planner',
                    number: 1,
                    icon: '',
                    title: 'Умный планировщик',
                    description: 'Составление оптимального расписания с учетом сложности предметов и свободного времени',
                    buttonText: 'Составить план'
                },
                {
                    id: 'homework',
                    number: 2,
                    icon: '📝',
                    title: 'Помощь с ДЗ (метод Сократа)',
                    description: 'ИИ помогает разобраться с домашкой, задавая наводящие вопросы вместо готовых ответов',
                    buttonText: 'Помочь с ДЗ'
                },
                {
                    id: 'explain',
                    number: 3,
                    icon: '🎓',
                    title: 'Объяснение тем',
                    description: 'Контекстный ИИ объясняет сложные темы простым языком, помня что вы смотрели',
                    buttonText: 'Объяснить тему'
                },
                {
                    id: 'videos',
                    number: 4,
                    icon: '🎥',
                    title: 'Видеоуроки',
                    description: 'Интеграция с RuTube и VK Видео - рекомендации по темам',
                    buttonText: 'Найти видео'
                },
                {
                    id: 'tests',
                    number: 5,
                    icon: '✅',
                    title: 'Тесты и проверка знаний',
                    description: 'Генерация тестов по любой теме для проверки понимания',
                    buttonText: 'Пройти тест'
                },
                {
                    id: 'motivation',
                    number: 6,
                    icon: '',
                    title: 'Мотивация и поддержка',
                    description: 'Эмоциональная поддержка, советы по преодолению прокрастинации',
                    buttonText: 'Получить мотивацию'
                },
                {
                    id: 'progress',
                    number: 7,
                    icon: '',
                    title: 'Прогресс обучения',
                    description: 'Отслеживание статистики, времени обучения и выполненных задач',
                    buttonText: 'Посмотреть прогресс'
                },
                {
                    id: 'deadlines',
                    number: 8,
                    icon: '⏰',
                    title: 'Дедлайны',
                    description: 'Напоминания о контрольных, домашних заданиях и важных датах',
                    buttonText: 'Управление дедлайнами'
                },
                {
                    id: 'adaptive',
                    number: 9,
                    icon: '🎯',
                    title: 'Адаптивное обучение',
                    description: 'Подстройка под ваш темп и стиль обучения',
                    buttonText: 'Настроить обучение'
                },
                {
                    id: 'group',
                    number: 10,
                    icon: '',
                    title: 'Групповая работа',
                    description: 'Совместное обучение, обмен материалами с одноклассниками',
                    buttonText: 'Групповая работа'
                },
                {
                    id: 'journal',
                    number: 11,
                    icon: '📚',
                    title: 'Интеграция с журналом',
                    description: 'Синхронизация с электронным журналом школы',
                    buttonText: 'Подключить журнал'
                },
                {
                    id: 'gamification',
                    number: 12,
                    icon: '',
                    title: 'Геймификация',
                    description: 'Достижения, баллы, уровни и рейтинги для мотивации',
                    buttonText: 'Мои достижения'
                },
                {
                    id: 'personalization',
                    number: 13,
                    icon: '🎨',
                    title: 'Персонализация',
                    description: 'Рекомендации контента под ваши интересы и цели',
                    buttonText: 'Настроить профиль'
                },
                {
                    id: 'offline',
                    number: 14,
                    icon: '📱',
                    title: 'Оффлайн режим',
                    description: 'Работа без интернета, скачивание материалов',
                    buttonText: 'Оффлайн материалы'
                },
                {
                    id: 'export',
                    number: 15,
                    icon: '📤',
                    title: 'Экспорт данных',
                    description: 'Выгрузка статистики, отчетов и результатов обучения',
                    buttonText: 'Экспортировать'
                }
            ];

            // Генерация карточек идей
            function renderIdeasGrid() {
                const grid = document.getElementById('ideasGrid');
                grid.innerHTML = ideas.map(idea => `
                    <div class="idea-card" onclick="showFeature('${idea.id}')">
                        <div class="idea-number">${idea.number}</div>
                        <div class="idea-icon">${idea.icon}</div>
                        <div class="idea-title">${idea.title}</div>
                        <div class="idea-description">${idea.description}</div>
                        <button class="idea-button" onclick="event.stopPropagation(); showFeature('${idea.id}')">
                            ${idea.buttonText}
                        </button>
                    </div>
                `).join('');
            }

            // Генерация секций для каждой идеи
            function renderFeatureSections() {
                const container = document.getElementById('featureSections');
                container.innerHTML = ideas.map(idea => `
                    <div id="section-${idea.id}" class="feature-section">
                        <button class="back-button" onclick="backToGrid()">← Назад к идеям</button>
                        <h2>${idea.icon} ${idea.title}</h2>
                        <p style="margin: 15px 0; color: #666;">${idea.description}</p>
                        ${getFeatureContent(idea.id)}
                    </div>
                `).join('');
            }

            // Контент для каждой секции
            function getFeatureContent(featureId) {
                const contents = {
                    planner: `
                        <div class="chat-box" id="chat-planner">
                            <div class="message bot">Привет! Я помогу составить оптимальное расписание. Сколько минут у тебя есть на учёбу сегодня?</div>
                        </div>
                        <input type="text" id="input-planner" placeholder="Например: 60 минут, математика и русский" onkeypress="if(event.key==='Enter') handlePlanner()">
                        <button onclick="handlePlanner()">Составить план</button>
                    `,
                    homework: `
                        <div class="chat-box" id="chat-homework">
                            <div class="message bot">Я не дам готовый ответ, но помогу разобраться! Напиши условие задачи или тему, с которой нужна помощь.</div>
                        </div>
                        <input type="text" id="input-homework" placeholder="Опиши задачу или тему..." onkeypress="if(event.key==='Enter') handleHomework()">
                        <button onclick="handleHomework()">Помочь с ДЗ</button>
                    `,
                    explain: `
                        <div class="chat-box" id="chat-explain">
                            <div class="message bot">Какую тему нужно объяснить? Напиши предмет и тему, например: "Математика, квадратные уравнения"</div>
                        </div>
                        <input type="text" id="input-explain" placeholder="Предмет, тема..." onkeypress="if(event.key==='Enter') handleExplain()">
                        <button onclick="handleExplain()">Объяснить</button>
                    `,
                    videos: `
                        <div class="chat-box" id="chat-videos">
                            <div class="message bot">По какой теме найти видеоуроки? Я подберу лучшие материалы с RuTube и VK Видео.</div>
                        </div>
                        <input type="text" id="input-videos" placeholder="Тема для поиска видео..." onkeypress="if(event.key==='Enter') handleVideos()">
                        <button onclick="handleVideos()">Найти видео</button>
                    `,
                    tests: `
                        <div class="chat-box" id="chat-tests">
                            <div class="message bot">Давай проверим знания! По какой теме хочешь тест? Выбери сложность: легкая, средняя или сложная.</div>
                        </div>
                        <select id="difficulty-tests">
                            <option value="easy">Легкий</option>
                            <option value="medium">Средний</option>
                            <option value="hard">Сложный</option>
                        </select>
                        <input type="text" id="input-tests" placeholder="Тема для теста..." onkeypress="if(event.key==='Enter') handleTests()">
                        <button onclick="handleTests()">Сгенерировать тест</button>
                    `,
                    motivation: `
                        <div class="chat-box" id="chat-motivation">
                            <div class="message bot">Я здесь, чтобы поддержать тебя! Расскажи, что тебя беспокоит или просто напиши "нужна мотивация".</div>
                        </div>
                        <input type="text" id="input-motivation" placeholder="Как себя чувствуешь?..." onkeypress="if(event.key==='Enter') handleMotivation()">
                        <button onclick="handleMotivation()">Получить поддержку</button>
                    `,
                    progress: `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-number" id="stat-time">0</div>
                                <div class="stat-label">Часов обучения</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="stat-tasks">0</div>
                                <div class="stat-label">Задач выполнено</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="stat-tests">0</div>
                                <div class="stat-label">Тестов пройдено</div>
                            </div>
                        </div>
                        <div class="chat-box" id="chat-progress">
                            <div class="message bot">Твой прогресс обновляется автоматически. Продолжай учиться!</div>
                        </div>
                    `,
                    deadlines: `
                        <div class="chat-box" id="chat-deadlines">
                            <div class="message bot">Добавь дедлайн: напиши дату и задачу, например: "15 декабря - контрольная по математике"</div>
                        </div>
                        <input type="text" id="input-deadlines" placeholder="Дата - задача..." onkeypress="if(event.key==='Enter') handleDeadlines()">
                        <button onclick="handleDeadlines()">Добавить дедлайн</button>
                        <div id="deadlines-list"></div>
                    `,
                    adaptive: `
                        <div class="chat-box" id="chat-adaptive">
                            <div class="message bot">Давай настроим обучение под тебя! Какой у тебя стиль обучения: визуал (люблю схемы), аудиал (люблю слушать) или кинестетик (люблю практиковать)?</div>
                        </div>
                        <input type="text" id="input-adaptive" placeholder="Опиши свой стиль..." onkeypress="if(event.key==='Enter') handleAdaptive()">
                        <button onclick="handleAdaptive()">Настроить</button>
                    `,
                    group: `
                        <div class="chat-box" id="chat-group">
                            <div class="message bot">Групповая работа помогает учиться лучше! Создай учебную группу или присоединись к существующей.</div>
                        </div>
                        <button onclick="alert('Функция создания группы (демо)')">Создать группу</button>
                        <button onclick="alert('Функция поиска группы (демо)')">Найти группу</button>
                    `,
                    journal: `
                        <div class="chat-box" id="chat-journal">
                            <div class="message bot">Подключи электронный журнал школы для автоматической синхронизации оценок и домашних заданий.</div>
                        </div>
                        <button onclick="alert('Интеграция с журналом (демо)')">Подключить журнал</button>
                    `,
                    gamification: `
                        <div class="chat-box" id="chat-gamification">
                            <div class="message bot">Твои достижения:</div>
                        </div>
                        <div id="achievements-list">
                            <div class="achievement"> Первый шаг - начал обучение</div>
                            <div class="achievement">📚 10 часов обучения</div>
                            <div class="achievement">✅ 5 выполненных тестов</div>
                        </div>
                    `,
                    personalization: `
                        <div class="chat-box" id="chat-personalization">
                            <div class="message bot">Расскажи о своих целях в обучении. Что хочешь улучшить? Какие предметы самые важные?</div>
                        </div>
                        <input type="text" id="input-personalization" placeholder="Мои цели..." onkeypress="if(event.key==='Enter') handlePersonalization()">
                        <button onclick="handlePersonalization()">Сохранить профиль</button>
                    `,
                    offline: `
                        <div class="chat-box" id="chat-offline">
                            <div class="message bot">Скачай материалы для работы оффлайн. Выбери тему для загрузки.</div>
                        </div>
                        <button onclick="alert('Скачивание материалов (демо)')">Скачать математику</button>
                        <button onclick="alert('Скачивание материалов (демо)')">Скачать русский язык</button>
                        <button onclick="alert('Скачивание материалов (демо)')">Скачать физику</button>
                    `,
                    export: `
                        <div class="chat-box" id="chat-export">
                            <div class="message bot">Экспортируй свои данные: статистику обучения, пройденные тесты, достижения.</div>
                        </div>
                        <button onclick="alert('Экспорт в PDF (демо)')">Экспорт в PDF</button>
                        <button onclick="alert('Экспорт в Excel (демо)')">Экспорт в Excel</button>
                        <button onclick="alert('Экспорт в JSON (демо)')">Экспорт в JSON</button>
                    `
                };
                return contents[featureId] || '<p>Функция в разработке</p>';
            }

            // Показать секцию идеи
            function showFeature(featureId) {
                document.getElementById('ideasGrid').style.display = 'none';
                document.querySelectorAll('.feature-section').forEach(section => {
                    section.classList.remove('active');
                });
                document.getElementById(`section-${featureId}`).classList.add('active');
            }

            // Вернуться к сетке идей
            function backToGrid() {
                document.getElementById('ideasGrid').style.display = 'grid';
                document.querySelectorAll('.feature-section').forEach(section => {
                    section.classList.remove('active');
                });
            }

            // Обработчики для каждой функции
            async function handlePlanner() {
                const input = document.getElementById('input-planner');
                const chat = document.getElementById('chat-planner');
                const text = input.value.trim();
                if (!text) return;

                chat.innerHTML += `<div class="message user">${text}</div>`;
                input.value = '';

                try {
                    const response = await fetch('/api/plan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({time: 60, subjects: ['Математика', 'Русский']})
                    });
                    const data = await response.json();
                    let planText = '📅 Вот твой план:\\n';
                    data.schedule.forEach(item => {
                        planText += `• ${item.subject}: ${item.time_allocated}\\n`;
                    });
                    chat.innerHTML += `<div class="message bot">${planText}</div>`;
                } catch (error) {
                    chat.innerHTML += `<div class="message bot">Ошибка: ${error.message}</div>`;
                }
                chat.scrollTop = chat.scrollHeight;
            }

            async function handleHomework() {
                await handleChat('homework', 'homework');
            }

            async function handleExplain() {
                await handleChat('explain', 'explain');
            }

            async function handleVideos() {
                const chat = document.getElementById('chat-videos');
                const input = document.getElementById('input-videos');
                const text = input.value.trim();
                if (!text) return;

                chat.innerHTML += `<div class="message user">${text}</div>`;
                input.value = '';

                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: `Найди видеоуроки по теме: ${text}`, feature_id: 'videos'})
                });
                const data = await response.json();
                chat.innerHTML += `<div class="message bot">${data.response}\\n\\n🎥 Рекомендую посмотреть видео на RuTube и VK Видео по этой теме.</div>`;
                chat.scrollTop = chat.scrollHeight;
            }

            async function handleTests() {
                const chat = document.getElementById('chat-tests');
                const input = document.getElementById('input-tests');
                const difficulty = document.getElementById('difficulty-tests').value;
                const text = input.value.trim();
                if (!text) return;

                chat.innerHTML += `<div class="message user">${text} (${difficulty})</div>`;
                input.value = '';

                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: `Сгенерируй тест по теме: ${text}, сложность: ${difficulty}`, feature_id: 'tests'})
                });
                const data = await response.json();
                chat.innerHTML += `<div class="message bot">${data.response}</div>`;
                chat.scrollTop = chat.scrollHeight;
            }

            async function handleMotivation() {
                await handleChat('motivation', 'motivation');
            }

            function handleProgress() {
                // Обновление статистики
                document.getElementById('stat-time').textContent = '12';
                document.getElementById('stat-tasks').textContent = '25';
                document.getElementById('stat-tests').textContent = '8';
            }

            function handleDeadlines() {
                const chat = document.getElementById('chat-deadlines');
                const input = document.getElementById('input-deadlines');
                const text = input.value.trim();
                if (!text) return;

                chat.innerHTML += `<div class="message user">${text}</div>`;
                input.value = '';
                chat.innerHTML += `<div class="message bot">✅ Дедлайн добавлен! Я напомню тебе.</div>`;
                
                const list = document.getElementById('deadlines-list');
                list.innerHTML += `<div class="deadline">📌 ${text}</div>`;
                chat.scrollTop = chat.scrollHeight;
            }

            async function handleAdaptive() {
                await handleChat('adaptive', 'adaptive');
            }

            function handleGroup() {
                alert('Функция групповой работы (демо)');
            }

            function handleJournal() {
                alert('Интеграция с журналом (демо)');
            }

            function handleGamification() {
                // Показ достижений
            }

            async function handlePersonalization() {
                await handleChat('personalization', 'personalization');
            }

            function handleOffline() {
                alert('Оффлайн режим (демо)');
            }

            function handleExport() {
                alert('Экспорт данных (демо)');
            }

            // Универсальная функция для чата
            async function handleChat(featureId, endpoint) {
                const input = document.getElementById(`input-${featureId}`);
                const chat = document.getElementById(`chat-${featureId}`);
                const text = input.value.trim();
                if (!text) return;

                chat.innerHTML += `<div class="message user">${text}</div>`;
                input.value = '';
                chat.innerHTML += `<div class="message bot">⏳ Думаю...</div>`;
                chat.scrollTop = chat.scrollHeight;

                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: text, feature_id: endpoint})
                    });
                    const data = await response.json();
                    
                    // Удаляем "Думаю..."
                    const loadingMsg = chat.querySelector('.message.bot:last-child');
                    if (loadingMsg && loadingMsg.textContent.includes('Думаю')) {
                        chat.removeChild(loadingMsg);
                    }
                    
                    chat.innerHTML += `<div class="message bot">${data.response}</div>`;
                } catch (error) {
                    const loadingMsg = chat.querySelector('.message.bot:last-child');
                    if (loadingMsg && loadingMsg.textContent.includes('Думаю')) {
                        chat.removeChild(loadingMsg);
                    }
                    chat.innerHTML += `<div class="message bot">Ошибка: ${error.message}</div>`;
                }
                chat.scrollTop = chat.scrollHeight;
            }

            // Инициализация
            renderIdeasGrid();
            renderFeatureSections();
            handleProgress();
        </script>
    </body>
    </html>
    """

# API эндпоинты
@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = AIService.process_message(request.message)
    return {"response": response}

@app.post("/api/plan")
async def get_plan(request: PlanRequest):
    return PlannerService.generate_plan(request.time, request.subjects)

@app.post("/api/test")
async def generate_test(request: TestRequest):
    # Генерация теста (заглушка)
    return {"questions": [], "topic": request.topic}

@app.get("/api/progress")
async def get_progress():
    return user_data["study_stats"]

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Sferum Navigator", "features": 15}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
