import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import http.server
import socketserver
import time
from config import RECEIVER_PORT, set_active_chat
from queue_manager import pop_messages

def print_messages(messages: list):
    if not messages:
        return
    print("\n" + "="*55)
    print(f"📥 TELEGRAM INCOMING ({len(messages)} message(s)):")
    for idx, msg in enumerate(messages, start=1):
        chat_id = msg.get("chat_id")
        user = msg.get("user", "Unknown")
        text = msg.get("text", "")
        if chat_id:
            set_active_chat(chat_id, {"username": user})
        print(f"[{idx}] From: @{user} (Chat ID: {chat_id})")
        print(f"    Message: {text}\n")
    print("="*55 + "\n", flush=True)

def print_incident(incident: dict):
    print("\n" + "!"*60)
    print(f"🚨 AUTONOMOUS INCIDENT ALERT from [{incident.get('service', 'BRIDGE')}]:")
    print(f"   Error: {incident.get('error')}")
    if incident.get('traceback'):
        print(f"   Traceback:\n{incident.get('traceback')}")
    print("!"*60 + "\n", flush=True)

class ReceiverHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = b""
        if content_length > 0:
            post_data = self.rfile.read(content_length)
            
        incident = None
        if post_data:
            try:
                parsed = json.loads(post_data.decode("utf-8"))
                if isinstance(parsed, dict) and parsed.get("type") == "CRITICAL_INCIDENT":
                    incident = parsed
            except Exception:
                pass

        if incident:
            print_incident(incident)
        else:
            messages = pop_messages()
            print_messages(messages)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "delivered_to_ide"}')

        def shutdown():
            time.sleep(0.05)
            os._exit(0)
            
        import threading
        threading.Thread(target=shutdown).start()

    def do_GET(self):
        self.do_POST()

    def log_message(self, format, *args):
        pass

def main():
    # 1. Check for pending incident files
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
                    sys.exit(0)
            except Exception:
                pass

    # 2. Check queue immediately on startup
    pending = pop_messages()
    if pending:
        print_messages(pending)
        sys.exit(0)

    # 3. Wait for HTTP trigger if queue was empty
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("127.0.0.1", RECEIVER_PORT), ReceiverHandler) as httpd:
            print(f"[Receiver] Queue empty. Listening on port {RECEIVER_PORT}...", flush=True)
            httpd.serve_forever()
    except OSError as e:
        print(f"[Receiver] Port {RECEIVER_PORT} error: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
