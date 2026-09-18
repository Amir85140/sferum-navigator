from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import uvicorn
from services import PlannerService, AIService

app = FastAPI(title="Sferum Navigator AI")

class PlanRequest(BaseModel):
    time: int
    subjects: List[str]

class ChatRequest(BaseModel):
    message: str

@app.post("/api/plan")
async def get_plan(request: PlanRequest):
    return PlannerService.generate_plan(request.time, request.subjects)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = AIService.process_message(request.message)
    return {"response": response}

@app.get("/", response_class=HTMLResponse)
async def web_interface():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Sferum Navigator</title>
        <style>
            body { font-family: sans-serif; background: #f0f2f5; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            h1 { color: #0077FF; text-align: center; }
            .chat-box { height: 300px; border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; overflow-y: scroll; }
            .message { margin: 5px 0; padding: 8px; border-radius: 5px; }
            .bot { background: #e3f2fd; }
            .user { background: #0077FF; color: white; text-align: right; }
            input, button { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: 1px solid #ccc; box-sizing: border-box; }
            button { background: #0077FF; color: white; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Sferum Navigator</h1>
            <div class="chat-box" id="chatBox">
                <div class="message bot">Привет! Сколько минут ты готов учиться сегодня?</div>
            </div>
            <input type="text" id="userInput" placeholder="Напиши сообщение...">
            <button onclick="sendMessage()">Отправить</button>
        </div>
        <script>
            async function sendMessage() {
                const input = document.getElementById('userInput');
                const chatBox = document.getElementById('chatBox');
                const text = input.value;
                if (!text) return;
                chatBox.innerHTML += `<div class="message user">${text}</div>`;
                input.value = '';
                const response = await fetch('/api/chat', {
                    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: text})
                });
                const data = await response.json();
                chatBox.innerHTML += `<div class="message bot">${data.response}</div>`;
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
