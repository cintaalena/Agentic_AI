import google.generativeai as genai
import logging
import json
import re
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY tidak ditemukan di environment.")

genai.configure(api_key=GEMINI_API_KEY)

def classify_intent(user_text: str) -> dict:
    """
    Menggunakan Gemini untuk mengklasifikasikan niat pengguna dan mengekstrak entitas.
    """
    try:
        genai.get_model('models/gemini-1.5-flash-latest')
    except Exception:
        logger.error("Gemini API key tidak terkonfigurasi atau model tidak ditemukan.")
        return {"intent": "error", "details": "Konfigurasi AI tidak valid."}

    prompt = f"""
    Analisis niat dari teks pengguna. Balas HANYA dengan JSON yang valid.
    Pilihan niat: 'create_reminder', 'find_paper', 'create_task_plan', 'greeting', 'unknown'.

    ATURAN PENTING:
    - Jika pengguna menyebutkan "tugas" atau "PR" DAN juga kata seperti "rencana", "bantuan", "kerjakan", atau "buatkan", niatnya adalah 'create_task_plan'.
    - Jika pengguna HANYA ingin "diingatkan" tentang sesuatu (bahkan jika itu tugas), niatnya adalah 'create_reminder'. Prioritaskan 'create_task_plan' jika ada permintaan untuk bantuan.

    Contoh:
    Teks: "ingatkan aku ada rapat besok jam 3 sore"
    JSON: {{"intent": "create_reminder", "details": "rapat besok jam 3 sore"}}

    Teks: "ingatkan saya deadline tugas ssdlc hari jumat"
    JSON: {{"intent": "create_reminder", "details": "deadline tugas ssdlc hari jumat"}}

    Teks: "carikan saya paper tentang dampak AI pada pendidikan"
    JSON: {{"intent": "find_paper", "topic": "dampak AI pada pendidikan"}}
    
    Teks: "saya ada tugas makalah, tolong buatkan rencananya"
    JSON: {{"intent": "create_task_plan", "topic": "tugas makalah", "deadline": null}}

    Teks: "saya ada tugas dkp deadline besok, butuh bantuan mengerjakannya"
    JSON: {{"intent": "create_task_plan", "topic": "tugas dkp", "deadline": "besok"}}

    Teks: "halo apa kabar"
    JSON: {{"intent": "greeting"}}

    ---
    Teks Pengguna: "{user_text}"
    JSON:
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        ai_output = response.text.strip()
        
        match = re.search(r'\{.*\}', ai_output, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            logger.error(f"Output Gemini tidak mengandung JSON: {ai_output}")
            return {"intent": "unknown", "details": "Gagal mengekstrak JSON dari AI."}
        
        result = json.loads(json_text)
        logger.info(f"Intent classified for '{user_text}': {result}")
        return result
    
    except json.JSONDecodeError:
        logger.error(f"Output Gemini bukan JSON valid: {json_text}")
        return {"intent": "unknown", "details": ai_output}

    except Exception as e:
        logger.error(f"Error saat klasifikasi niat: {e}")
        return {"intent": "error", "details": str(e)}
