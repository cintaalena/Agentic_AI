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

##workflow kerja 

<img width="2048" height="2048" alt="Gemini_Generated_Image_l3nf6rl3nf6rl3nf" src="https://github.com/user-attachments/assets/928f5734-0e0d-4331-a17a-7d4fa2064b42" />


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

## Model Bahasa (LLM) 🧠
Yang Digunakan: Google Gemini API (Cloud-based).

Keterangan: Seluruh kecerdasan buatan sistem ini ditenagai oleh model Gemini milik Google. Aplikasi ini harus terhubung ke internet dan memiliki API key yang valid untuk bisa berfungsi.

## Arsitektur Agen 🤖
Jenis: Single-Agent dari segi implementasi, namun dirancang dengan pola Multi-Agent secara konseptual.

Keterangan: Program berjalan sebagai satu proses tunggal (single-agent), tetapi desainnya sangat modular, menyerupai tim spesialis (summarizer_highlighter, quiz_generator) yang dikoordinasikan oleh satu manajer utama.

## Database 🗄️
Jenis: Penyimpanan Berbasis File (JSON & Pickle).

Keterangan: Sistem ini menggunakan file sederhana untuk menyimpan data sementara seperti daftar tugas, status mode fokus, dan "ingatan" percakapan bot. Ini adalah ciri khas prototipe, bukan aplikasi skala produksi.

## ⚙️ Panduan Instalasi & Konfigurasi

##▶️ Cara Menjalankan Bot Utama
Pastikan virtual environment Anda sudah aktif.

Jalankan script utama:

python main.py
Bot Anda sekarang aktif dan siap menerima perintah di Telegram!
