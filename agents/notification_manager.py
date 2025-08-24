import os
import requests
from dotenv import load_dotenv


load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") 

def send_telegram_message(message: str):
    """
    Mengirim pesan teks sederhana ke chat ID yang telah ditentukan melalui Telegram Bot API.
    Fungsi ini ringan dan tidak memiliki dependensi ke agen lain.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID tidak ditemukan di .env")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() 
        print(f" -> Pesan reminder berhasil dikirim ke Telegram.")
    except requests.exceptions.RequestException as e:
        print(f" -> Gagal mengirim pesan ke Telegram: {e}")
