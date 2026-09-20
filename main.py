from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
from services import AIService

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    chat_id: str
    feature_id: str = "general"

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sferum Navigator</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);height:100vh;overflow:hidden;color:#fff}
.container{display:flex;height:100vh;padding:20px;gap:20px}
.panel{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:20px;padding:20px;border:1px solid rgba(255,255,255,0.2);display:flex;flex-direction:column;overflow:hidden}
.panel-title{font-size:20px;font-weight:700;margin-bottom:15px;flex-shrink:0;display:flex;align-items:center;justify-content:space-between}
.scrollable{flex:1;overflow-y:auto;padding-right:5px}
.history-panel{width:280px}
.main-panel{flex:1}
.chat-container{flex:1;overflow-y:auto;background:rgba(0,0,0,0.3);border-radius:15px;padding:15px;margin-bottom:15px}
.input-area{flex-shrink:0;display:flex;gap:10px}
.input-area input{flex:1;padding:14px 18px;border:none;border-radius:12px;background:rgba(255,255,255,0.2);color:#fff;font-size:16px}
.input-area input:focus{outline:none;background:rgba(255,255,255,0.3)}
.input-area button{padding:14px 28px;background:#ffdb4d;color:#000;border:none;border-radius:12px;font-weight:700;cursor:pointer}
.ideas-panel{width:320px}
.ideas-grid{display:flex;flex-direction:column;gap:10px}
.idea-card{background:rgba(255,255,255,0.15);border-radius:12px;padding:12px;cursor:pointer;transition:all 0.2s;border:2px solid transparent;display:flex;align-items:center;gap:10px;flex-shrink:0}
.idea-card:hover{background:rgba(255,255,255,0.25);transform:translateX(5px)}
.idea-card.selected{background:rgba(255,219,77,0.3);border-color:#ffdb4d}
.idea-icon{font-size:24px;flex-shrink:0}
.idea-name{font-size:14px;font-weight:600}
.message{margin-bottom:12px;padding:12px 16px;border-radius:12px;max-width:80%;animation:slideIn 0.3s;white-space:pre-wrap;word-wrap:break-word}
@keyframes slideIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.user-msg{background:linear-gradient(135deg,#667eea,#764ba2);margin-left:auto;text-align:right}
.bot-msg{background:rgba(255,255,255,0.2)}
.status-bar{background:rgba(255,219,77,0.2);border:2px solid #ffdb4d;border-radius:12px;padding:12px 18px;margin-bottom:15px;font-weight:600;flex-shrink:0}
.chat-item{background:rgba(255,255,255,0.1);padding:10px;border-radius:8px;margin-bottom:6px;cursor:pointer;transition:all 0.2s;flex-shrink:0}
.chat-item:hover{background:rgba(255,255,255,0.2)}
.chat-item.active{background:rgba(255,219,77,0.3);border-left:3px solid #ffdb4d}
.chat-title{font-size:13px;margin-bottom:3px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chat-time{font-size:11px;opacity:0.7}
.empty-state{text-align:center;padding:30px 20px;opacity:0.6}
.new-chat-btn{width:100%;padding:10px;background:rgba(255,219,77,0.3);color:#fff;border:2px solid #ffdb4d;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;margin-bottom:10px;transition:.2s}
.new-chat-btn:hover{background:rgba(255,219,77,0.5)}
.search-box{margin-bottom:10px}
.search-box input{width:100%;padding:8px 12px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;font-size:13px;outline:none}
.search-box input:focus{border-color:#ffdb4d}
.project-btn{width:100%;padding:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid rgba(255,255,255,0.2);border-radius:8px;cursor:pointer;font-size:13px;margin-bottom:6px;transition:.2s;display:flex;align-items:center;gap:8px}
.project-btn:hover{background:rgba(255,255,255,0.2)}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:rgba(255,255,255,0.1);border-radius:3px}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.3);border-radius:3px}
</style>
</head>
<body>
<div class="container">
<div class="panel history-panel">
<div class="panel-title"><span>📜 Чаты</span></div>
<button class="new-chat-btn" onclick="newChat()">+ Новый чат</button>
<div class="search-box">
<input type="text" placeholder="Поиск чатов..." id="searchInput" oninput="filterChats()">
</div>
<div class="scrollable" id="chatsList">
<div class="empty-state">Нет чатов</div>
</div>
<div style="margin-top:10px;flex-shrink:0">
<button class="project-btn" onclick="alert('Синхронизация с МЭШ (демо)')"> МЭШ</button>
<button class="project-btn" onclick="alert('Сообщество (демо)')">👥 Сообщество</button>
<button class="project-btn" onclick="alert('Coder (демо)')">💻 Coder</button>
<button class="project-btn" onclick="alert('Новый проект (демо)')">🚀 Новый проект</button>
</div>
</div>
<div class="panel main-panel">
<div class="status-bar" id="statusBar">
<span>🎯</span>
<span id="statusText">Режим: Общий помощник</span>
</div>
<div class="chat-container" id="chatBox">
<div class="message bot-msg">Привет! Выбери режим справа и задай вопрос.</div>
</div>
<div class="input-area">
<input type="text" id="messageInput" placeholder="Напиши свой вопрос..." onkeypress="if(event.key==='Enter')sendMessage()">
<button onclick="sendMessage()">Отправить</button>
</div>
</div>
<div class="panel ideas-panel">
<div class="panel-title">✨ Режимы</div>
<div class="scrollable">
<div class="ideas-grid" id="ideasList"></div>
</div>
</div>
</div>
<script>
const ideas=[
{id:'general',name:'Общий помощник',icon:'🤖'},
{id:'planner',name:'Подготовка к экзаменам',icon:'📅'},
{id:'homework',name:'Помощь с домашкой',icon:'📝'},
{id:'explain',name:'Объяснение темы',icon:'🎓'},
{id:'tests',name:'Проверка знаний',icon:'✅'},
{id:'motivation',name:'Мотивация и поддержка',icon:'💪'},
{id:'videos',name:'Видеоуроки',icon:'🎥'},
{id:'progress',name:'Мой прогресс',icon:'📊'},
{id:'deadlines',name:'Дедлайны и напоминания',icon:'⏰'},
{id:'adaptive',name:'Адаптивное обучение',icon:'🎯'},
{id:'group',name:'Групповая работа',icon:'👥'},
{id:'journal',name:'Оценки и МЭШ',icon:'📚'},
{id:'gamification',name:'Достижения и уровни',icon:'🏆'},
{id:'personalization',name:'Персональные рекомендации',icon:''},
{id:'offline',name:'Оффлайн материалы',icon:'📱'},
{id:'export',name:'Экспорт данных',icon:'📤'}
];

let chats = {};
let currentChatId = null;
let chatCounter = 0;
let currentFeature = 'general';

function createChat(featureId, title) {
    chatCounter++;
    const chatId = 'chat_' + chatCounter;
    chats[chatId] = {
        id: chatId,
        title: title,
        featureId: featureId,
        messages: [],
        createdAt: new Date().toISOString(),
        firstMessageSent: false
    };
    return chatId;
}

function newChat() {
    const featureId = prompt('Выбери режим:\\ngeneral, planner, homework, explain, tests, motivation, videos, progress, deadlines, adaptive, group, journal, gamification, personalization, offline, export', 'general');
    if (!featureId) return;
    const idea = ideas.find(i => i.id === featureId);
    const title = idea ? idea.name : 'Новый чат';
    const chatId = createChat(featureId, title);
    selectChat(chatId);
    renderChats();
}

function selectChat(chatId) {
    currentChatId = chatId;
    const chat = chats[chatId];
    currentFeature = chat.featureId;
    const idea = ideas.find(i => i.id === chat.featureId);
    document.getElementById('statusText').textContent = 'Режим: ' + (idea ? idea.name : 'Общий');
    renderMessages();
    renderChats();
    renderIdeas();
}

function renderChats(filter = '') {
    const list = document.getElementById('chatsList');
    const sortedChats = Object.values(chats).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    const filtered = sortedChats.filter(c => c.title.toLowerCase().includes(filter.toLowerCase()));
    
    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-state">Нет чатов</div>';
        return;
    }
    
    list.innerHTML = filtered.map(chat => {
        const time = new Date(chat.createdAt).toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
        return `
            <div class="chat-item ${chat.id === currentChatId ? 'active' : ''}" onclick="selectChat('${chat.id}')">
                <div class="chat-title">${chat.title}</div>
                <div class="chat-time">${time}</div>
            </div>
        `;
    }).join('');
}

function renderMessages() {
    const chat = chats[currentChatId];
    const area = document.getElementById('chatBox');
    
    if (!chat || chat.messages.length === 0) {
        area.innerHTML = '<div class="message bot-msg">Привет! Чем могу помочь?</div>';
        return;
    }
    
    area.innerHTML = chat.messages.map(msg => `
        <div class="message ${msg.role}-msg">${msg.content}</div>
    `).join('');
    
    area.scrollTop = area.scrollHeight;
}

function renderIdeas() {
    document.getElementById('ideasList').innerHTML = ideas.map(i => `
        <div class="idea-card ${i.id === currentFeature ? 'selected' : ''}" onclick="selectIdea('${i.id}','${i.name}')">
            <div class="idea-icon">${i.icon}</div>
            <div class="idea-name">${i.name}</div>
        </div>
    `).join('');
}

function selectIdea(id, name) {
    // Создаём новый чат при выборе режима
    const chatId = createChat(id, name);
    selectChat(chatId);
    renderChats();
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text || !currentChatId) return;
    
    const chat = chats[currentChatId];
    chat.messages.push({role: 'user', content: text});
    input.value = '';
    renderMessages();
    
    // Переименовываем чат после первого сообщения
    if (!chat.firstMessageSent) {
        chat.firstMessageSent = true;
        const shortDesc = text.length > 30 ? text.substring(0, 30) + '...' : text;
        const idea = ideas.find(i => i.id === chat.featureId);
        chat.title = (idea ? idea.name : 'Чат') + '. ' + shortDesc;
        renderChats();
    }
    
    try {
        const r = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: text,
                chat_id: currentChatId,
                feature_id: chat.featureId
            })
        });
        const d = await r.json();
        chat.messages.push({role: 'bot', content: d.response});
        renderMessages();
    } catch (e) {
        chat.messages.push({role: 'bot', content: 'Ошибка: ' + e.message});
        renderMessages();
    }
}

function filterChats() {
    const query = document.getElementById('searchInput').value;
    renderChats(query);
}

// Инициализация
const firstChatId = createChat('general', 'Общий помощник');
selectChat(firstChatId);
renderChats();
renderIdeas();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def main():
    return HTML

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = AIService.process_message(request.message, request.feature_id)
    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
