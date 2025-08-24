import os
import sys
import asyncio
import json
import ctypes
import pyautogui
import requests
import webbrowser
import shutil  
import time
from pytube import Search
from telethon import TelegramClient, events
from dotenv import load_dotenv
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = "my_focus_listener"
TARGET_CHANNEL_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", 0)) 

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY_NAME = os.getenv("CITY_NAME")

SEARCH_TERMS = {
    "Cerah": os.getenv("Youtube_CERAH"),
    "Hujan": os.getenv("Youtube_HUJAN"),
    "Berawan": os.getenv("Youtube_BERAWAN"),
    "Default": os.getenv("Youtube_DEFAULT")
}
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VOLUME_STATE_FILE = os.path.join(PROJECT_ROOT, 'volume_states.json')
BROWSERS_TO_KEEP_UNMUTED = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"]

APPS_TO_BLOCK = {
    "Telegram": r"C:\Program Files\WindowsApps\TelegramMessengerLLP.TelegramDesktop_6.0.2.0_x64__t4vj0pshhgkwm",
    "Whatsapp": r"C:\Program Files\WindowsApps\5319275A.WhatsAppDesktop_2.2531.4.0_x64__cv1g1gvanyjgm",
    "Edge":r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "chrome":r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "brave":r"C:\Users\Lenovo\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
}
APPS_TO_CLOSE = [
    "Telegram.exe",
    "WhatsApp.exe"
]
SITES_TO_BLOCK = [
    "www.facebook.com", "facebook.com",
    "www.twitter.com", "twitter.com",
    "www.instagram.com", "instagram.com",
    "www.tiktok.com", "tiktok.com"
]
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def control_app_volumes(action: str):
    """Membungkam semua aplikasi kecuali browser, atau mengembalikannya."""
    print(f"Mengontrol volume aplikasi: {action}")
    sessions = AudioUtilities.GetAllSessions()
    
    if action == "MUTE_OTHERS":
        original_volumes = {}
        for session in sessions:
            if session.Process:
                try:
                    process_name = session.Process.name()
                    volume = session.QueryInterface(ISimpleAudioVolume)
                    if not volume.GetMute():
                        original_volumes[str(session.ProcessId)] = {
                            "name": process_name, "volume": volume.GetMasterVolume()
                        }
                    if process_name.lower() not in BROWSERS_TO_KEEP_UNMUTED:
                        print(f"  -> Membungkam {process_name}")
                        volume.SetMute(1, None)
                    else:
                        print(f"  -> Browser {process_name} tidak dibungkam.")
                        volume.SetMute(0, None)
                except Exception: continue
        with open(VOLUME_STATE_FILE, 'w') as f:
            json.dump(original_volumes, f, indent=4)

    elif action == "RESTORE":
        if not os.path.exists(VOLUME_STATE_FILE): return
        with open(VOLUME_STATE_FILE, 'r') as f:
            original_volumes = json.load(f)
        for session in sessions:
            if session.Process:
                try:
                    pid_str = str(session.ProcessId)
                    if pid_str in original_volumes:
                        volume = session.QueryInterface(ISimpleAudioVolume)
                        saved_state = original_volumes[pid_str]
                        print(f"  -> Mengembalikan volume {saved_state['name']}")
                        volume.SetMasterVolume(saved_state['volume'], None)
                        volume.SetMute(0, None)
                except Exception: continue
        os.remove(VOLUME_STATE_FILE)

def open_notification_center():
    try:
        print("Membuka panel notifikasi (Win + N)...")
        pyautogui.hotkey('win', 'n')
    except Exception as e: print(f"Gagal menekan tombol: {e}")

def control_firewall_rules(action: str):
    for name, path in APPS_TO_BLOCK.items():
        rule_name = f"Block {name} Focus Mode"
        command = ""
        if action == "CREATE":
            command = f'netsh advfirewall firewall add rule name="{rule_name}" dir=out action=block program="{path}" > nul 2>&1'
        elif action == "DELETE":
            command = f'netsh advfirewall firewall delete rule name="{rule_name}" > nul 2>&1'
        if command: os.system(command)

def control_hosts_file(action: str):
    redirect_ip = "127.0.0.1"
    backup_path = HOSTS_PATH + ".backup_focus"
    
    try:
        if action == "BLOCK":
            print("Memblokir situs via file hosts...")
            if not os.path.exists(backup_path):
                print("  -> Membuat file backup 'hosts' yang asli.")
                shutil.copy(HOSTS_PATH, backup_path)

            with open(backup_path, "r") as f_in, open(HOSTS_PATH, "w") as f_out:
                content = f_in.read()
                f_out.write(content)
                if not content.endswith("\n"):
                    f_out.write("\n")
                f_out.write("\n# Start Focus Block\n")
                for site in SITES_TO_BLOCK:
                    f_out.write(f"{redirect_ip} {site}\n")
                f_out.write("# End Focus Block\n")
            print("  -> Situs pengganggu telah diblokir.")

        elif action == "UNBLOCK":
            print("Mengembalikan file hosts...")
            if os.path.exists(backup_path):
                print("  -> Mengembalikan 'hosts' dari backup dan menghapus backup.")
                os.remove(HOSTS_PATH)
                os.rename(backup_path, HOSTS_PATH)
                print("  -> File hosts telah normal kembali.")
            else:
                print("  -> Tidak ada file backup yang ditemukan, tidak ada aksi.")

    except Exception as e:
        print(f"[ERROR] Gagal memodifikasi file hosts. Detail: {e}")
        if os.path.exists(backup_path):
            try:
                os.remove(HOSTS_PATH)
                os.rename(backup_path, HOSTS_PATH)
                print("  -> [RECOVERY] Berhasil memulihkan hosts dari backup.")
            except Exception as rec_e:
                print(f"  -> [FATAL] Gagal memulihkan hosts dari backup: {rec_e}")

def get_current_weather(api_key, city):
    if not api_key or not city: return None
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    try:
        print(f"Mengambil data cuaca untuk {city}...")
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        weather_condition = data['weather'][0]['main']
        temp = data['main']['temp']
        print(f"Cuaca saat ini: {weather_condition}, Suhu: {temp}°C")
        return weather_condition
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengambil data cuaca: {e}")
        return None

def play_youtube_by_weather(weather):
    """
    Mencari video YouTube dengan logika retry, lalu membukanya di Chrome
    dengan fallback ke browser default.
    """
    search_term = ""
    if weather == "Clear": search_term = SEARCH_TERMS.get("Cerah", "lofi hip hop radio")
    elif weather in ["Rain", "Drizzle", "Thunderstorm"]: search_term = SEARCH_TERMS.get("Hujan", "rain sounds for sleeping")
    elif weather in ["Clouds", "Mist", "Fog", "Haze"]: search_term = SEARCH_TERMS.get("Berawan", "peaceful piano music for studying")
    else: search_term = SEARCH_TERMS.get("Default", "4k nature relaxation film")
    
    if not search_term:
        print("Tidak ada kata kunci YouTube yang valid di file .env")
        return

    video_link = None
    for i in range(3):
        try:
            print(f"Mencari video di YouTube (Percobaan {i+1}/3): '{search_term}'...")
            search_query = Search(search_term)

            if search_query.results:
                video = search_query.results[0]
                video_link = video.watch_url
                print(f"Video ditemukan: {video.title}")
                break  
            else:
                print("Tidak ada video ditemukan.")
        
        except Exception as e:
            print(f"Gagal pada percobaan {i+1}: {e}")
            if i == 2: 
                print("Gagal total mencari video setelah beberapa kali percobaan.")
                return 
        
        if not video_link:
            time.sleep(5)

    if video_link:
        print("Membuka video di browser...")
        try:
            webbrowser.get('chrome').open(video_link)
        except webbrowser.Error:
            print("   -> Google Chrome tidak ditemukan, membuka dengan browser default.")
            webbrowser.open(video_link)

def stop_browsers():
    print("Menutup semua browser...")
    all_browsers_to_close = set(b.lower() for b in BROWSERS_TO_KEEP_UNMUTED)
    for browser in all_browsers_to_close:
        os.system(f"taskkill /F /IM {browser} > nul 2>&1")
    print("Browser telah ditutup.")

def close_distraction_apps():
    """Menutup paksa aplikasi yang ada di daftar APPS_TO_CLOSE."""
    print("Menutup aplikasi pengganggu (WhatsApp, Telegram, dll)...")
    for app_exe in APPS_TO_CLOSE:
        print(f"  -> Mencoba menutup {app_exe}...")
        os.system(f"taskkill /F /IM {app_exe} > nul 2>&1")
    print("Aplikasi pengganggu telah ditutup.")

# FUNGSI MAIN
async def main():
    print("Listener lokal dimulai...")
    if not TARGET_CHANNEL_ID:
        print("KRITIS: TELEGRAM_CHANNEL_ID tidak diatur."); return
        
    print(f"Mendengarkan sinyal di Channel ID: {TARGET_CHANNEL_ID}")
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        @client.on(events.NewMessage(chats=TARGET_CHANNEL_ID))
        async def handler(event):
            message_text = event.message.text
            print(f"--- Sinyal Diterima: {message_text} ---")
            
            if message_text == "START_FOCUS":
                print("-> Aksi FOKUS AKTIF dimulai...")
                close_distraction_apps()
                stop_browsers()
                await asyncio.sleep(2) 
                open_notification_center()
                control_firewall_rules("CREATE")
                control_hosts_file("BLOCK")
                control_app_volumes("MUTE_OTHERS")
                weather = get_current_weather(OPENWEATHER_API_KEY, CITY_NAME)
                play_youtube_by_weather(weather)
                print("-> Aksi FOKUS AKTIF selesai.")
                
            elif message_text == "STOP_FOCUS":
                print("-> Aksi FOKUS BERHENTI dimulai...")
                control_firewall_rules("DELETE")
                control_hosts_file("UNBLOCK")
                control_app_volumes("RESTORE")
                stop_browsers()
                print("-> Aksi FOKUS BERHENTI selesai.")

        await client.run_until_disconnected()

if __name__ == "__main__":
    if not is_admin():
        print("="*60)
        print("KESALAHAN: HAK AKSES TIDAK CUKUP! Harap jalankan sebagai Administrator.")
        print("="*60)
        sys.exit()
    
    print("="*50)
    print("Listener berjalan sebagai Administrator. Siap menerima sinyal.")
    print("Tekan Ctrl+C untuk berhenti.")
    print("="*50)
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Terjadi error tak terduga: {e}")