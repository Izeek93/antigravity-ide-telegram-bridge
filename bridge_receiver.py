"""
tg-bot/bridge_receiver.py
=========================
Локальный файловый приёмник и триггер пробуждения IDE без использования сетевых портов.
- Не открывает никаких TCP-портов (0% риска конфликта портов).
- Блокирующе ждёт появления новых сообщений в inbox.json.
- При появлении сообщения выводит его в консоль и завершает процесс, мгновенно пробуждая агента в IDE.
"""

import os
import sys
import time
import json

# Принудительный UTF-8 вывод на консоли Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import set_active_chat
from queue_manager import pop_messages

def print_messages(messages: list):
    if not messages:
        return
    print("\n" + "="*55)
    print(f"📥 INCOMING MESSAGES ({len(messages)} message(s)):")
    for idx, msg in enumerate(messages, start=1):
        source = msg.get("source", "TELEGRAM")
        chat_id = msg.get("chat_id")
        user = msg.get("user", "Unknown")
        text = msg.get("text", "")
        if source == "TELEGRAM" and chat_id:
            set_active_chat(chat_id, {"username": user})
        print(f"[{idx}] [{source}] From: {user} (ID: {chat_id})")
        print(f"    Message: {text}\n")
    print("="*55 + "\n", flush=True)

def print_incident(incident: dict):
    print("\n" + "!"*60)
    print(f"🚨 AUTONOMOUS INCIDENT ALERT from [{incident.get('service', 'BRIDGE')}]:")
    print(f"   Error: {incident.get('error')}")
    if incident.get('traceback'):
        print(f"   Traceback:\n{incident.get('traceback')}")
    print("!"*60 + "\n", flush=True)

def check_incidents():
    """Проверка очереди критических инцидентов из файлов incidents.json."""
    for base_p in [os.path.dirname(__file__), os.path.join(os.path.dirname(__file__), "..", "vk-bot")]:
        inc_file = os.path.join(base_p, "incidents.json")
        if os.path.exists(inc_file):
            try:
                with open(inc_file, "r", encoding="utf-8") as f:
                    incidents = json.load(f)
                if incidents:
                    for inc in incidents:
                        print_incident(inc)
                    with open(inc_file, "w", encoding="utf-8") as f:
                        json.dump([], f)
                    return True
            except Exception:
                pass
    return False

def main():
    # 1. Быстрая проверка инцидентов
    if check_incidents():
        sys.exit(0)

    # 2. Непрерывный легковесный вотчер очереди (без сетевых сокетов)
    while True:
        messages = pop_messages()
        if messages:
            print_messages(messages)
            sys.exit(0)

        if check_incidents():
            sys.exit(0)

        time.sleep(0.2)

if __name__ == "__main__":
    main()
