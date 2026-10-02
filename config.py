"""Local configuration for OneMoreRep. Set credentials via environment variables."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).parent / ".env")

DB_HOST = os.getenv("ONEMOREREP_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("ONEMOREREP_DB_PORT", "5432"))
DB_USER = os.getenv("ONEMOREREP_DB_USER", "postgres")
try:
    from config_local import DB_PASSWORD as LOCAL_DB_PASSWORD
except ImportError:
    LOCAL_DB_PASSWORD = ""
DB_PASSWORD = os.getenv("ONEMOREREP_DB_PASSWORD", LOCAL_DB_PASSWORD)
DB_NAME = os.getenv("ONEMOREREP_DB_NAME", "onemorerep")
SESSION_COOKIE_NAME = "onemorerep_session"
SESSION_COOKIE_SECURE = os.getenv("ONEMOREREP_COOKIE_SECURE", "true" if os.getenv("VERCEL") else "false").lower() == "true"
UPLOAD_DIR = Path(os.getenv("ONEMOREREP_UPLOAD_DIR", str(Path(__file__).parent / "uploads")))
CORS_ORIGINS = [origin.strip() for origin in os.getenv(
    "ONEMOREREP_CORS_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000"
).split(",") if origin.strip()]
MEDIA_STORAGE = os.getenv("ONEMOREREP_MEDIA_STORAGE", "local").strip().lower()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "onemorerep-private").strip()

MORNING_START = "05:00:00"
MORNING_END = "11:59:59"
EVENING_START = "17:00:00"
EVENING_END = "23:59:59"
