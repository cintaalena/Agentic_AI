# N.E.R.D - Telegram Bot

Sebuah bot Telegram cerdas yang dirancang untuk membantu mahasiswa dan akademisi dalam mengelola tugas-tugas mereka. Bot ini menggunakan kekuatan AI generatif (Google Gemini) untuk memahami bahasa alami dan mengotomatiskan berbagai pekerjaan seperti meringkas dokumen, menyorot poin penting, mengelola jadwal, dan mencari referensi ilmiah.

## ✨ Fitur Utama

-   **Peringkas & Penyorot Dokumen Cerdas**: Cukup kirim file `.pdf` atau `.docx`, dan bot akan secara otomatis:
    -   Membuat ringkasan analitis dari isi dokumen menggunakan AI.
    -   Membuat salinan dokumen asli dengan bagian-bagian paling penting yang sudah ditandai (highlighted).
-   **Pengingat Bahasa Alami**: Buat pengingat atau acara di kalender hanya dengan mengirim pesan biasa.
    -   **Contoh**: *"ingatkan saya ada ujian kalkulus hari jumat jam 10 pagi"*
    -   Bot akan memproses permintaan ini dan secara otomatis membuat acara di Google Calendar Anda.
-   **Pencari Paper Ilmiah**: Temukan referensi dan paper dengan cepat dari berbagai sumber akademis.
    -   **Command**: `/paper [topik penelitian]`
    -   Bot akan mencari di database seperti arXiv dan Semantic Scholar dan memberikan daftar paper yang relevan.
-   **Mode Fokus & Evaluasi**:
    -   `/fokus`: Mengirim sinyal untuk memulai sesi belajar.
    -   `/stopfokus`: Mengakhiri sesi dan secara otomatis memicu sesi evaluasi, di mana bot akan membuat kuis singkat tentang topik yang baru dipelajari untuk menguji pemahaman.
-   **Routing Niat Cerdas**: Bot dapat membedakan antara berbagai jenis permintaan (misalnya, membuat pengingat vs. mencari paper) tanpa perlu perintah yang kaku, sehingga interaksi terasa lebih natural.

## 🤫 Fitur Lanjutan: Listener Mode Fokus Lokal

Fitur ini bersifat **opsional dan ditujukan untuk pengguna tingkat lanjut**. Script `local_listener.py` berinteraksi langsung dengan sistem operasi Anda (misalnya, memodifikasi file `hosts` untuk memblokir situs web) dan **memerlukan hak Administrator** untuk berjalan. Gunakan dengan hati-hati.

### Cara Kerja
-   Script `local_listener.py` berfungsi sebagai jembatan antara bot Telegram dengan laptop Anda.
-   Ketika Anda mengetik `/fokus` di Telegram, bot akan mengirim sinyal `START_FOCUS` ke sebuah channel khusus.
-   `local_listener.py` yang berjalan di laptop Anda akan menangkap sinyal ini dan mengaktifkan mode fokus dengan cara memblokir akses ke situs-situs yang mengganggu (misalnya, media sosial).
-   Ketika Anda mengetik `/stopfokus`, sinyal `STOP_FOCUS` akan dikirim untuk menonaktifkan pemblokiran dan mengembalikan sistem Anda seperti semula.

### Cara Menjalankan
1.  Klik kanan pada **Command Prompt (CMD)** atau **PowerShell**, lalu pilih **"Run as administrator"**.
2.  Arahkan ke direktori proyek Anda: `cd path\to\your\project`
3.  Aktifkan virtual environment: `.\venv\Scripts\activate`
4.  Jalankan listener: `python agents\local_listener.py`
5.  **Biarkan jendela terminal ini tetap terbuka** selama Anda ingin mode fokus aktif. Menutupnya akan menghentikan listener.


## 🚀 Teknologi yang Digunakan

-   **Bahasa**: Python 3
-   **Library Utama**:
    -   `python-telegram-bot`: Untuk interaksi dengan API Telegram.
    -   `google-generativeai`: Untuk terhubung dengan model AI Google Gemini.
    -   `spacy`: Untuk pemrosesan bahasa alami (NLP) tingkat lanjut.
    -   `PyMuPDF (fitz)` & `python-docx`: Untuk membaca dan memanipulasi file PDF dan DOCX.
    -   `google-api-python-client`: Untuk integrasi dengan Google Calendar.
-   **Platform**: Telegram
-   **AI Model**: Google Gemini 1.5 Flash

## ⚙️ Panduan Instalasi & Konfigurasi

Berikut adalah langkah-langkah untuk menjalankan bot ini di komputer Anda sendiri.

### 1. Clone Repository
Salin proyek ini ke komputer Anda.

git clone 
cd Agentic_AI

###2. Buat dan Aktifkan Virtual Environment
Sangat disarankan untuk menggunakan lingkungan virtual agar tidak mengganggu instalasi Python utama Anda.

# Buat venv
python -m venv venv

# Aktifkan venv (untuk Windows)
.\venv\Scripts\activate

##3. Instal Semua Paket yang Dibutuhkan
Instal semua library yang diperlukan dengan perintah berikut:

pip install --upgrade pip
pip install python-telegram-bot google-generativeai python-dotenv spacy PyMuPDF python-docx langdetect nltk httpx "python-telegram-bot[job-queue]" google-api-python-client google-auth-httplib2 google-auth-oauthlib

#Setelah itu, unduh model bahasa untuk Spacy:
python -m spacy download en_core_web_sm
python -m spacy download xx_ent_wiki_sm

##4. Konfigurasi Kunci API (.env)
Buat sebuah file baru di folder utama proyek dengan nama .env. File ini akan berisi semua kunci rahasia Anda.

# Ganti dengan token dari BotFather di Telegram
TELEGRAM_BOT_TOKEN="XXXXXXXXXXXXXXXXXXXXX"

# Ganti dengan API Key dari Google AI Studio
GEMINI_API_KEY="XXXXXXXXXXXXXXXXXXXXX"

# (Opsional) Ganti dengan ID channel Telegram untuk fitur Mode Fokus
TELEGRAM_CHANNEL_ID="XXXXXXXXXXXXXXXX"

#Konfigurasi Google Calendar API
Untuk fitur pengingat, Anda memerlukan akses ke Google Calendar API.

Ikuti panduan Google untuk membuat OAuth 2.0 Client ID.

Unduh file JSON yang diberikan dan ganti namanya menjadi credentials.json, lalu letakkan di folder utama proyek Anda.

Saat pertama kali menjalankan fitur pengingat, bot akan membuka browser dan meminta Anda untuk login dan memberikan izin. Proses ini akan secara otomatis membuat file token.json untuk sesi berikutnya.

##▶️ Cara Menjalankan Bot Utama
Pastikan virtual environment Anda sudah aktif.

Jalankan script utama:

python main.py
Bot Anda sekarang aktif dan siap menerima perintah di Telegram!
