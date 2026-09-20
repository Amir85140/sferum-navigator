from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from services import AIService
import json
from datetime import datetime

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    chat_id: str
    feature_id: str = "general"

class Chat:
    def __init__(self, id: str, title: str, feature_id: str = "general"):
        self.id = id
        self.title = title
        self.feature_id = feature_id
        self.messages = []
        self.created_at = datetime.now().isoformat()

# Хранилище чатов (в памяти)
chats = {}
current_chat_id = None

def create_chat(feature_id: str = "general", title: str = None):
    chat_id = f"chat_{len(chats) + 1}"
    if not title:
        titles = {
            "planner": "Планировщик",
            "homework": "Помощь с ДЗ",
            "explain": "Объяснение темы",
            "tests": "Тесты",
            "motivation": "Мотивация",
            "videos": "Видеоуроки",
            "general": "Новый чат"
        }
        title = titles.get(feature_id, "Новый чат")
    chats[chat_id] = Chat(chat_id, title, feature_id)
    return chat_id

# Создаём первый чат по умолчанию
create_chat("general", "Общий помощник")
current_chat_id = list(chats.keys())[0]

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sferum Navigator</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#fff;height:100vh;overflow:hidden}
.app{display:flex;height:100vh}
.sidebar{width:260px;background:#171717;border-right:1px solid #2a2a2a;display:flex;flex-direction:column;overflow:hidden}
.sidebar-header{padding:12px;border-bottom:1px solid #2a2a2a}
.new-chat-btn{width:100%;padding:10px;background:#2a2a2a;color:#fff;border:1px solid #3a3a3a;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;transition:.2s;display:flex;align-items:center;justify-content:center;gap:8px}
.new-chat-btn:hover{background:#3a3a3a}
.search-box{margin-top:10px}
.search-box input{width:100%;padding:8px 12px;background:#2a2a2a;border:1px solid #3a3a3a;border-radius:8px;color:#fff;font-size:13px;outline:none}
.search-box input:focus{border-color:#5a5a5a}
.chats-list{flex:1;overflow-y:auto;padding:8px}
.chat-item{padding:10px 12px;border-radius:8px;cursor:pointer;margin-bottom:4px;transition:.2s;display:flex;align-items:center;gap:10px}
.chat-item:hover{background:#2a2a2a}
.chat-item.active{background:#2a2a2a;border-left:3px solid #ffdb4d}
.chat-icon{font-size:18px;flex-shrink:0}
.chat-title{font-size:14px;font-weight:500;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chat-time{font-size:11px;color:#666;flex-shrink:0}
.sidebar-footer{padding:12px;border-top:1px solid #2a2a2a}
.project-btn{width:100%;padding:10px;background:transparent;color:#999;border:1px solid #3a3a3a;border-radius:8px;cursor:pointer;font-size:13px;margin-bottom:6px;transition:.2s;display:flex;align-items:center;gap:8px}
.project-btn:hover{background:#2a2a2a;color:#fff}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.chat-header{padding:16px 20px;border-bottom:1px solid #2a2a2a;background:#0a0a0a;display:flex;align-items:center;justify-content:space-between}
.chat-header-title{font-size:16px;font-weight:600}
.chat-header-feature{font-size:12px;color:#999;background:#2a2a2a;padding:4px 10px;border-radius:12px}
.messages{flex:1;overflow-y:auto;padding:20px}
.message{margin-bottom:16px;display:flex;animation:fadeIn 0.3s}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.message.user{justify-content:flex-end}
.message-content{max-width:70%;padding:12px 16px;border-radius:12px;font-size:15px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}
.message.user .message-content{background:#2a2a2a;border-bottom-right-radius:4px}
.message.bot .message-content{background:#1a1a1a;border:1px solid #2a2a2a;border-bottom-left-radius:4px}
.input-area{padding:16px 20px;border-top:1px solid #2a2a2a;background:#0a0a0a}
.input-wrapper{display:flex;gap:10px;max-width:800px;margin:0 auto}
.input-wrapper input{flex:1;padding:12px 16px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;color:#fff;font-size:15px;outline:none}
.input-wrapper input:focus{border-color:#ffdb4d}
.input-wrapper button{padding:12px 24px;background:#ffdb4d;color:#000;border:none;border-radius:12px;font-weight:700;cursor:pointer;transition:.2s}
.input-wrapper button:hover{background:#ffe066}
.empty-chat{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#666}
.empty-chat-icon{font-size:64px;margin-bottom:16px}
.empty-chat-title{font-size:20px;font-weight:600;margin-bottom:8px}
.empty-chat-text{font-size:14px}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#2a2a2a;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#3a3a3a}
</style>
</head>
<body>
<div class="app">
<div class="sidebar">
<div class="sidebar-header">
<button class="new-chat-btn" onclick="newChat()">
<span>+</span>
<span>Новый чат</span>
</button>
<div class="search-box">
<input type="text" placeholder="Поиск чатов..." id="searchInput" oninput="filterChats()">
</div>
</div>
<div class="chats-list" id="chatsList"></div>
<div class="sidebar-footer">
<button class="project-btn" onclick="alert('Сообщество (демо)')">
<span></span>
<span>Сообщество</span>
</button>
<button class="project-btn" onclick="alert('Coder (демо)')">
<span>💻</span>
<span>Coder</span>
</button>
<button class="project-btn" onclick="alert('Новый проект (демо)')">
<span>🚀</span>
<span>Новый проект</span>
</button>
</div>
</div>
<div class="main" id="mainArea">
<div class="chat-header">
<div class="chat-header-title" id="chatTitle">Общий помощник</div>
<div class="chat-header-feature" id="chatFeature">Общий</div>
</div>
<div class="messages" id="messagesArea"></div>
<div class="input-area">
<div class="input-wrapper">
<input type="text" id="messageInput" placeholder="Напиши сообщение..." onkeypress="if(event.key==='Enter')sendMessage()">
<button onclick="sendMessage()">Отправить</button>
</div>
</div>
</div>
</div>
<script>
let chats = {};
let currentChatId = null;
let chatCounter = 0;

const features = {
    planner: {name: 'Планировщик', icon: '📅'},
    homework: {name: 'Помощь с ДЗ', icon: '📝'},
    explain: {name: 'Объяснить тему', icon: '🎓'},
    tests: {name: 'Тесты', icon: '✅'},
    motivation: {name: 'Мотивация', icon: '💪'},
    videos: {name: 'Видеоуроки', icon: ''},
    general: {name: 'Общий', icon: '🤖'}
};

function init() {
    const firstChatId = createChat('general', 'Общий помощник');
    selectChat(firstChatId);
    renderChats();
}

function createChat(featureId, title) {
    chatCounter++;
    const chatId = 'chat_' + chatCounter;
    chats[chatId] = {
        id: chatId,
        title: title || 'Новый чат',
        featureId: featureId,
        messages: [],
        createdAt: new Date().toISOString()
    };
    return chatId;
}

function newChat() {
    const featureId = prompt('Выбери режим (planner, homework, explain, tests, motivation, videos, general):', 'general');
    if (!featureId) return;
    const title = features[featureId]?.name || 'Новый чат';
    const chatId = createChat(featureId, title);
    selectChat(chatId);
    renderChats();
}

function selectChat(chatId) {
    currentChatId = chatId;
    const chat = chats[chatId];
    document.getElementById('chatTitle').textContent = chat.title;
    document.getElementById('chatFeature').textContent = features[chat.featureId]?.name || 'Общий';
    renderMessages();
    renderChats();
}

function renderChats(filter = '') {
    const list = document.getElementById('chatsList');
    const sortedChats = Object.values(chats).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    const filtered = sortedChats.filter(c => c.title.toLowerCase().includes(filter.toLowerCase()));
    
    list.innerHTML = filtered.map(chat => {
        const time = new Date(chat.createdAt).toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
        const icon = features[chat.featureId]?.icon || '💬';
        return `
            <div class="chat-item ${chat.id === currentChatId ? 'active' : ''}" onclick="selectChat('${chat.id}')">
                <div class="chat-icon">${icon}</div>
                <div class="chat-title">${chat.title}</div>
                <div class="chat-time">${time}</div>
            </div>
        `;
    }).join('');
}

function renderMessages() {
    const chat = chats[currentChatId];
    const area = document.getElementById('messagesArea');
    
    if (chat.messages.length === 0) {
        area.innerHTML = `
            <div class="empty-chat">
                <div class="empty-chat-icon">${features[chat.featureId]?.icon || '🤖'}</div>
                <div class="empty-chat-title">${chat.title}</div>
                <div class="empty-chat-text">Начни диалог, написав сообщение ниже</div>
            </div>
        `;
        return;
    }
    
    area.innerHTML = chat.messages.map(msg => `
        <div class="message ${msg.role}">
            <div class="message-content">${msg.content}</div>
        </div>
    `).join('');
    
    area.scrollTop = area.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text) return;
    
    const chat = chats[currentChatId];
    chat.messages.push({role: 'user', content: text});
    input.value = '';
    renderMessages();
    
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

init();
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
