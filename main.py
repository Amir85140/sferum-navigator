from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services import AIService

app = FastAPI(title="Sferum Navigator", version="6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

HTML_CODE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sferum Navigator</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#fff;height:100vh;overflow:hidden}
body.light{background:#f5f5f5;color:#000}
.app{display:flex;height:100vh}
.nav{width:70px;background:#121212;border-right:1px solid #2a2a2a;display:flex;flex-direction:column;align-items:center;padding:20px 0;gap:8px}
body.light .nav{background:#fff;border-color:#e0e0e0}
.nav-logo{width:40px;height:40px;background:#ffdb4d;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:20px;cursor:pointer}
.nav-item{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:#999;transition:.2s}
.nav-item:hover{background:#252525;color:#fff}
body.light .nav-item:hover{background:#e8e8e8;color:#000}
.nav-item.active{color:#ffdb4d}
.nav-item svg{width:24px;height:24px}
.nav-bottom{margin-top:auto}
.history{width:280px;background:#121212;border-right:1px solid #2a2a2a;display:flex;flex-direction:column;overflow:hidden}
body.light .history{background:#fff;border-color:#e0e0e0}
.history-header{padding:24px 20px 16px;font-size:20px;font-weight:800}
.history-search{margin:0 16px 16px;padding:10px 14px;background:#1a1a1a;border:none;border-radius:10px;color:#fff;font-size:14px;outline:none}
body.light .history-search{background:#f0f0f0;color:#000}
.history-search::placeholder{color:#666}
.history-list{flex:1;overflow-y:auto;padding:0 12px}
.history-item{padding:12px 14px;border-radius:10px;margin-bottom:4px;cursor:pointer;transition:.2s;border-left:3px solid transparent}
.history-item:hover{background:#252525;border-left-color:#ffdb4d}
body.light .history-item:hover{background:#e8e8e8;border-left-color:#0077ff}
.history-item-text{font-size:14px;font-weight:500;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.history-item-time{font-size:11px;color:#666}
.history-empty{padding:40px 20px;text-align:center;color:#666;font-size:13px}
.history-footer{padding:16px;border-top:1px solid #2a2a2a}
body.light .history-footer{border-color:#e0e0e0}
.clear-btn{width:100%;padding:10px;background:#1a1a1a;border:none;border-radius:10px;color:#999;font-size:13px;font-weight:600;cursor:pointer}
body.light .clear-btn{background:#f0f0f0}
.clear-btn:hover{color:#fff}
body.light .clear-btn:hover{color:#000}
.main{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px}
.search-title{font-size:42px;font-weight:900;text-align:center;margin-bottom:32px;background:linear-gradient(135deg,#ffdb4d,#ff9f43);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-1px}
.search-box{position:relative;margin-bottom:40px;width:100%;max-width:640px}
.search-input{width:100%;padding:20px 70px 20px 28px;font-size:17px;border:2px solid #2a2a2a;border-radius:16px;background:#121212;color:#fff;outline:none;transition:.3s;font-family:inherit}
body.light .search-input{background:#fff;border-color:#e0e0e0;color:#000}
.search-input:focus{border-color:#ffdb4d}
.search-input::placeholder{color:#666}
.search-btn{position:absolute;right:10px;top:50%;transform:translateY(-50%);background:#ffdb4d;border:none;border-radius:12px;padding:12px 24px;color:#000;cursor:pointer;font-weight:700;font-size:14px;transition:.2s}
.search-btn:hover{background:#ffe066;transform:translateY(-50%) scale(1.05)}
.quick{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;width:100%;max-width:640px}
.chip{padding:20px;background:#121212;border:2px solid #2a2a2a;border-radius:16px;text-align:center;cursor:pointer;transition:.3s}
body.light .chip{background:#fff;border-color:#e0e0e0}
.chip:hover{transform:translateY(-5px);border-color:#ffdb4d;box-shadow:0 8px 24px rgba(255,219,77,.2)}
.chip-icon{font-size:36px;margin-bottom:12px}
.chip-title{font-size:14px;font-weight:700}
.ideas{width:400px;background:#121212;border-left:1px solid #2a2a2a;display:flex;flex-direction:column;overflow:hidden}
body.light .ideas{background:#fff;border-color:#e0e0e0}
.ideas-header{padding:24px 24px 16px}
.ideas-title{font-size:24px;font-weight:900;margin-bottom:6px;background:linear-gradient(135deg,#ffdb4d,#ff9f43);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ideas-sub{font-size:13px;color:#666}
.ideas-list{flex:1;overflow-y:auto;padding:0 12px 20px}
.idea{display:flex;align-items:center;gap:16px;padding:16px;border-radius:16px;cursor:pointer;transition:.3s;margin-bottom:8px}
.idea:hover{transform:translateX(8px) scale(1.02);background:#252525}
body.light .idea:hover{background:#e8e8e8}
.idea.selected{background:#2f2f2f;border:2px solid #ffdb4d}
body.light .idea.selected{background:#e0e0e0;border-color:#0077ff}
.idea-icon{width:68px;height:68px;border-radius:18px;display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 8px 24px rgba(0,0,0,.3);transition:.3s}
.idea:hover .idea-icon{transform:rotate(8deg) scale(1.1)}
.idea-icon svg{width:36px;height:36px}
.idea-info{flex:1;min-width:0}
.idea-label{font-size:11px;color:#666;margin-bottom:6px;text-transform:uppercase;letter-spacing:.8px;font-weight:600}
.idea-name{font-size:16px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.idea-arrow{color:#666;font-size:24px;opacity:0;transition:.3s}
.idea:hover .idea-arrow{opacity:1}
.selected-bar{padding:20px 24px;border-top:1px solid #2a2a2a;background:#1a1a1a;min-height:80px;display:flex;align-items:center;gap:16px}
body.light .selected-bar{background:#f0f0f0;border-color:#e0e0e0}
.selected-icon{width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 4px 12px rgba(0,0,0,.3)}
.selected-icon svg{width:24px;height:24px}
.selected-text{flex:1;min-width:0}
.selected-label{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:4px}
.selected-name{font-size:16px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.selected-btn{padding:10px 20px;background:#ffdb4d;color:#000;border:none;border-radius:12px;font-weight:800;font-size:13px;cursor:pointer;transition:.2s}
.selected-btn:hover{background:#ffe066;transform:scale(1.05)}
.selected-btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.theme-btn{position:fixed;top:20px;right:420px;width:44px;height:44px;background:#121212;border:2px solid #2a2a2a;border-radius:50%;font-size:20px;cursor:pointer;z-index:1000;display:flex;align-items:center;justify-content:center;transition:.3s;color:#fff}
body.light .theme-btn{background:#fff;border-color:#e0e0e0;color:#000}
.theme-btn:hover{transform:rotate(180deg) scale(1.1);border-color:#ffdb4d}
.idea{animation:fadeIn .5s ease-out forwards;opacity:0}
.idea:nth-child(1){animation-delay:.05s}
.idea:nth-child(2){animation-delay:.1s}
.idea:nth-child(3){animation-delay:.15s}
.idea:nth-child(4){animation-delay:.2s}
.idea:nth-child(5){animation-delay:.25s}
.idea:nth-child(6){animation-delay:.3s}
.idea:nth-child(7){animation-delay:.35s}
.idea:nth-child(8){animation-delay:.4s}
.idea:nth-child(9){animation-delay:.45s}
.idea:nth-child(10){animation-delay:.5s}
.idea:nth-child(11){animation-delay:.55s}
.idea:nth-child(12){animation-delay:.6s}
.idea:nth-child(13){animation-delay:.65s}
.idea:nth-child(14){animation-delay:.7s}
.idea:nth-child(15){animation-delay:.75s}
@keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:#1a1a1a;border-radius:3px}
body.light ::-webkit-scrollbar-track{background:#f0f0f0}
::-webkit-scrollbar-thumb{background:#2a2a2a;border-radius:3px}
body.light ::-webkit-scrollbar-thumb{background:#e0e0e0}
</style>
</head>
<body>
<button class="theme-btn" onclick="toggleTheme()" id="themeBtn">☀️</button>
<div class="app">
<div class="nav">
<div class="nav-logo">🚀</div>
<div class="nav-item active"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/></svg></div>
<div class="nav-item"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9z"/></svg></div>
<div class="nav-item"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></div>
<div class="nav-bottom">
<div class="nav-item"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L3.16 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg></div>
</div>
</div>
<div class="history">
<div class="history-header">📜 История</div>
<input type="text" class="history-search" placeholder="Поиск в истории...">
<div class="history-list" id="historyList">
<div class="history-empty">История пуста<br>Начни поиск</div>
</div>
<div class="history-footer">
<button class="clear-btn" onclick="clearHistory()">🗑 Очистить</button>
</div>
</div>
<div class="main">
<h1 class="search-title">Sferum Navigator</h1>
<div class="search-box">
<input type="text" class="search-input" id="searchInput" placeholder="Что тебя интересует?" onkeypress="if(event.key==='Enter')handleSearch()">
<button class="search-btn" onclick="handleSearch()">Найти</button>
</div>
<div class="quick">
<div class="chip" onclick="quickAction('planner')"><div class="chip-icon">📅</div><div class="chip-title">Планировщик</div></div>
<div class="chip" onclick="quickAction('homework')"><div class="chip-icon">📝</div><div class="chip-title">Помощь с ДЗ</div></div>
<div class="chip" onclick="quickAction('explain')"><div class="chip-icon"></div><div class="chip-title">Объяснить тему</div></div>
<div class="chip" onclick="quickAction('tests')"><div class="chip-icon">✅</div><div class="chip-title">Тесты</div></div>
<div class="chip" onclick="quickAction('motivation')"><div class="chip-icon">💪</div><div class="chip-title">Мотивация</div></div>
<div class="chip" onclick="quickAction('videos')"><div class="chip-icon"></div><div class="chip-title">Видеоуроки</div></div>
</div>
</div>
<div class="ideas">
<div class="ideas-header">
<div class="ideas-title">✨ Идеи для тебя</div>
<div class="ideas-sub">Выбери, что хочешь попробовать</div>
</div>
<div class="ideas-list" id="ideasList"></div>
<div class="selected-bar">
<div class="selected-icon" id="selIcon" style="background:#333"><svg viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg></div>
<div class="selected-text">
<div class="selected-label">Выбрано</div>
<div class="selected-name" id="selName">Ничего не выбрано</div>
</div>
<button class="selected-btn" id="useBtn" onclick="useSelected()" disabled>Открыть</button>
</div>
</div>
</div>
<script>
const ideas=[
{id:'planner',name:'Умный планировщик',label:'Рекомендуем',color:'#FF6B6B'},
{id:'homework',name:'Помощь с ДЗ',label:'Метод Сократа',color:'#4ECDC4'},
{id:'explain',name:'Объяснение тем',label:'Контекстный ИИ',color:'#45B7D1'},
{id:'tests',name:'Тесты и проверка',label:'Проверь себя',color:'#FFA07A'},
{id:'motivation',name:'Мотивация',label:'Поддержка',color:'#98D8C8'},
{id:'videos',name:'Видеоуроки',label:'RuTube и VK',color:'#F7DC6F'},
{id:'progress',name:'Прогресс обучения',label:'Твоя статистика',color:'#BB8FCE'},
{id:'deadlines',name:'Дедлайны',label:'Не забудь!',color:'#F1948A'},
{id:'adaptive',name:'Адаптивное обучение',label:'Под твой темп',color:'#82E0AA'},
{id:'group',name:'Групповая работа',label:'Вместе веселее',color:'#85C1E9'},
{id:'journal',name:'Интеграция с журналом',label:'Синхронизация',color:'#F0B27A'},
{id:'gamification',name:'Геймификация',label:'Достижения',color:'#D7BDE2'},
{id:'personalization',name:'Персонализация',label:'Только для тебя',color:'#A9DFBF'},
{id:'offline',name:'Оффлайн режим',label:'Без интернета',color:'#FAD7A0'},
{id:'export',name:'Экспорт данных',label:'Выгрузка',color:'#AED6F1'}
];
let selected=null;
const svg='<svg viewBox="0 0 24 24" fill="white"><path d="M20.5 11H19V7c0-1.1-.9-2-2-2h-4V3.5C13 2.12 11.88 1 10.5 1S8 2.12 8 3.5V5H4c-1.1 0-1.99.9-1.99 2v3.8H3.5c1.49 0 2.7 1.21 2.7 2.7s-1.21 2.7-2.7 2.7H2V20c0 1.1.9 2 2 2h3.8v-1.5c0-1.49 1.21-2.7 2.7-2.7s2.7 1.21 2.7 2.7V22H17c1.1 0 2-.9 2-2v-4h1.5c1.38 0 2.5-1.12 2.5-2.5S21.88 11 20.5 11z"/></svg>';
function render(){
document.getElementById('ideasList').innerHTML=ideas.map(i=>`<div class="idea" id="idea-${i.id}" onclick="select('${i.id}')"><div class="idea-icon" style="background:${i.color}">${svg}</div><div class="idea-info"><div class="idea-label">${i.label}</div><div class="idea-name">${i.name}</div></div><div class="idea-arrow">›</div></div>`).join('');
}
function select(id){
document.querySelectorAll('.idea').forEach(e=>e.classList.remove('selected'));
document.getElementById('idea-'+id).classList.add('selected');
selected=ideas.find(i=>i.id===id);
document.getElementById('selIcon').style.background=selected.color;
document.getElementById('selName').textContent=selected.name;
document.getElementById('useBtn').disabled=false;
}
function useSelected(){
if(!selected)return;
document.getElementById('searchInput').value=selected.name;
addHistory(selected.name);
handleSearch();
}
function quickAction(id){
const i=ideas.find(x=>x.id===id);
document.getElementById('searchInput').value=i.name;
addHistory(i.name);
select(id);
}
async function handleSearch(){
const q=document.getElementById('searchInput').value.trim();
if(!q)return;
addHistory(q);
try{
const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q})});
const d=await r.json();
alert(d.response);
}catch(e){alert('Ошибка: '+e.message);}
}
function addHistory(q){
const l=document.getElementById('historyList');
const t=new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'});
if(l.children.length===1&&l.children[0].classList.contains('history-empty'))l.innerHTML='';
const d=document.createElement('div');
d.className='history-item';
d.innerHTML=`<div class="history-item-text">${q}</div><div class="history-item-time">${t}</div>`;
d.onclick=()=>{document.getElementById('searchInput').value=q;};
l.insertBefore(d,l.firstChild);
if(l.children.length>30)l.removeChild(l.lastChild);
}
function clearHistory(){
document.getElementById('historyList').innerHTML='<div class="history-empty">История пуста<br>Начни поиск</div>';
}
function toggleTheme(){
document.body.classList.toggle('light');
const isLight=document.body.classList.contains('light');
document.getElementById('themeBtn').textContent=isLight?'':'☀️';
localStorage.setItem('theme',isLight?'light':'dark');
}
if(localStorage.getItem('theme')==='light'){document.body.classList.add('light');document.getElementById('themeBtn').textContent='';}
render();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return HTML_CODE

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = AIService.process_message(request.message)
    return {"response": response}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
