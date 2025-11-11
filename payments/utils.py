import os
from pathlib import Path
from django.conf import settings

def _parse_and_set_env(path: Path):
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass

def _ensure_env_loaded():
    try:
        from dotenv import load_dotenv
    except Exception:
        load_dotenv = None

    if load_dotenv:
        try:
            base = getattr(settings, "BASE_DIR", None)
            if base:
                env_path = Path(base) / ".env"
                load_dotenv(env_path if env_path.exists() else None)
            else:
                load_dotenv()
        except Exception:
            load_dotenv()

    if not os.getenv("CHAPA_SECRET_KEY"):
        candidates = []
        try:
            base = getattr(settings, "BASE_DIR", None)
            if base:
                candidates.append(Path(base) / ".env")
        except Exception:
            pass

        here = Path(__file__).resolve()
        for p in [here.parent / ".env"] + [parent / ".env" for parent in list(here.parents)[:4]]:
            if p and p.exists():
                candidates.append(p)

        for c in candidates:
            if c and c.exists():
                _parse_and_set_env(c)
                if os.getenv("CHAPA_SECRET_KEY"):
                    break

def get_chapa_secret_key() -> str | None:
    key = getattr(settings, "CHAPA_SECRET_KEY", None)
    if key:
        return key
    _ensure_env_loaded()
    return os.getenv("CHAPA_SECRET_KEY")

def get_chapa_public_key() -> str | None:
    key = getattr(settings, "CHAPA_PUBLIC_KEY", None)
    if key:
        return key
    _ensure_env_loaded()
    return os.getenv("CHAPA_PUBLIC_KEY")
