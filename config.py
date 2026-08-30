import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
SECRETS_FILE = os.path.join(BASE_DIR, "secrets.json")
ACTIVE_CHAT_FILE = os.path.join(BASE_DIR, "active_chat.json")
INBOX_FILE = os.path.join(BASE_DIR, "inbox.json")
VOICE_SETTINGS_FILE = os.path.join(BASE_DIR, "voice_settings.json")

def is_voice_enabled() -> bool:
    """Проверка, включено ли голосовое сопровождение ответов."""
    if os.path.exists(VOICE_SETTINGS_FILE):
        try:
            with open(VOICE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("enabled", True))
        except Exception:
            pass
    return True

def set_voice_enabled(enabled: bool) -> bool:
    """Включение или отключение голосового сопровождения ответов."""
    data = {"enabled": enabled}
    try:
        with open(VOICE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def load_dotenv():
    """Загрузка переменных из .env без внешних зависимостей."""
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

def load_secrets_json():
    """Фоллбэк загрузка из secrets.json, если .env не задан."""
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k not in os.environ:
                        if isinstance(v, (list, dict)):
                            os.environ[k] = json.dumps(v)
                        else:
                            os.environ[k] = str(v)
        except Exception:
            pass

load_dotenv()
load_secrets_json()

# Конфигурационные переменные
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
RECEIVER_PORT = int(os.environ.get("RECEIVER_PORT", "8080"))

def get_active_chat_id():
    if os.path.exists(ACTIVE_CHAT_FILE):
        try:
            with open(ACTIVE_CHAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("chat_id")
        except Exception:
            pass
    return None

def set_active_chat(chat_id, user_info=None):
    data = {"chat_id": chat_id, "user_info": user_info or {}}
    with open(ACTIVE_CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
