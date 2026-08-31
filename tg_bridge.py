import os
import sys
import subprocess
import time
import json
import urllib.request
import urllib.parse
from google import genai
from google.genai import types

from config import TG_BOT_TOKEN, RECEIVER_PORT, set_active_chat, get_active_chat_id
from send_tg import (
    send_message, send_photo, send_chat_action, ActionKeeper,
    set_bot_commands, REMOVE_REPLY_KEYBOARD
)
from screenshot import capture_desktop
from queue_manager import push_message
from local_stt import transcribe_local_whisper
from model_lifecycle import ensure_watchdog_running, stop_comfyui_process

GEMINI_API_KEY = "AQ.Ab8RN6LLCCbG03IZkv8PAv1HeBmLZCpyvgFdcquKNeyaxg3jjw"
genai_client = genai.Client(api_key=GEMINI_API_KEY)

def tg_api_call(method: str, params: dict = None) -> dict:
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    if params:
        data = json.dumps(params).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[Telegram API Error] {method}: {e}", file=sys.stderr)
        return {"ok": False, "error": str(e)}

def download_telegram_file(file_id: str, dest_path: str, max_retries: int = 3) -> bool:
    info = tg_api_call("getFile", {"file_id": file_id})
    if not info.get("ok"):
        return False
    file_path = info.get("result", {}).get("file_path")
    if not file_path:
        return False
    download_url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_path}"
    
    # 1. First try system curl.exe (most resilient to DPI and latency)
    try:
        cmd = ["curl.exe", "-sSL", "--retry", "3", "--retry-delay", "1", "--connect-timeout", "15", "--max-time", "60", "-o", dest_path, download_url]
        res = subprocess.run(cmd, capture_output=True, timeout=70)
        if res.returncode == 0 and os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            return True
    except Exception as e:
        print(f"[Download via curl.exe failed]: {e}", file=sys.stderr)
        
    # 2. Fallback to urllib streaming
    import time
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                return True
        except Exception as e:
            print(f"[Download Attempt {attempt}/{max_retries} Failed]: {e}", file=sys.stderr)
            time.sleep(1.5 * attempt)
            
    return False



def transcribe_audio_file(audio_path: str) -> str:
    # 1. First try local faster-whisper on GPU (large-v3-turbo)
    try:
        text = transcribe_local_whisper(audio_path, model_size="large-v3-turbo")
        if text and len(text.strip()) > 0:
            print(f"[STT Local Faster-Whisper] {text}")
            return text.strip()
    except Exception as e:
        print(f"[STT Local Whisper Error] {e}, falling back to Gemini...", file=sys.stderr)

    # 2. Fallback to Gemini
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        mime_type = "audio/ogg" if (audio_path.endswith(".ogg") or audio_path.endswith(".oga")) else "audio/mp3"
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        for model_name in ["gemini-3.6-flash", "gemini-3.5-flash"]:
            try:
                response = genai_client.models.generate_content(
                    model=model_name,
                    contents=[
                        audio_part,
                        "Расшифруй это голосовое сообщение на русском языке в точности как сказано. Выведи только распознанный текст без кавычек и лишних комментариев."
                    ]
                )
                if response.text and response.text.strip():
                    return response.text.strip()
            except Exception as e:
                print(f"STT model {model_name} error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"STT Fallback Error: {e}", file=sys.stderr)
    return ""

def trigger_ide_receiver():
    url = f"http://127.0.0.1:{RECEIVER_PORT}"
    req = urllib.request.Request(url, data=b"{}", headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass

def handle_message(msg: dict):
    chat_id = msg.get("chat", {}).get("id")
    user = msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name", "User")
    text = (msg.get("text") or msg.get("caption") or "").strip()

    if not chat_id:
        return

    set_active_chat(chat_id, {"username": user})

    # 0. Handle Telegram Quotes / Replies (reply_to_message)
    reply_prefix = ""
    reply_msg = msg.get("reply_to_message")
    if reply_msg:
        # If user replied to a voice / audio message
        if "voice" in reply_msg or "audio" in reply_msg:
            v_info = reply_msg.get("voice") or reply_msg.get("audio")
            v_fid = v_info.get("file_id")
            timestamp = int(time.time())
            os.makedirs(os.path.join(os.path.dirname(__file__), "media"), exist_ok=True)
            dest_voice = os.path.join(os.path.dirname(__file__), "media", f"reply_voice_{timestamp}.ogg")
            if download_telegram_file(v_fid, dest_voice):
                transcribed = transcribe_audio_file(dest_voice)
                if transcribed:
                    reply_prefix = f"↳ [В ответ на голосовое сообщение]: «{transcribed}»\n"
                else:
                    reply_prefix = "↳ [В ответ на голосовое сообщение]\n"
            else:
                reply_prefix = "↳ [В ответ на голосовое сообщение]\n"
        # If user replied to a text message
        elif "text" in reply_msg:
            quoted = reply_msg["text"].strip()
            if len(quoted) > 150:
                quoted = quoted[:150] + "..."
            reply_prefix = f"↳ [В ответ на: «{quoted}»]\n"
        # If user replied to a photo
        elif "photo" in reply_msg:
            cap = reply_msg.get("caption", "").strip()
            cap_str = f" («{cap}»)" if cap else ""
            reply_prefix = f"↳ [В ответ на фото/скриншот{cap_str}]\n"
        # If user replied to a document
        elif "document" in reply_msg:
            doc_n = reply_msg.get("document", {}).get("file_name", "документ")
            reply_prefix = f"↳ [В ответ на документ «{doc_n}»]\n"

    # 1. Handle incoming photos & screenshots
    if "photo" in msg:
        photo_sizes = msg.get("photo", [])
        if photo_sizes:
            largest_photo = photo_sizes[-1]
            file_id = largest_photo.get("file_id")
            timestamp = int(time.time())
            photo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"incoming_photo_{timestamp}.png"))
            
            with ActionKeeper("upload_photo", chat_id):
                if download_telegram_file(file_id, photo_path):
                    caption = msg.get("caption", "").strip()
                    caption_str = f" с комментарием: «{caption}»" if caption else ""
                    text = f"[📸 Входящий скриншот/фото]: сохранён в `{photo_path}`{caption_str}"
                    send_message(f"📥 Скриншот успешно получен и передан в IDE!{caption_str}", chat_id=chat_id)
                else:
                    send_message("❌ Ошибка при сохранении входящего скриншота.", chat_id=chat_id)
                    return

    # 2. Handle incoming files & documents
    elif "document" in msg:
        doc_info = msg.get("document", {})
        file_id = doc_info.get("file_id")
        orig_name = doc_info.get("file_name", f"doc_{int(time.time())}.dat")
        dest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"incoming_{orig_name}"))
        
        with ActionKeeper("upload_document", chat_id):
            if download_telegram_file(file_id, dest_path):
                caption = msg.get("caption", "").strip()
                caption_str = f" (комментарий: «{caption}»)" if caption else ""
                text = f"[📄 Входящий файл]: сохранён в `{dest_path}`{caption_str}"
                send_message(f"📥 Файл `{orig_name}` успешно сохранён и передан в IDE!", chat_id=chat_id)
            else:
                send_message("❌ Ошибка при загрузке документа.", chat_id=chat_id)
                return

    # 3. Handle voice / audio messages
    elif "voice" in msg or "audio" in msg:
        audio_info = msg.get("voice") or msg.get("audio")
        file_id = audio_info.get("file_id")
        
        # Start continuous voice indicator while processing STT
        with ActionKeeper("record_voice", chat_id):
            timestamp = int(time.time())
            voice_file = os.path.join(os.path.dirname(__file__), f"voice_{timestamp}.ogg")
            if download_telegram_file(file_id, voice_file):
                transcribed = transcribe_audio_file(voice_file)
                if transcribed:
                    text = f"[🎙 Голосовое сообщение]: {transcribed}"
                else:
                    send_message("❌ Не удалось распознать голосовое сообщение.", chat_id=chat_id)
                    return
            else:
                send_message("❌ Ошибка загрузки голосового сообщения.", chat_id=chat_id)
                return

    if reply_prefix:
        text = f"{reply_prefix}\n{text}".strip()

    clean_text = (msg.get("text") or msg.get("caption") or "").strip().lower()

    # Fast built-in button & command handlers (checked on clean_text)
    if clean_text in ["/start", "/help", "help", "старт", "помощь"]:
        send_message(
            "👋 Привет! Этот бот работает как **прямое зеркало активной сессии Antigravity IDE**.\n\n"
            "📌 Команды в нативном меню **`[ Menu ☰ ]`**:\n"
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
        return

    if clean_text in ["/status", "📊 статус ide", "статус ide", "статус", "/heal", "диагностика", "error", "ошибка"]:
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
            f"• Связь с IDE: `127.0.0.1:8080 (Active)`",
            chat_id=chat_id
        )
        return

    if clean_text.startswith("/voice") or clean_text in ["голос", "озвучка", "звук"]:
        from config import is_voice_enabled, set_voice_enabled
        parts = clean_text.split()
        current = is_voice_enabled()
        if len(parts) > 1:
            arg = parts[1].lower()
            if arg in ["on", "1", "вкл", "включить", "true"]:
                set_voice_enabled(True)
                send_message("🔊 **Голосовое сопровождение ВКЛЮЧЕНО.**\nОтветы агента будут озвучиваться голосовыми сообщениями.", chat_id=chat_id)
                return
            elif arg in ["off", "0", "выкл", "выключить", "false"]:
                set_voice_enabled(False)
                send_message("🔇 **Голосовое сопровождение ВЫКЛЮЧЕНО.**\nОтветы агента будут приходить только в текстовом виде.", chat_id=chat_id)
                return
        # Toggle current state
        new_state = not current
        set_voice_enabled(new_state)
        if new_state:
            send_message("🔊 **Голосовое сопровождение ВКЛЮЧЕНО.**\nОтветы агента будут озвучиваться голосовыми сообщениями.", chat_id=chat_id)
        else:
            send_message("🔇 **Голосовое сопровождение ВЫКЛЮЧЕНО.**\nОтветы агента будут приходить только текстом.", chat_id=chat_id)
        return

    if clean_text in ["/limits", "/quota", "лимиты", "квоты", "остаток", "⏳ лимиты и квоты"]:
        from limits_checker import format_limits_report
        rep = format_limits_report()
        send_message(rep, chat_id=chat_id)
        return

    if clean_text in ["/tasks", "задачи", "процессы", "фоновые задачи", "⚙️ фоновые задачи"]:
        from tasks_checker import get_background_tasks_report
        rep = get_background_tasks_report()
        send_message(rep, chat_id=chat_id)
        return

    if clean_text in ["/free", "/unload", "освободи память", "выгрузи модели", "очисти память"]:
        stop_comfyui_process()
        send_message("🧹 **Память и фоновые модели освобождены!**\nВсе тяжелые процессы выгружены из VRAM и RAM.", chat_id=chat_id)
        return

    if clean_text in ["/screen", "/screenshot", "скрин", "скриншот", "пришли скрин", "пришли скриншот", "📸 скриншот экрана"]:
        with ActionKeeper("upload_photo", chat_id):
            try:
                shot_file = capture_desktop("desktop_real.png")
                send_photo(shot_file, caption="📸 Скриншот рабочего стола", chat_id=chat_id)
            except Exception as e:
                send_message(f"❌ Ошибка захвата экрана: {e}", chat_id=chat_id)
        return

    if clean_text in ["📁 файлы проекта", "/files", "файлы"]:
        msg_files = (
            "📁 <b>Архитектура проекта Telegram Bridge:</b>\n\n"
            "🟢 <b>Ядро и мост:</b>\n"
            "• <code>tg_bridge.py</code> — Основной сервис-демон\n"
            "• <code>send_tg.py</code> & <code>tg_formatter.py</code> — Отправка и HTML-форматирование\n"
            "• <code>queue_manager.py</code> — Гарантированная FIFO-очередь\n\n"
            "🧠 <b>Центральный AI-стек (shared_ai):</b>\n"
            "• <code>voice_engine.py</code> — Модульный синтез речи (TTS)\n"
            "• <code>local_stt.py</code> — Локальный Faster-Whisper GPU\n"
            "• <code>model_lifecycle.py</code> — Watchdog авто-выгрузки памяти (5 мин)\n\n"
            "📊 <b>Мониторинг и утилиты:</b>\n"
            "• <code>limits_checker.py</code> — Квоты Gemini API и VRAM\n"
            "• <code>tasks_checker.py</code> — Статус фоновых процессов\n"
            "• <code>screenshot.py</code> — Захват экранов ПК\n"
            "• <code>media/</code> — Изолированная папка вложений"
        )
        send_message(msg_files, chat_id=chat_id, raw=True)
        return

    # Put normal user message into guaranteed FIFO Queue for IDE Agent
    payload = {
        "chat_id": chat_id,
        "user": user,
        "text": text,
        "timestamp": time.time()
    }
    push_message(payload)
    send_chat_action("typing", chat_id=chat_id)
    trigger_ide_receiver()

def run_bridge():
    print("Starting Telegram <-> Antigravity IDE Bridge Daemon (Full Media + Status Indicators)...")
    me = tg_api_call("getMe")
    if not me.get("ok"):
        print(f"Failed to connect to Telegram Bot API: {me}", file=sys.stderr)
        sys.exit(1)

    bot_username = me.get("result", {}).get("username", "Bot")
    print(f"Connected to @{bot_username}")

    # Register native Bot Commands menu in Telegram client
    set_bot_commands()
    ensure_watchdog_running()

    offset = None
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            updates = tg_api_call("getUpdates", params)
            if updates.get("ok"):
                for upd in updates.get("result", []):
                    offset = upd.get("update_id") + 1
                    if "message" in upd:
                        handle_message(upd["message"])
                    elif "callback_query" in upd:
                        cb = upd["callback_query"]
                        cb_id = cb.get("id")
                        cb_data = cb.get("data")
                        tg_api_call("answerCallbackQuery", {"callback_query_id": cb_id})
                        msg_from_cb = {
                            "chat": cb.get("message", {}).get("chat", {}),
                            "from": cb.get("from", {}),
                            "text": cb_data
                        }
                        handle_message(msg_from_cb)
            else:
                time.sleep(3)
        except Exception as e:
            print(f"[Bridge Loop Error] {e}", file=sys.stderr)
            try:
                from incident_manager import report_bridge_incident
                report_bridge_incident("TG_BRIDGE", str(e))
            except Exception:
                pass
            time.sleep(3)

if __name__ == "__main__":
    run_bridge()
