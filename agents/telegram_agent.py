import sys
import os
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root_path)
import logging
import threading
import asyncio
import json
import re
import telegram
import docx
import google.generativeai as genai 
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    filters,
)
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from agents.google_calendar_agent import create_calendar_event
from agents.summarizer_highlighter import process_file, extract_text_from_pdf, extract_text_from_docx
from agents.quiz_generator import generate_quiz, score_essay_answer
from agents.paper_finder_agent import cari_paper_ilmiah
from agents.intent_router_agent import classify_intent
from agents.semantic_scholar_agent import cari_paper_semantic_scholar

# --- Konfigurasi Awal ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com")
TARGET_CHANNEL_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", 0))
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FOCUS_MODE_FILE = os.path.join(PROJECT_ROOT_DIR, 'focus_mode.json')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def call_gemini_for_plan(prompt: str) -> str:
    """Mengirim prompt ke Gemini dan mengembalikan respons teksnya."""
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY tidak diatur di file .env"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt, safety_settings={'HARM_CATEGORY_HARASSMENT':'BLOCK_NONE'})
        return response.text
    except Exception as e:
        logger.error(f"Error saat memanggil Gemini API: {e}")
        return f"Maaf, terjadi kesalahan saat berkomunikasi dengan AI: {e}"

#conversation_handler
(
    CONFIRM_REMINDER,
    GET_STUDY_TOPIC,       
    ANSWERING_EVALUATION,
    CHOOSE_ACTION,
    GET_TASK_TITLE,
    GET_TASK_DEADLINE,
    AWAITING_PLAN_CONFIRMATION   
) = range(7)


#helper
def get_formatted_task_list() -> str:
    TASK_FILE = os.path.join(PROJECT_ROOT_DIR, 'tasks.json')
    if not os.path.exists(TASK_FILE):
        return "Saat ini tidak ada tugas aktif."
    
    try:
        with open(TASK_FILE, 'r', encoding='utf-8') as f:
            all_tasks = json.load(f)

        if not all_tasks:
            return "Saat ini tidak ada tugas aktif."

        now = datetime.now()
        upcoming_tasks = [
            task for task in all_tasks 
            if datetime.strptime(task['deadline'], "%Y-%m-%d %H:%M") > now
        ]

        if not upcoming_tasks:
            return "Saat ini tidak ada tugas aktif."

        upcoming_tasks.sort(key=lambda x: datetime.strptime(x['deadline'], "%Y-%m-%d %H:%M"))
        
        message = "🗓️ *Daftar Tugas Aktif Anda:*\n\n"
        for i, task in enumerate(upcoming_tasks, 1):
            message += f"{i}. *{task['title']}*\n    - Deadline: `{task['deadline']}`\n"
        return message
        
    except (json.JSONDecodeError, FileNotFoundError):
        return "Gagal memuat daftar tugas."
    except ValueError:
        logger.error("Format tanggal salah terdeteksi di tasks.json")
        return "Gagal memuat daftar tugas karena format tanggal tidak valid."


#FOKUS MODE
def set_focus_mode_status(active: bool):
    """Menulis status mode fokus ke file JSON."""
    status = {"focus_mode_active": active}
    if os.path.exists(os.path.dirname(FOCUS_MODE_FILE)):
        with open(FOCUS_MODE_FILE, 'w') as f:
            json.dump(status, f)
    print(f"Mode fokus diatur ke: {active}")

async def send_long_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    """
    Secara otomatis memecah dan mengirim teks yang panjangnya melebihi batas Telegram.
    Versi ini menggunakan context.bot.send_message secara langsung.
    """
    MAX_MESSAGE_LENGTH = 4096
    

    if len(text) <= MAX_MESSAGE_LENGTH:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except telegram.error.BadRequest:

            await context.bot.send_message(chat_id=chat_id, text=text)
        return


    parts = []
    current_part = ""
    for line in text.splitlines(keepends=True):
        if len(current_part) + len(line) > MAX_MESSAGE_LENGTH:
            parts.append(current_part)
            current_part = line
        else:
            current_part += line
    

    if current_part:
        parts.append(current_part)


    for part in parts:
        try:
            await context.bot.send_message(chat_id=chat_id, text=part, parse_mode="Markdown")
        except telegram.error.BadRequest:
            await context.bot.send_message(chat_id=chat_id, text=part)
        await asyncio.sleep(1) 

async def start_focus_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim sinyal dan mengaktifkan status blokir."""
    
    if TARGET_CHANNEL_ID != 0:
        await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text="START_FOCUS")
        print("Sinyal START_FOCUS telah dikirim ke jembatan.")
    
    set_focus_mode_status(True)
    
    await update.message.reply_text(
        "🚀 Mode Fokus"
    )

async def stop_focus_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mengirim sinyal STOP dan memulai alur evaluasi."""
    if TARGET_CHANNEL_ID != 0:
        await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text="STOP_FOCUS")
        print("Sinyal STOP_FOCUS telah dikirim ke jembatan.")
    set_focus_mode_status(False)
    
    await update.message.reply_text(
        "✅ Mode Fokus telah dihentikan.\n\n"
        "Untuk menguji pemahaman Anda, materi apa yang baru saja dipelajari?"
    )
    
    return GET_STUDY_TOPIC

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyapa pengguna dan memberikan instruksi awal."""
    user = update.effective_user
    await update.message.reply_html(
        f"Halo {user.mention_html()}! Saya adalah asisten AI Anda.\n\n"
        "<b>Cara menggunakan saya:</b>\n\n"
        "📄 <b>Kirim file</b> (.pdf/.docx) dan saya akan otomatis meringkas dan menyorotnya.\n\n"
        "🗣️ Langsung ketik saja jika ingin membuat reminder atau mencari refrensi paper"
        "🍅 Gunakan <b>/fokus</b> dan <b>/stopfokus</b> untuk sesi belajar Anda.",
    )
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Tindakan dibatalkan.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencatat semua error yang muncul dan menampilkannya di konsol."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    
    if isinstance(update, Update):
        await update.message.reply_text("Maaf, terjadi kesalahan internal. Coba lagi nanti.")

def extract_reminder_details_sync(text: str, current_time: str) -> dict:
    """Fungsi sinkron untuk memanggil AI dan mengekstrak detail reminder."""
    prompt = (
        f"Anda adalah AI ahli dalam mengekstrak informasi. Berdasarkan permintaan pengguna dan waktu saat ini ({current_time}), ekstrak 'judul acara' dan 'waktu deadline' dalam format YYYY-MM-DD HH:MM.\n"
        "Contoh:\n"
        "Teks: 'ingatkan aku Ujian Kalkulus hari Jumat jam 10 pagi'\n"
        "Waktu Saat Ini: '2025-08-22 22:35'\n"
        'Hasil: {{"title": "Ujian Kalkulus", "deadline": "2025-08-29 10:00"}}\n\n'
        "Teks: 'ada rapat tim besok jam 2 siang'\n"
        "Waktu Saat Ini: '2025-08-22 22:35'\n"
        'Hasil: {{"title": "Rapat tim", "deadline": "2025-08-23 14:00"}}\n\n'
        "--- Analisis Teks Berikut ---\n"
        f"Teks: '{text}'\n"
        "Hasil:"
    )
    response_text = call_gemini_for_plan(prompt)
    try:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"error": "AI tidak mengembalikan format yang benar."}
    return {"error": "Gagal mengekstrak detail dari permintaan Anda."}

def generate_plan_from_text_sync(task_topic: str, deadline_str: str, file_content: str) -> str:
    """Membuat rencana belajar yang realistis berdasarkan sisa waktu yang dihitung."""
    
    time_constraint_text = f"Selesaikan tugas sebelum deadline: {deadline_str}."
    try:

        deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
        time_remaining = deadline_dt - datetime.now()
        days_remaining = time_remaining.days

        if time_remaining.total_seconds() <= 0:
            return "Waktu untuk tugas ini sudah habis. Tidak ada rencana yang bisa dibuat."

        if days_remaining < 1:
            hours_remaining = max(1, int(time_remaining.total_seconds() / 3600))
            time_constraint_text = f"Anda hanya memiliki sekitar {hours_remaining} jam. Buatkan rencana kerja per jam yang sangat padat dan mendesak."
        else:
            time_constraint_text = f"Anda memiliki sisa waktu {days_remaining} hari. Buatkan rencana kerja harian yang realistis."

    except (ValueError, TypeError):
        logger.warning(f"Format deadline '{deadline_str}' tidak bisa di-parse, menyerahkannya pada AI.")


    prompt = (
        f"Anda adalah seorang perencana tugas yang sangat disiplin dan realistis. Tugas Anda adalah membuat rencana kerja untuk menyelesaikan sebuah tugas.\n\n"
        f"**Topik Tugas:** {task_topic}\n"
        f"**Deadline Final:** {deadline_str}\n\n"
        f"**KENDALA WAKTU UTAMA:** {time_constraint_text}\n\n"
        f"**PERINTAH TEGAS:** Buat rencana yang SANGAT REALISTIS dan hanya menggunakan sisa waktu yang ada. JANGAN membuat rencana yang melebihi batas waktu yang telah ditentukan. Jika waktu sangat singkat (kurang dari sehari), pecah tugas menjadi blok-blok per jam yang bisa dikerjakan. Jika waktunya beberapa hari, buat rencana harian.\n"
        "JANGAN membuat estimasi waktu yang tidak masuk akal seperti '300 hari' jika deadlinenya besok.\n\n"
        f"**Materi Tugas (untuk referensi):**\n---\n{file_content[:3000]}\n---\n\n"
        f"Sajikan rencana dalam format Markdown yang jelas dan terstruktur."
    )
    return call_gemini_for_plan(prompt)

async def handle_plan_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pilihan pengguna dan membuat rencana secara non-blocking."""
    query = update.callback_query
    await query.answer()

    deadline_str = context.user_data.get('deadline_str')
    file_path = context.user_data.get('file_path')


    if not deadline_str or not file_path:
        await query.edit_message_text(
            text="Maaf, sesi ini telah berakhir atau data tidak lengkap. Silakan mulai lagi dengan mengirim file."
        )
        context.user_data.clear()
        return ConversationHandler.END


    if query.data == 'create_plan':
        await query.edit_message_text(text="Baik! Saya akan buatkan rencana belajar 🧠")
        
        try:
            loop = asyncio.get_running_loop()
            plan_result = await loop.run_in_executor(
                None, generate_plan_from_text_sync, deadline_str, file_path
            )
            
            await send_long_message(context, query.message.chat_id, plan_result)

        except Exception as e:
            logger.error(f"Gagal membuat rencana: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id, text=f"Maaf, terjadi kesalahan saat membuat rencana: {e}"
            )

    else: 
        await query.edit_message_text(text="Oke, tidak masalah. Selamat mengerjakan tugasnya! 👍")
    
    context.user_data.clear()
    return ConversationHandler.END
    
async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai alur pembuatan reminder dari bahasa natural."""
    # Mengambil teks setelah perintah /tolong
    user_input = " ".join(context.args)
    if not user_input:
        await update.message.reply_text("Tentu, apa yang perlu saya ingatkan? Contoh:\n`/tolong Ujian Kalkulus besok jam 10 pagi`")
        return ConversationHandler.END

    await update.message.reply_text("Oke, saya coba pahami permintaan Anda...")
    
    try:
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        loop = asyncio.get_running_loop()
        details = await loop.run_in_executor(None, extract_reminder_details_sync, user_input, current_time_str)

        if "error" in details:
            await update.message.reply_text(f"Maaf, saya kesulitan memahami: {details['error']}")
            return ConversationHandler.END

        context.user_data['reminder_details'] = details
        
        deadline_dt = datetime.strptime(details['deadline'], "%Y-%m-%d %H:%M")
        human_readable_deadline = deadline_dt.strftime("%A, %d %B %Y, %H:%M")

        keyboard = [[InlineKeyboardButton("✅ Konfirmasi", callback_data="confirm"),
                     InlineKeyboardButton("❌ Batal", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Saya akan membuat reminder untuk:\n"
            f"<b>Judul:</b> {details['title']}\n"
            f"<b>Waktu:</b> {human_readable_deadline}\n\n"
            "Apakah benar?",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return CONFIRM_REMINDER
        
    except Exception as e:
        logger.error(f"Error di alur /tolong: {e}")
        await update.message.reply_text(f"Maaf, terjadi kesalahan: {e}")
        return ConversationHandler.END

async def confirm_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani konfirmasi pembuatan reminder dari tombol inline."""
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm':
        details = context.user_data.get('reminder_details')
        if not details:
            await query.edit_message_text("Maaf, detail reminder hilang. Silakan coba lagi.")
            return ConversationHandler.END

        await query.edit_message_text("Sip! Sedang membuat reminder di Google Calendar...")
        
        loop = asyncio.get_running_loop()
        result_message = await loop.run_in_executor(
            None, create_calendar_event, details['title'], details['deadline']
        )
        await query.edit_message_text(result_message)
    else:
        await query.edit_message_text("Oke, dibatalkan.")

    context.user_data.clear()
    return ConversationHandler.END


async def paper_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani perintah /paper dengan mencari di arXiv DAN Semantic Scholar."""
    if not context.args:
        await update.message.reply_text("Gunakan format: /paper [topik pencarian]")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔎 Siap! Saya cari paper tentang '{query}' dari berbagai sumber...")

    
    hasil_arxiv = cari_paper_ilmiah(query, max_results=3)
    hasil_ss = cari_paper_semantic_scholar(query, max_results=3)

    
    hasil_gabungan = hasil_ss + hasil_arxiv 

    
    hasil_bersih = [res for res in hasil_gabungan if not res.startswith("Gagal")]

    if not hasil_bersih:
        await update.message.reply_text(f"Maaf, setelah mencari di berbagai sumber, saya tidak menemukan paper yang cocok untuk topik '{query}'.")
        return

    
    unique_results = []
    seen_titles = set()
    for res in hasil_bersih:
        
        title_line = res.split('\n')[0] 
        if title_line not in seen_titles:
            unique_results.append(res)
            seen_titles.add(title_line)


    full_message = f"📚 Berikut adalah hasil gabungan terbaik dari berbagai sumber untuk '{query}':\n\n"
    full_message += "\n\n---\n\n".join(unique_results)
    
    await send_long_message(context, update.effective_chat.id, full_message)

def evaluation_generation_thread(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, loop: asyncio.AbstractEventLoop):
    """Fungsi di thread untuk mencari, membuat ringkasan, dan kuis evaluasi."""
    chat_id = update.effective_chat.id
    
    try:
        prompt = (
            f"Anda adalah seorang tutor ahli. Saya baru saja selesai mempelajari topik: '{topic}'.\n\n"
            "Tugas Anda adalah membuat paket evaluasi komprehensif berdasarkan topik ini. Lakukan langkah-langkah berikut:\n\n"
            "1.  **Lakukan Riset Mendalam**: Cari informasi yang akurat dan relevan tentang '{topic}'.\n"
            "2.  **Buat Ringkasan Poin Kunci**: Sajikan 3-5 poin paling penting dari topik ini dalam format bullet point. Gunakan *teks tebal* untuk menyorot istilah kunci.\n"
            "3.  **Buat Kuis Evaluasi**: Buat 5-7 pertanyaan yang beragam untuk menguji pemahaman. Campurkan jenis pertanyaan (misalnya, Pilihan Ganda, Benar/Salah, Esai Singkat).\n"
            "4.  **Format Output**: Kembalikan seluruh output dalam format JSON yang ketat. Strukturnya harus seperti ini:\n"
            "    ```json\n"
            "    {{\n"
            '        "topic": "{topic}",\n'
            '        "summary": ["Poin kunci pertama...", "Poin kunci kedua..."],\n'
            '        "quiz": [\n'
            '            {{"question_number": 1, "type": "Pilihan Ganda", "question": "...", "options": ["A. Opsi 1", "B. Opsi 2"], "answer": "..."}},\n'
            '            {{"question_number": 2, "type": "Benar/Salah", "question": "...", "answer": "Benar"}},\n'
            '            {{"question_number": 3, "type": "Esai Singkat", "question": "...", "answer": "Jawaban ideal..."}}\n'
            '        ]\n'
            '    }}\n'
            "    ```\n\n"
            "Pastikan JSON yang Anda hasilkan valid."
        )

        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        
        cleaned_json = re.search(r'```json\n(.*?)\n```', response.text, re.DOTALL)
        if not cleaned_json:
            raise ValueError("AI tidak mengembalikan format JSON yang valid.")
        
        eval_data = json.loads(cleaned_json.group(1))

        context.user_data['evaluation_data'] = eval_data
        context.user_data['current_question_index'] = 0
        context.user_data['user_answers'] = []

        asyncio.run_coroutine_threadsafe(start_evaluation_session(update, context), loop)

    except Exception as e:
        logger.error(f"Gagal membuat evaluasi untuk topik '{topic}': {e}")
        asyncio.run_coroutine_threadsafe(
            context.bot.send_message(chat_id=chat_id, text=f"Maaf, terjadi kesalahan saat membuat evaluasi: {e}"),
            loop
        )

async def start_evaluation_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai sesi evaluasi dengan mengirim ringkasan dan pertanyaan pertama."""
    eval_data = context.user_data.get('evaluation_data')
    if not eval_data: return

    summary_text = f"Berikut adalah poin-poin kunci untuk topik *{eval_data['topic']}*:\n\n"
    summary_text += "\n".join([f"• {point}" for point in eval_data['summary']])
    summary_text += "\n\nSekarang, mari kita mulai kuisnya!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=summary_text, parse_mode="Markdown")
    
    await asyncio.sleep(1)
    await ask_next_question(update, context)

async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim pertanyaan berikutnya dalam kuis."""
    eval_data = context.user_data['evaluation_data']
    current_index = context.user_data['current_question_index']
    question_data = eval_data['quiz'][current_index]
    
    question_text = f"*{question_data['type']}* ({current_index + 1}/{len(eval_data['quiz'])})\n\n{question_data['question']}"
    
    reply_markup = ReplyKeyboardRemove()
    if question_data.get('type') == 'Pilihan Ganda':
        reply_markup = ReplyKeyboardMarkup([[opt] for opt in question_data['options']], one_time_keyboard=True, resize_keyboard=True)
    elif question_data.get('type') == 'Benar/Salah':
        reply_markup = ReplyKeyboardMarkup([["Benar", "Salah"]], one_time_keyboard=True, resize_keyboard=True)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=question_text, parse_mode="Markdown", reply_markup=reply_markup)

async def get_study_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima topik dari pengguna dan memulai thread pembuatan evaluasi."""
    topic = update.message.text
    await update.message.reply_text(f"Baik! Saya akan membuat paket evaluasi untuk topik *'{topic}'*.\n\nMohon tunggu sebentar... 🧠", parse_mode="Markdown")
    
    
    loop = asyncio.get_running_loop()
    
    
    threading.Thread(
        target=evaluation_generation_thread, 
        args=(update, context, topic, loop) 
    ).start()
    
    return ANSWERING_EVALUATION

async def handle_evaluation_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani jawaban dari pengguna dan lanjut ke pertanyaan berikutnya atau menyimpulkan."""
    user_answer = update.message.text
    context.user_data['user_answers'].append(user_answer)
    
    current_index = context.user_data['current_question_index']
    total_questions = len(context.user_data['evaluation_data']['quiz'])
    
    context.user_data['current_question_index'] += 1
    
    if context.user_data['current_question_index'] < total_questions:
        await ask_next_question(update, context)
        return ANSWERING_EVALUATION
    else:
        await update.message.reply_text("Kuis selesai! Saya akan mengevaluasi jawaban Anda sekarang...", reply_markup=ReplyKeyboardRemove())
        loop = asyncio.get_running_loop()
        threading.Thread(
            target=final_scoring_thread, 
            args=(update, context, loop) 
        ).start()
        
        return ConversationHandler.END

def final_scoring_thread(update: Update, context: ContextTypes.DEFAULT_TYPE, loop: asyncio.AbstractEventLoop):
    """Thread untuk menilai semua jawaban dan memberikan umpan balik akhir."""
    chat_id = update.effective_chat.id
    
    try:
        eval_data = context.user_data['evaluation_data']
        user_answers = context.user_data['user_answers']
        
        prompt = (
            f"Anda adalah seorang guru yang sedang menilai hasil kuis. Berikut adalah data kuis dan jawaban siswa:\n"
            f"**Topik**: {eval_data['topic']}\n"
            f"**Detail Kuis (Soal dan Jawaban Benar)**:\n{json.dumps(eval_data['quiz'], indent=2, ensure_ascii=False)}\n"
            f"**Jawaban Siswa**:\n{json.dumps(user_answers, indent=2, ensure_ascii=False)}\n\n"
            "Tugas Anda:\n"
            "1.  **Beri Skor**: Hitung skor siswa. Beri 1 poin untuk setiap jawaban yang benar. Untuk esai, berikan penilaian subjektif (0, 0.5, atau 1) berdasarkan kedekatan dengan jawaban ideal.\n"
            "2.  **Hitung Total**: Tampilkan skor akhir dalam format 'Skor: X/Y'.\n"
            "3.  **Beri Umpan Balik**: Berdasarkan skor, berikan kesimpulan akhir yang membangun. Klasifikasikan pemahaman siswa menjadi salah satu dari tiga level:\n"
            "    - **Sangat Baik (Skor > 80%)**: Puji pemahaman mereka.\n"
            "    - **Cukup Baik (Skor 50-80%)**: Beri tahu apa yang sudah bagus dan sebutkan 1-2 area spesifik yang perlu diperkuat.\n"
            "    - **Perlu Belajar Lagi (Skor < 50%)**: Beri semangat dan sarankan untuk mempelajari kembali materi, terutama pada konsep yang salah dijawab.\n"
            "4.  **Sajikan Hasil**: Gabungkan semuanya dalam satu pesan yang jelas, terstruktur, dan gunakan Markdown."
        )

        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        final_feedback = response.text

        asyncio.run_coroutine_threadsafe(
            context.bot.send_message(chat_id=chat_id, text=final_feedback, parse_mode="Markdown"),
            loop
        )
    except Exception as e:
        logger.error(f"Gagal melakukan penilaian akhir: {e}")
        asyncio.run_coroutine_threadsafe(
            context.bot.send_message(chat_id=chat_id, text=f"Maaf, terjadi kesalahan saat menilai jawaban Anda: {e}"),
            loop
        )
    finally:
        context.user_data.clear()



async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Menangani file yang masuk dengan dua alur yang berbeda:
    1. Jika diminta (state 'awaiting_task_file'), HANYA buat rencana belajar.
    2. Jika dikirim langsung, HANYA ringkas dan sorot.
    """
    # Flag ini menjadi pembeda utama antara dua alur
    is_task_file_for_planning = context.user_data.get('state') == 'awaiting_task_file'
    
    document = update.message.document
    file = await document.get_file()
    
    input_files_dir = os.path.join(PROJECT_ROOT_DIR, 'input_files')
    os.makedirs(input_files_dir, exist_ok=True)
    file_path = os.path.join(input_files_dir, document.file_name)

    try:
        await file.download_to_drive(file_path)
    except Exception as e:
        logger.error(f"Gagal mengunduh file: {e}")
        await update.message.reply_text(f"Terjadi kesalahan saat mengunduh file: {e}")
        return

    try:
        loop = asyncio.get_running_loop()
        
        if is_task_file_for_planning:
            await update.message.reply_text("File tugas diterima! Membuat rencana kerja untuk Anda, mohon tunggu...")
            
            task_details = context.user_data.get('task_details', {})
            task_topic = task_details.get('topic', 'Tugas Anda')
            deadline = task_details.get('deadline', 'segera')
            
            file_content = ""
            if file_path.endswith('.pdf'):
                file_content = extract_text_from_pdf(file_path)
            elif file_path.endswith('.docx'):
                file_content = extract_text_from_docx(file_path)

            if file_content:
                plan = await loop.run_in_executor(None, generate_plan_from_text_sync, task_topic, deadline, file_content)
                await update.message.reply_text("✨ *Berikut adalah rencana kerja yang saya sarankan untuk tugas Anda:*")
                await send_long_message(context, update.effective_chat.id, plan)
            else:
                await update.message.reply_text("Gagal membaca konten file untuk dapat membuat rencana.")

        else:
            await update.message.reply_text("Menerima file, sedang memprosesnya untuk diringkas & disorot...")
            
            summary_path, highlighted_path = await loop.run_in_executor(None, process_file, file_path)
            
            if summary_path and os.path.exists(summary_path):
                with open(summary_path, 'rb') as f:
                    await update.message.reply_document(document=f, caption="Berikut adalah ringkasan dari dokumen Anda.")
            
            if highlighted_path and os.path.exists(highlighted_path):
                 with open(highlighted_path, 'rb') as f:
                    await update.message.reply_document(document=f, caption="Ini dokumen asli dengan bagian penting yang telah disorot.")

    except Exception as e:
        logger.error(f"Gagal memproses file: {e}")
        await update.message.reply_text(f"Maaf, terjadi kesalahan saat memproses file: {e}")
    finally:a
    context.user_data.clear()

async def handle_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima judul tugas dari pengguna dan meminta deadline."""
    task_title = update.message.text
    context.user_data['task_title'] = task_title
    
    await update.message.reply_text(
        f"Baik, judul tugas '{task_title}' telah disimpan.\n\n"
        "Sekarang, kapan deadline untuk tugas ini? (Contoh: 'besok jam 5 sore', 'Jumat ini 23:59')"
    )
    
    return GET_TASK_DEADLINE

async def get_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima deadline tugas dan meminta konfirmasi untuk membuat rencana."""
    
    deadline_text = update.message.text
    context.user_data['deadline_str'] = deadline_text
    task_title = context.user_data.get('task_title', 'Tugas Anda')


    keyboard = [
        [
            InlineKeyboardButton("✅ Ya, Buatkan Rencana", callback_data="create_plan"),
            InlineKeyboardButton("❌ Tidak Perlu", callback_data="cancel_plan"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)


    await update.message.reply_text(
        f"Oke, deadline untuk '{task_title}' adalah '{deadline_text}'.\n\n"
        "Apakah Anda ingin saya buatkan rencana kerja untuk tugas ini?",
        reply_markup=reply_markup,
    )


    return AWAITING_PLAN_CONFIRMATION

def process_file_sync(file_path: str) -> tuple[str, str]:
    """
    Fungsi sinkron yang melakukan pekerjaan berat: memproses file.
    Aman untuk dijalankan di dalam executor.
    """
    if not file_path:
        raise ValueError("Path file tidak valid.")
    
    summary_path, highlighted_path = process_file(file_path)
    return summary_path, highlighted_path


async def send_summary_results(update: Update, context: ContextTypes.DEFAULT_TYPE, summary_path: str, highlighted_path: str):
    """
    Mengirim hasil ringkasan dan file yang disorot dengan aman.
    Fungsi ini sekarang memeriksa apakah path file valid sebelum mencoba mengirim.
    """
    await update.message.reply_text("✅ Proses selesai! Berikut adalah hasilnya:")
    
    file_sent = False
    try:
        
        if summary_path and os.path.exists(summary_path):
            with open(summary_path, 'rb') as summary_file:
                await update.message.reply_document(
                    document=summary_file,
                    caption="Ini adalah ringkasan dari dokumen Anda."
                )
            file_sent = True
        else:
            logger.warning(f"File ringkasan tidak ditemukan atau path-nya None: {summary_path}")

        
        if highlighted_path and os.path.exists(highlighted_path):
            with open(highlighted_path, 'rb') as highlighted_file:
                await update.message.reply_document(
                    document=highlighted_file,
                    caption="Ini adalah dokumen asli dengan bagian-bagian penting yang telah disorot."
                )
            file_sent = True
        else:
            logger.warning(f"File sorotan tidak ditemukan atau path-nya None: {highlighted_path}")

       
        if not file_sent:
            await update.message.reply_text("Meskipun proses selesai, tidak ada file hasil yang bisa dikirim.")

    except Exception as e:
        logger.error(f"Gagal mengirim file hasil: {e}")
        await update.message.reply_text(f"Terjadi kesalahan saat mengirim file hasil: {e}")
    finally:
        
        if context.user_data:
            context.user_data.clear()

async def handle_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani jawaban waktu dari pengguna dan menyelesaikan pembuatan reminder."""
    user_time_text = update.message.text
    chat_id = update.effective_chat.id
    
    pending_reminder = context.user_data.pop('pending_reminder', None)
    context.user_data.pop('next_step', None)

    if not pending_reminder:
        await update.message.reply_text("Maaf, sesi ini sepertinya sudah berakhir. Silakan coba buat reminder lagi dari awal.")
        return

    await update.message.reply_text(f"Oke, jam '{user_time_text}' diterima. Mencoba membuat reminder lengkap...")

    final_deadline_str = f"{pending_reminder['date']} {user_time_text}"

    prompt = (
        f"Validasi dan format ulang teks berikut menjadi format YYYY-MM-DD HH:MM yang ketat. Waktu saat ini adalah {datetime.now().strftime('%Y-%m-%d %H:%M')} untuk referensi.\n"
        f"Teks Input: '{final_deadline_str}'\n\n"
        "Contoh:\n"
        "Input: '2025-08-31 jam 5 sore' -> Hasil: '2025-08-31 17:00'\n"
        "Input: '2025-09-01 9 pagi' -> Hasil: '2025-09-01 09:00'\n"
        "Hasil:"
    )
    
    cleaned_deadline = call_gemini_for_plan(prompt).strip().replace("'", "")

    try:
        datetime.strptime(cleaned_deadline, "%Y-%m-%d %H:%M")
        
        title = pending_reminder['title']
        is_assignment = pending_reminder.get('is_assignment', False)

        result_message = create_calendar_event(title, cleaned_deadline)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Siap! Reminder berhasil dibuat di kalender!\n\n{result_message}",
            parse_mode="Markdown"
        )

        if is_assignment:
            context.user_data['state'] = 'awaiting_task_file'
            context.user_data['task_details'] = {'topic': title, 'deadline': cleaned_deadline}
            
            await update.message.reply_text(
                "Karena ini adalah sebuah tugas, apakah Anda ingin saya buatkan juga rencana belajarnya? "
                "Jika ya, silakan kirim file materinya sekarang."
            )

    except (ValueError, TypeError):
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Maaf, saya kesulitan memahami waktu '{user_time_text}'. Coba lagi dengan format yang lebih umum (contoh: 'jam 1 siang', '14:30')."
        )

async def handle_natural_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mendeteksi niat pengguna dan merutekannya ke fungsi yang sesuai."""
    
    if context.user_data.get('next_step') == 'get_reminder_time':
        await handle_reminder_time(update, context)
        return

    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    classification = classify_intent(user_text)
    intent = classification.get("intent")
    
    if intent == "create_task_plan":
        context.user_data['state'] = 'awaiting_task_file'
        context.user_data['task_details'] = {
            'topic': classification.get('topic', 'Tugas'),
            'deadline': classification.get('deadline', 'Tidak ditentukan')
        }
        await update.message.reply_text(
            "Tentu, saya bisa bantu membuatkan rencana untuk tugas Anda. "
            "Silakan kirim file tugasnya (.pdf atau .docx) agar saya bisa menganalisisnya lebih dalam."
        )

    elif intent == "create_reminder":
        details_text = classification.get("details")
        if not details_text:
            await update.message.reply_text("Maaf, saya tidak bisa memahami detail reminder Anda.")
            return

        await update.message.reply_text("Oke, saya coba proses permintaan reminder Anda...")
        is_assignment = 'tugas' in details_text.lower() or 'pr' in details_text.lower()

        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt = (
            f"Anda adalah AI ahli dalam mengekstrak informasi waktu. Ubah permintaan pengguna menjadi JSON. Gunakan waktu saat ini sebagai referensi.\n"
            f"Jika pengguna tidak menyebutkan jam, KEMBALIKAN HANYA TANGGAL dalam format YYYY-MM-DD.\n"
            f"Waktu Saat Ini: {current_time_str}\n\n"
            "--- CONTOH ---\n"
            "Teks: 'ada rapat tim besok jam 2 siang'\n"
            'Hasil: {{"title": "Rapat tim", "deadline": "2025-08-25 14:00"}}\n\n'
            "Teks: 'ingatkan saya deadline tugas metlit minggu depan'\n"
            'Hasil: {{"title": "Deadline tugas metlit", "deadline": "2025-08-31"}}\n\n'
            "--- ANALISIS TEKS BERIKUT ---\n"
            f"Teks: '{details_text}'\n"
            "Hasil:"
        )
        
        response_text = call_gemini_for_plan(prompt)
        try:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not match:
                raise ValueError("AI tidak mengembalikan format JSON yang valid.")

            details = json.loads(match.group(0))
            title = details.get("title")
            deadline = details.get("deadline")

            if not deadline:
                await update.message.reply_text("Saya tidak bisa menemukan waktu sama sekali. Coba lagi dengan lebih spesifik.")
                return

            if re.match(r'^\d{4}-\d{2}-\d{2}$', deadline):
                context.user_data['pending_reminder'] = {
                    'title': title, 
                    'date': deadline,
                    'is_assignment': is_assignment 
                }
                context.user_data['next_step'] = 'get_reminder_time'
                
                human_date = datetime.strptime(deadline, "%Y-%m-%d").strftime("%A, %d %B %Y")
                await update.message.reply_text(f"Oke, saya catat untuk '{title}' pada tanggal {human_date}.\n\nJam berapa tepatnya?")
                return
            
            result_message = create_calendar_event(title, deadline)
            await update.message.reply_text(
                f"✅ Reminder berhasil dibuat di kalender!\n\n{result_message}", 
                parse_mode="Markdown"
            )

            if is_assignment:
                context.user_data['state'] = 'awaiting_task_file'
                context.user_data['task_details'] = {'topic': title, 'deadline': deadline}
                
                await update.message.reply_text(
                    "Karena ini adalah sebuah tugas, apakah Anda ingin saya buatkan juga rencana belajarnya? "
                    "Jika ya, silakan kirim file materinya sekarang."
                )

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Error memproses reminder: {e} - Respon AI: {response_text}")
            await update.message.reply_text(f"Maaf, saya kesulitan memahami waktu dari '{details_text}'. Coba lebih spesifik.")
    
    elif intent == "find_paper":
        topic = classification.get("topic")
        if topic:
            await update.message.reply_text(f"🔎 Siap! Saya cari paper tentang '{topic}'...")
            hasil_arxiv = cari_paper_ilmiah(topic, max_results=2)
            hasil_ss = cari_paper_semantic_scholar(topic, max_results=2)
            
            hasil_gabungan = hasil_ss + hasil_arxiv
            hasil_bersih = [res for res in hasil_gabungan if not res.startswith("Gagal")]

            if not hasil_bersih:
                await update.message.reply_text(f"Maaf, saya tidak menemukan paper yang cocok untuk topik '{topic}'.")
                return
            
            unique_results = list(dict.fromkeys(hasil_bersih))
            full_message = f"📚 Berikut adalah hasil pencarian untuk '{topic}':\n\n"
            full_message += "\n\n---\n\n".join(unique_results)
            await send_long_message(context, chat_id, full_message)
        else:
            await update.message.reply_text("Saya mengerti Anda ingin mencari paper, tapi bisa sebutkan topiknya?")

    elif intent == "greeting":
        await update.message.reply_text("Halo! Ada yang bisa saya bantu? 😊")

    else:
        await update.message.reply_text("Maaf, saya tidak begitu mengerti maksud Anda. Bisa coba dengan kalimat lain?")
        logger.warning(f"Intent tidak diketahui atau error untuk teks: '{user_text}'. Detail: {classification.get('details')}")

# FUNGSI UNTUK MENJALANKAN BOT
def run_bot():
    """Mengkonfigurasi dan menjalankan aplikasi bot."""
    if not TELEGRAM_BOT_TOKEN: 
        logger.error("Token tidak ditemukan. Pastikan TELEGRAM_BOT_TOKEN ada di file .env Anda.")
        return

    persistence = PicklePersistence(filepath="bot_persistence")
    
    request = HTTPXRequest(connect_timeout=10.0, read_timeout=60.0, write_timeout=30.0)
    
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .request(request)
        .build()
    )



    # 1. Conversation handler untuk alur /stopfokus -> evaluasi
    evaluation_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("stopfokus", stop_focus_mode)],
        states={
            GET_STUDY_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_study_topic)],
            ANSWERING_EVALUATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_evaluation_answer)],
        },
        fallbacks=[CommandHandler("batal", cancel_command)],
        conversation_timeout=600 # 10 menit timeout
    )

    # 2. Conversation handler untuk alur file -> ringkas/reminder -> rencana
    file_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Document.ALL, file_handler)],
        states={
            CHOOSE_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, CHOOSE_ACTION)],
            GET_TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_title)],
            GET_TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_deadline)],
            AWAITING_PLAN_CONFIRMATION: [CallbackQueryHandler(handle_plan_decision)],
        },
        fallbacks=[CommandHandler("batal", cancel_command)],
    )

    # --- HANDLER ---

    application.add_error_handler(error_handler)
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("fokus", start_focus_mode))
    application.add_handler(CommandHandler("paper", paper_command_handler))
    application.add_handler(evaluation_conv_handler)
    application.add_handler(file_conv_handler) 
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_text))

    logger.info("🤖 Bot Telegram sedang mendengarkan...")
    application.run_polling()

if __name__ == '__main__':
    run_bot()