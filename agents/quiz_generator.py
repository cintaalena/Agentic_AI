import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_quiz(text: str, quiz_type: str) -> str:
    """
    Membuat kuis dalam format JSON.
    - Pilihan Ganda: {question, options, correct_answer}
    - Esai: {question, ideal_answer}
    """
    print(f" -> Agen Kuis: Memulai pembuatan kuis tipe '{quiz_type}' dalam format JSON...")
    
    if not GEMINI_API_KEY:
        return json.dumps({"error": "Kunci API Gemini tidak ditemukan."})

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = ""
        
        if quiz_type == "Pilihan Ganda":
            prompt = (
                "Anda adalah ahli pembuat soal. Berdasarkan teks berikut, buatlah 5 pertanyaan pilihan ganda. "
                "Respon WAJIB dalam format JSON yang valid. JSON harus berupa sebuah array dari objek. "
                "Setiap objek harus memiliki tiga kunci: 'question' (string), 'options' (sebuah array berisi 4 string pilihan jawaban), dan 'correct_answer' (string berisi jawaban yang benar persis seperti salah satu opsi). "
                "JANGAN tambahkan teks atau format markdown apa pun sebelum atau sesudah blok JSON.\n\n"
                f"--- TEKS DOKUMEN ---\n{text[:15000]}\n\n--- AKHIR TEKS ---\n\n"
            )
        elif quiz_type == "Esai":
            prompt = (
                "Anda adalah seorang dosen ahli. Berdasarkan teks berikut, buatlah 3 pertanyaan esai yang mendalam dan analitis. "
                "Respon WAJIB dalam format JSON yang valid. JSON harus berupa sebuah array dari objek. "
                "Setiap objek harus memiliki dua kunci: 'question' (string berisi pertanyaan) dan 'ideal_answer' (string berisi jawaban ideal yang komprehensif untuk pertanyaan tersebut). "
                "JANGAN tambahkan teks atau format markdown apa pun sebelum atau sesudah blok JSON.\n\n"
                f"--- TEKS DOKUMEN ---\n{text[:15000]}\n\n--- AKHIR TEKS ---\n\n"
            )
        else:
            return json.dumps({"error": "Tipe kuis tidak valid."})

        response = model.generate_content(prompt)
        
        if response.parts:
            try:
                cleaned_text = re.search(r'\[.*\]', response.text, re.DOTALL).group(0)
                print(" -> Kuis JSON berhasil dibuat oleh Gemini API.")
                return cleaned_text
            except AttributeError:
                print(" -> Gagal menemukan format JSON di respons API.")
                return json.dumps({"error": "AI tidak memberikan format JSON yang benar."})
        else:
            return json.dumps({"error": "API tidak memberikan hasil."})

    except Exception as e:
        print(f" -> Terjadi error saat memanggil Gemini API untuk kuis: {e}")
        return json.dumps({"error": f"Gagal menghubungi layanan AI: {e}"})

def score_essay_answer(ideal_answer: str, user_answer: str) -> int:
    """Membandingkan jawaban pengguna dengan jawaban ideal dan memberikan skor 1-100."""
    print(" -> Agen Penilai: Memulai penilaian jawaban esai...")
    if not GEMINI_API_KEY:
        return 0
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Anda adalah seorang asisten dosen yang tugasnya menilai jawaban esai. "
            "Bandingkan 'Jawaban Mahasiswa' dengan 'Kunci Jawaban Ideal' berdasarkan kesamaan konsep dan substansi. "
            "Abaikan perbedaan gaya bahasa atau panjang kalimat. Berikan skor kemiripan dari 1 hingga 100. "
            "RESPON ANDA HANYA BOLEH BERUPA ANGKA SAJA (contoh: 85). Jangan tambahkan teks atau penjelasan lain.\n\n"
            f"--- KUNCI JAWABAN IDEAL ---\n{ideal_answer}\n\n"
            f"--- JAWABAN MAHASISWA ---\n{user_answer}\n\n"
            "SKOR (1-100):"
        )
        response = model.generate_content(prompt)
        
        # Ekstrak hanya angka dari respons
        score_text = ''.join(filter(str.isdigit, response.text))
        if score_text:
            score = int(score_text)
            print(f" -> Skor yang diberikan: {score}")
            return score
        return 0
    except Exception as e:
        print(f" -> Gagal memberikan skor: {e}")
        return 0