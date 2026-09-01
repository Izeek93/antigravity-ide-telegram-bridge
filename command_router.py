"""
tg-bot/command_router.py
========================
Модульный роутер и обработчик сервисных слэш-команд Telegram моста.
Принцип:
- Строго слэш-команды (/new, /screen, /voice, /limits, /tasks, /status, /free, /help).
- Никаких перехватов обычных слов естественного языка.
- Все текстовые сообщения без слэша гарантированно направляются в очередь IDE.
"""

import os
import sys
import time
from send_tg import send_message, send_photo, ActionKeeper, REMOVE_REPLY_KEYBOARD
from screenshot import capture_desktop
from queue_manager import push_message
from model_lifecycle import stop_comfyui_process
from session_manager import start_new_ide_session

# Множества для удаленного интерактивного подтверждения (только при активном запросе)
APPROVAL_AFFIRMATIVE = {
    "да", "подтверждаю", "разрешаю", "ок", "выполняй", "approve", "/approve", "/yes", "1",
    "✅ подтвердить", "подтвердить", "✅ да", "подтверждаю действие"
}
APPROVAL_NEGATIVE = {
    "нет", "отмена", "отклонить", "не надо", "reject", "/reject", "/no", "0",
    "❌ отклонить", "отклонить", "❌ нет", "отменить"
}



def handle_new(chat_id: int | str, user: str, args: str = "") -> bool:
    # Запускаем открытие чистого чата через CLI Antigravity
    prompt_text = args.strip() if args else "Старт новой сессии через Telegram-мост."
    start_new_ide_session(prompt_text)
    
    push_message({
        "source": "TELEGRAM",
        "chat_id": chat_id,
        "user": user,
        "text": f"[SYSTEM_EVENT]: Создана новая сессия в IDE через команду /new. Тема: {prompt_text}",
        "timestamp": time.time()
    })
    send_message(
        "✨ **Новая сессия открыта в Antigravity IDE!**\n\n"
        "• В IDE открыт чистый чат через CLI (`antigravity-ide chat`).\n"
        "• Контекст сброшен на 0%.\n"
        "• Долговременная память (`Qdrant`) и 7 навыков активны.\n\n"
        "💬 *Я готова к новой задаче. Напишите текст или надиктуйте голосовое сообщение прямо сюда.*",
        chat_id=chat_id
    )
    return True

def handle_help(chat_id: int | str, user: str, args: str = "") -> bool:
    send_message(
        "👋 Привет! Этот бот работает как **прямое зеркало активной сессии Antigravity IDE**.\n\n"
        "📌 Команды в нативном меню **`[ Menu ☰ ]`**:\n"
        "• `/new` — 🔄 Начать новую чистую сессию\n"
        "• `/screen` — 📸 Скриншот рабочего стола\n"
        "• `/voice` — 🔊 Включить/выключить голосовые ответы\n"
        "• `/limits` — ⏳ Квоты и телеметрия IDE\n"
        "• `/tasks` — ⚙️ Фоновые задачи и процессы\n"
        "• `/status` — 📊 Статус подключения IDE\n"
        "• `/help` — ℹ️ Справка и возможности\n\n"
        "✨ *Текстовые и голосовые сообщения передаются прямо агенту в IDE.*",
        chat_id=chat_id,
        reply_markup=REMOVE_REPLY_KEYBOARD
    )
    return True

def handle_status(chat_id: int | str, user: str, args: str = "") -> bool:
    from config import is_voice_enabled
    from bridge_health_watchdog import run_self_healing_health_check
    diag = run_self_healing_health_check()
    v_status = "🔊 Включено" if is_voice_enabled() else "🔇 Выключено (только текст)"
    heal_info = "🟢 Без сбоев" if not diag["lock_healed"] and not diag["inbox_healed"] else "🛠 Выполнено автовосстановление"
    send_message(
        f"🟢 **Antigravity IDE Bridge Health & Self-Healing**\n"
        f"• Статус моста: `Active / Healthy`\n"
        f"• Самовосстановление: {heal_info}\n"
        f"• Очередь `inbox`: `{diag['pending_inbox_messages']} сообщ.`\n"
        f"• Голосовые ответы: {v_status}\n"
        f"• STT: Локальный Faster-Whisper GPU\n"
        f"• TTS: Модульный синтез речи\n"
        f"• IPC: Бессетевой файловый вотчер",
        chat_id=chat_id
    )
    return True

def handle_voice(chat_id: int | str, user: str, args: str = "") -> bool:
    from config import is_voice_enabled, set_voice_enabled
    parts = args.split()
    current = is_voice_enabled()
    if parts:
        arg = parts[0].lower()
        if arg in ["on", "1", "вкл", "включить", "true"]:
            set_voice_enabled(True)
            send_message("🔊 **Голосовое сопровождение ВКЛЮЧЕНО.**\nОтветы агента будут озвучиваться голосовыми сообщениями.", chat_id=chat_id)
            return True
        elif arg in ["off", "0", "выкл", "выключить", "false"]:
            set_voice_enabled(False)
            send_message("🔇 **Голосовое сопровождение ВЫКЛЮЧЕНО.**\nОтветы агента будут приходить только в текстовом виде.", chat_id=chat_id)
            return True
    new_state = not current
    set_voice_enabled(new_state)
    if new_state:
        send_message("🔊 **Голосовое сопровождение ВКЛЮЧЕНО.**\nОтветы агента будут озвучиваться голосовыми сообщениями.", chat_id=chat_id)
    else:
        send_message("🔇 **Голосовое сопровождение ВЫКЛЮЧЕНО.**\nОтветы агента будут приходить только текстом.", chat_id=chat_id)
    return True

def handle_limits(chat_id: int | str, user: str, args: str = "") -> bool:
    from limits_checker import format_limits_report
    send_message(format_limits_report(), chat_id=chat_id)
    return True

def handle_tasks(chat_id: int | str, user: str, args: str = "") -> bool:
    from tasks_checker import get_background_tasks_report
    send_message(get_background_tasks_report(), chat_id=chat_id)
    return True

def handle_screen(chat_id: int | str, user: str, args: str = "") -> bool:
    media_dir = os.path.join(os.path.dirname(__file__), "media")
    os.makedirs(media_dir, exist_ok=True)
    shot_path = os.path.join(media_dir, "desktop_real.png")
    with ActionKeeper("upload_photo", chat_id):
        try:
            shot_file = capture_desktop(shot_path)
            send_photo(shot_file, caption="📸 Скриншот рабочего стола", chat_id=chat_id)
        except Exception as e:
            send_message(f"❌ Ошибка захвата экрана: {e}", chat_id=chat_id)
    return True

def handle_free_memory(chat_id: int | str, user: str, args: str = "") -> bool:
    stop_comfyui_process()
    send_message("🧹 **Память и фоновые модели освобождены!**\nВсе тяжелые процессы выгружены из VRAM и RAM.", chat_id=chat_id)
    return True

def handle_approval(clean_text: str, chat_id: int | str, user: str) -> bool:
    """Обработка удаленного подтверждения ТОЛЬКО при наличии активного запроса от IDE."""
    if clean_text in APPROVAL_AFFIRMATIVE or clean_text in APPROVAL_NEGATIVE:
        try:
            from remote_approval_manager import get_pending_approval, resolve_approval
            pending = get_pending_approval()
            if pending:
                decision = clean_text in APPROVAL_AFFIRMATIVE
                resolve_approval(decision)
                res_str = "✅ **Действие подтверждено!** Передано в IDE на исполнение." if decision else "❌ **Действие отклонено.** Отменено в IDE."
                send_message(res_str, chat_id=chat_id)
                push_message({
                    "source": "REMOTE_APPROVAL",
                    "chat_id": chat_id,
                    "user": user,
                    "action": pending.get("action"),
                    "approved": decision,
                    "text": f"[{'✅ ПОДТВЕРЖДЕНО' if decision else '❌ ОТКЛОНЕНО'} через Telegram]: «{pending.get('action')}»",
                    "timestamp": time.time()
                })
                return True
        except Exception as e:
            print(f"[Remote Approval Error] {e}", file=sys.stderr)
    return False

# Строгая таблица слэш-команд
SLASH_COMMAND_MAP = {
    "/new": handle_new,
    "/reset": handle_new,
    "/start": handle_help,
    "/help": handle_help,
    "/status": handle_status,
    "/heal": handle_status,
    "/voice": handle_voice,
    "/limits": handle_limits,
    "/quota": handle_limits,
    "/tasks": handle_tasks,
    "/screen": handle_screen,
    "/screenshot": handle_screen,
    "/free": handle_free_memory,
    "/unload": handle_free_memory,
}

def dispatch_command(clean_text: str, chat_id: int | str, user: str) -> bool:
    """
    Проверяет, является ли текст системной слэш-командой или активным подтверждением.
    Возвращает True, если команда обработана, иначе False (сообщение идёт в IDE).
    """
    # 1. Проверяем интерактивное подтверждение действия
    if handle_approval(clean_text, chat_id, user):
        return True

    # 2. Строгий фильтр: системными командами могут быть ТОЛЬКО строки с префиксом '/'
    if not clean_text.startswith("/"):
        return False

    # Точное совпадение
    if clean_text in SLASH_COMMAND_MAP:
        return SLASH_COMMAND_MAP[clean_text](chat_id, user, "")

    # Совпадение по первому слову (например, "/voice off")
    base_cmd = clean_text.split()[0]
    if base_cmd in SLASH_COMMAND_MAP:
        args = clean_text[len(base_cmd):].strip()
        return SLASH_COMMAND_MAP[base_cmd](chat_id, user, args)

    return False
