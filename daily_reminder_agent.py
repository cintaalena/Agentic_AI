import json
import os
from datetime import datetime
from agents.notification_manager import send_telegram_message

try:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    PROJECT_ROOT = os.getcwd()
TASK_FILE = os.path.join(PROJECT_ROOT, 'tasks.json')

def check_and_send_reminders():
    """
    Membaca file tasks.json, mengirim reminder untuk tugas aktif,
    dan menghapus tugas yang sudah lewat deadline.
    """
    print(f"[{datetime.now()}] Menjalankan pengecekan reminder harian...")
    
    if not os.path.exists(TASK_FILE):
        print(f" -> File tasks.json tidak ditemukan di path yang benar: {TASK_FILE}. Tidak ada tugas untuk diingatkan.")
        return

    tasks = []
    try:
        with open(TASK_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                tasks = json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f" -> File tasks.json di {TASK_FILE} kosong atau rusak. Selesai.")
        return

    if not tasks:
        print(" -> Tidak ada tugas aktif dalam daftar. Selesai.")
        return

    active_tasks = []
    
    for task in tasks:
        title = task.get('title', 'Tanpa Judul')
        deadline_str = task.get('deadline')

        if not deadline_str:
            print(f" -> Tugas '{title}' tidak memiliki deadline. Melewati.")
            continue
        
        try:
            deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
        except ValueError:
            print(f" -> Format tanggal salah untuk tugas '{title}'. Melewati.")
            continue
            
        now = datetime.now()

        if deadline_dt < now:
            print(f" -> Tugas '{title}' sudah lewat deadline. Menghapus dari daftar.")
            continue

        time_remaining = deadline_dt - now
        days_remaining = time_remaining.days

        message = ""
        if days_remaining > 1:
            message = f"‼️ *REMINDER HARIAN* ‼️\n\nJangan lupa, tugas:\n*{title}*\n\nDeadline dalam *{days_remaining} hari lagi* ({deadline_str})."
        elif days_remaining == 1:
            message = f"‼️ *REMINDER HARIAN* ‼️\n\n*BESOK DEADLINE* untuk tugas:\n*{title}*\n\nSegera selesaikan sebelum {deadline_str}!"
        else:
            message = f"🚨 *HARI INI DEADLINE* 🚨\n\nTugas:\n*{title}*\n\nharus selesai hari ini sebelum jam *{deadline_dt.strftime('%H:%M')}*!"
        
        send_telegram_message(message)
        
        active_tasks.append(task)

    with open(TASK_FILE, 'w', encoding='utf-8') as f:
        json.dump(active_tasks, f, indent=4, ensure_ascii=False)
        
    print("Pengecekan reminder harian selesai.")


if __name__ == "__main__":
    check_and_send_reminders()