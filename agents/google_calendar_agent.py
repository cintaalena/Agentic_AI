import datetime
import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- KONFIGURASI PATH ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TOKEN_FILE = os.path.join(PROJECT_ROOT, 'token.json')
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, 'credentials.json')
TASK_FILE = os.path.join(PROJECT_ROOT, 'tasks.json')

# Scope ini memberikan izin untuk membaca dan menulis di kalender.
SCOPES = ['https://www.googleapis.com/auth/calendar']


# --- FUNGSI OTENTIKASI (UNTUK SATU PENGGUNA) ---
def authenticate_google_calendar():
    """
    Menangani otentikasi Google untuk satu akun.
    Jika token tidak ada atau kedaluwarsa, alur otorisasi akan dimulai.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return creds


# --- FUNGSI MENYIMPAN TUGAS LOKAL ---
def save_task_for_reminder(title, deadline_str):
    """Menyimpan detail tugas ke file JSON lokal sebagai catatan."""
    new_task = {'title': title, 'deadline': deadline_str}
    tasks = []
    
    if os.path.exists(TASK_FILE):
        try:
            with open(TASK_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    tasks = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            tasks = [] 
    
    tasks.append(new_task)
    
    with open(TASK_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
    print(" -> Tugas berhasil dicatat di file tasks.json.")


# --- FUNGSI UTAMA PEMBUATAN EVENT ---
def create_calendar_event(summary, deadline_str):
    """
    Membuat acara di Google Calendar dan mengembalikan pesan status untuk bot.
    """
    print(" -> Agen Kalender: Memulai proses pembuatan acara...")
    try:
        creds = authenticate_google_calendar()
        service = build('calendar', 'v3', credentials=creds)

        start_time = datetime.datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
        end_time = start_time + datetime.timedelta(hours=1) 

        event_body = {
            'summary': summary,
            'description': f'Tugas terkait file yang baru ditambahkan. Dibuat oleh Agen AI.',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Jakarta',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Jakarta',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60}, 
                    {'method': 'popup', 'minutes': 60},      
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event_body).execute()
        success_message = f"✅ Berhasil! Reminder untuk '{summary}' telah dibuat di Google Calendar."
        print(f" -> Sukses! Link Acara: {event.get('htmlLink')}")
        save_task_for_reminder(summary, deadline_str)
        
        return success_message

    except ValueError:
        error_msg = f"Format tanggal tidak valid: '{deadline_str}'. Gunakan format: YYYY-MM-DD HH:MM"
        print(f" -> {error_msg}")
        return f"❌ Gagal: {error_msg}"
    except HttpError as error:
        error_msg = f"Terjadi error pada API Google Calendar: {error}"
        print(f' -> {error_msg}')
        return f"❌ Gagal: {error_msg}"
    except Exception as e:
        error_msg = f"Terjadi error tak terduga: {e}"
        print(f" -> {error_msg}")
        return f"❌ Gagal: {error_msg}"