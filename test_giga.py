import requests
from requests.auth import HTTPBasicAuth
import urllib3

# Отключаем предупреждения о небезопасном SSL (нужно для Codespaces)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

print("🔄 Получаем токен от GigaChat...")

try:
    # 1. Получаем токен через HTTP Basic Auth (самый надежный способ для Сбера)
    response = requests.post(
        url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": "00000000-0000-0000-0000-000000000000"
        },
        data="scope=GIGACHAT_API_PERS",
        verify=False
    )
    
    print(f"Статус ответа: {response.status_code}")
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Токен получен: {token[:40]}...")
        
        # 2. Тестируем саму нейросеть
        print("\n🔄 Отправляем тестовый запрос в GigaChat...")
        chat_response = requests.post(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "model": "GigaChat:latest",
                "messages": [
                    {"role": "user", "content": "Привет! Ответь одним словом: работает?"}
                ],
                "max_tokens": 20
            },
            verify=False
        )
        
        if chat_response.status_code == 200:
            answer = chat_response.json()["choices"][0]["message"]["content"]
            print(f"✅ GigaChat ответил: {answer}")
            print("\n🎉 ВСЁ РАБОТАЕТ! Ключи верные.")
        else:
            print(f"❌ Ошибка GigaChat: {chat_response.status_code}")
            print(chat_response.text)
    else:
        print(f"❌ Ошибка получения токена: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Критическая ошибка: {e}")
