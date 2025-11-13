import os
from pathlib import Path
from django.conf import settings
from dotenv import load_dotenv

def load_env():
    base_dir = getattr(settings, "BASE_DIR", Path(__file__).resolve().parent)
    env_path = Path(base_dir) / ".env"
    if env_path.exists():
        load_dotenv(env_path)

def get_env_key(key: str) -> str | None:
    value = getattr(settings, key, None)
    if value:
        return value
    if not os.getenv(key):
        load_env()
    return os.getenv(key)

def get_chapa_secret_key() -> str | None:
    return get_env_key("CHAPA_SECRET_KEY")

def get_chapa_public_key() -> str | None:
    return get_env_key("CHAPA_PUBLIC_KEY")
