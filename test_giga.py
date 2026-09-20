import base64
import requests

# Твои ключи от Сбера
CLIENT_ID = "01a0bafa-206f-7e07-a2e7-df9e0acea285"
CLIENT_SECRET = "93e085d7-803b-4fe2-b1da-468aff78a450"

# Соединяем в формате Client_ID:Client_Secret
credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"

# Кодируем в base64
encoded_credentials = base64.b64encode(credentials.encode()).decode()

print("🔑 Ваши ключи:")
print(f"Client ID: {CLIENT_ID}")
print(f"Client Secret: {CLIENT_SECRET}")
print(f"\n📦 Закодированная строка: {encoded_credentials}")

# Пробуем получить токен
print("\n🔄 Пробуем подключиться к GigaChat...")

headers = {
    "Authorization": f"Basic {encoded_credentials}",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json"
}

data = {
    "scope": "GIGACHAT_API_PERS"
}

try:
    response = requests.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers=headers,
        data=data,
        verify=False  # Отключаем проверку SSL для Codespaces
    )
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        print(f"\n✅ УСПЕХ! Получен токен:")
        print(f"{access_token[:50]}...")
        
        # Теперь пробуем сделать запрос к GigaChat
        print("\n🔄 Пробуем сделать запрос к нейросети...")
        
        chat_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        chat_data = {
            "model": "GigaChat:latest",
            "messages": [
                {"role": "system", "content": "Ты полезный помощник. Ответь одним словом: 'Работает'."},
                {"role": "user", "content": "Привет, ты меня слышишь?"}
            ],
            "max_tokens": 50
        }
        
        chat_response = requests.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers=chat_headers,
            json=chat_data,
            verify=False
        )
        
        if chat_response.status_code == 200:
            result = chat_response.json()
            answer = result["choices"][0]["message"]["content"]
            print(f"\n🎉 НЕЙРОСЕТЬ ОТВЕТИЛА: {answer}")
            print("\n✅ ВСЁ РАБОТАЕТ! Теперь можно вставлять эти ключи в бота.")
        else:
            print(f"\n❌ Ошибка при запросе к GigaChat: {chat_response.status_code}")
            print(chat_response.text)
    else:
        print(f"\n❌ Ошибка при получении токена: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
