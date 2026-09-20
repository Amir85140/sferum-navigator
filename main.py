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
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sferum Navigator</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#fff;height:100vh}
.app{display:flex;height:100vh}
.nav{width:70px;background:#121212;border-right:1px solid #2a2a2a}
.history{width:280px;background:#121212;border-right:1px solid #2a2a2a;padding:20px;overflow-y:auto}
.main{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px}
.ideas{width:400px;background:#121212;border-left:1px solid #2a2a2a;padding:20px;overflow-y:auto}
h1{font-size:36px;margin-bottom:30px;background:linear-gradient(135deg,#ffdb4d,#ff9f43);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
input{width:100%;padding:15px;border:2px solid #2a2a2a;border-radius:12px;background:#121212;color:#fff;font-size:16px;margin-bottom:15px}
input:focus{outline:none;border-color:#ffdb4d}
button{padding:12px 24px;background:#ffdb4d;color:#000;border:none;border-radius:12px;font-weight:700;cursor:pointer}
button:hover{background:#ffe066}
.chat-box{width:100%;max-width:600px;height:300px;border:2px solid #2a2a2a;border-radius:12px;padding:15px;overflow-y:auto;margin-bottom:15px;background:#121212}
.msg{margin:10px 0;padding:12px;border-radius:10px;max-width:80%;white-space:pre-wrap;word-wrap:break-word}
.user{background:#252525;margin-left:auto;text-align:right}
.bot{background:#1a3a5c}
.idea{padding:15px;margin-bottom:10px;background:#1a1a1a;border-radius:12px;cursor:pointer;transition:.2s}
.idea:hover{background:#252525;transform:translateX(8px)}
.idea.selected{border:2px solid #ffdb4d}
.history-item{padding:10px;margin-bottom:8px;background:#1a1a1a;border-radius:8px;cursor:pointer}
.history-item:hover{background:#252525}
.current-feature{padding:10px;background:#1a3a5c;border-radius:8px;margin-bottom:15px;font-size:14px}
</style>
</head>
<body>
<div class="app">
<div class="nav"></div>
<div class="history">
<h3>📜 История</h3>
<div id="historyList"></div>
</div>
<div class="main">
<h1>Sferum Navigator</h1>
<div class="current-feature" id="currentFeature"> Режим: Общий</div>
<input type="text" id="searchInput" placeholder="Что тебя интересует?">
<button onclick="handleSearch()">Отправить</button>
<div class="chat-box" id="chatBox"></div>
</div>
<div class="ideas">
<h3>✨ Идеи</h3>
<div id="ideasList"></div>
</div>
</div>
<script>
const ideas=[
{id:'planner',name:'Планировщик'},
{id:'homework',name:'Помощь с ДЗ'},
{id:'explain',name:'Объяснить тему'},
{id:'tests',name:'Тесты'},
{id:'motivation',name:'Мотивация'},
{id:'videos',name:'Видеоуроки'},
{id:'progress',name:'Прогресс'},
{id:'deadlines',name:'Дедлайны'},
{id:'adaptive',name:'Адаптивность'},
{id:'group',name:'Групповая работа'},
{id:'journal',name:'Журнал'},
{id:'gamification',name:'Геймификация'},
{id:'personalization',name:'Персонализация'},
{id:'offline',name:'Оффлайн'},
{id:'export',name:'Экспорт'}
];
let history=[];
let currentFeature='general';

function renderIdeas(){
document.getElementById('ideasList').innerHTML=ideas.map(i=>`<div class="idea" id="idea-${i.id}" onclick="selectIdea('${i.id}','${i.name}')">${i.name}</div>`).join('');
}

function selectIdea(id,name){
document.querySelectorAll('.idea').forEach(e=>e.classList.remove('selected'));
document.getElementById('idea-'+id).classList.add('selected');
currentFeature=id;
document.getElementById('currentFeature').textContent='🎯 Режим: '+name;
document.getElementById('chatBox').innerHTML='';
}

async function handleSearch(){
const input=document.getElementById('searchInput');
const q=input.value.trim();
if(!q)return;

const chat=document.getElementById('chatBox');
chat.innerHTML+=`<div class="msg user">${q}</div>`;
input.value='';

history.unshift({query:q,time:new Date().toLocaleTimeString()});
if(history.length>20)history.pop();
renderHistory();

try{
const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q,feature_id:currentFeature})});
const d=await r.json();
chat.innerHTML+=`<div class="msg bot">${d.response}</div>`;
}catch(e){
chat.innerHTML+=`<div class="msg bot">Ошибка: ${e.message}</div>`;
}
chat.scrollTop=chat.scrollHeight;
}

function renderHistory(){
document.getElementById('historyList').innerHTML=history.map(h=>`<div class="history-item" onclick="document.getElementById('searchInput').value='${h.query}'">${h.query}<br><small style="color:#666">${h.time}</small></div>`).join('');
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
