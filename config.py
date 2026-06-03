import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY tidak ditemukan. "
        "Pastikan file .env sudah diisi sesuai .env.example"
    )

CORS_ORIGINS: list[str] = ["*"]
GEMINI_MODEL: str = "gemini-3.1-flash-image-preview"
