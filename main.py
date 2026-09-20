from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
from services import AIService

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
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
.panel-title{font-size:20px;font-weight:700;margin-bottom:15px;flex-shrink:0}
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
.message{margin-bottom:12px;padding:12px 16px;border-radius:12px;max-width:80%;animation:slideIn 0.3s}
@keyframes slideIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.user-msg{background:linear-gradient(135deg,#667eea,#764ba2);margin-left:auto;text-align:right}
.bot-msg{background:rgba(255,255,255,0.2)}
.status-bar{background:rgba(255,219,77,0.2);border:2px solid #ffdb4d;border-radius:12px;padding:12px 18px;margin-bottom:15px;font-weight:600;flex-shrink:0}
.history-item{background:rgba(255,255,255,0.1);padding:10px;border-radius:8px;margin-bottom:6px;cursor:pointer;transition:all 0.2s;flex-shrink:0}
.history-item:hover{background:rgba(255,255,255,0.2)}
.history-query{font-size:13px;margin-bottom:3px}
.history-time{font-size:11px;opacity:0.7}
.empty-state{text-align:center;padding:30px 20px;opacity:0.6}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:rgba(255,255,255,0.1);border-radius:3px}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.3);border-radius:3px}
</style>
</head>
<body>
<div class="container">
<div class="panel history-panel">
<div class="panel-title">📜 История</div>
<div class="scrollable" id="historyList">
<div class="empty-state">История пуста</div>
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
<input type="text" id="searchInput" placeholder="Напиши свой вопрос..." onkeypress="if(event.key==='Enter')handleSearch()">
<button onclick="handleSearch()">Отправить</button>
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
{id:'planner',name:'Планировщик',icon:'📅'},
{id:'homework',name:'Помощь с ДЗ',icon:'📝'},
{id:'explain',name:'Объяснить тему',icon:'🎓'},
{id:'tests',name:'Тесты',icon:'✅'},
{id:'motivation',name:'Мотивация',icon:'💪'},
{id:'videos',name:'Видеоуроки',icon:'🎥'},
{id:'progress',name:'Прогресс',icon:'📊'},
{id:'deadlines',name:'Дедлайны',icon:'⏰'},
{id:'adaptive',name:'Адаптивность',icon:'🎯'},
{id:'group',name:'Групповая работа',icon:'👥'},
{id:'journal',name:'Журнал',icon:'📚'},
{id:'gamification',name:'Геймификация',icon:'🏆'},
{id:'personalization',name:'Персонализация',icon:''},
{id:'offline',name:'Оффлайн',icon:'📱'},
{id:'export',name:'Экспорт',icon:'📤'}
];
let history=[];
let currentFeature='general';

function renderIdeas(){
document.getElementById('ideasList').innerHTML=ideas.map(i=>`
<div class="idea-card ${i.id===currentFeature?'selected':''}" onclick="selectIdea('${i.id}','${i.name}')">
<div class="idea-icon">${i.icon}</div>
<div class="idea-name">${i.name}</div>
</div>
`).join('');
}

function selectIdea(id,name){
currentFeature=id;
document.getElementById('statusText').textContent='Режим: '+name;
renderIdeas();
document.getElementById('chatBox').innerHTML='<div class="message bot-msg">Теперь я в режиме "'+name+'". Чем помочь?</div>';
}

async function handleSearch(){
const input=document.getElementById('searchInput');
const q=input.value.trim();
if(!q)return;
const chat=document.getElementById('chatBox');
chat.innerHTML+=`<div class="message user-msg">${q}</div>`;
input.value='';
chat.scrollTop=chat.scrollHeight;
history.unshift({query:q,time:new Date().toLocaleTimeString()});
if(history.length>20)history.pop();
renderHistory();
try{
const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q,feature_id:currentFeature})});
const d=await r.json();
chat.innerHTML+=`<div class="message bot-msg">${d.response}</div>`;
}catch(e){
chat.innerHTML+=`<div class="message bot-msg">Ошибка: ${e.message}</div>`;
}
chat.scrollTop=chat.scrollHeight;
}

function renderHistory(){
const list=document.getElementById('historyList');
if(history.length===0){
list.innerHTML='<div class="empty-state">История пуста</div>';
return;
}
list.innerHTML=history.map(h=>`
<div class="history-item" onclick="document.getElementById('searchInput').value='${h.query}'">
<div class="history-query">${h.query}</div>
<div class="history-time">${h.time}</div>
</div>
`).join('');
}

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
