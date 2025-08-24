import os
import logging
from agents.telegram_agent import run_bot


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

if __name__ == "__main__":
    print("=====================================================")
    print("===== Agentic AI Akademik - Mode Interaktif Bot =====")
    print("=====================================================")
    
    os.makedirs('input_files', exist_ok=True)
    os.makedirs('output_files', exist_ok=True)
    
    try:
        logging.info("Memulai Telegram bot...")
        run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Sistem dihentikan oleh pengguna.")
    except Exception as e:
        print(f"❌ Terjadi error fatal: {e}")
    finally:
        print("✅ Sistem berhasil dihentikan.")