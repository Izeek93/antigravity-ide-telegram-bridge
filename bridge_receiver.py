import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

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

class ReceiverHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
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
    # 1. Check queue immediately on startup
    pending = pop_messages()
    if pending:
        print_messages(pending)
        sys.exit(0)

    # 2. Wait for HTTP trigger if queue was empty
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
