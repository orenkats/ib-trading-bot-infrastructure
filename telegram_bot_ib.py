import requests

bot_token = '6228550710:AAGJnS1dtuGZfK-1F_O2XHDvkxoTk-5HfO0'
chat_id =  '-861053639'

def send_telegram_message(text):
    
    max_chars = 4096
    for i in range(0, len(text), max_chars):
        chunk = text[i:i+max_chars]
        send_message_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(send_message_url, data={"chat_id": chat_id, "text": chunk})
