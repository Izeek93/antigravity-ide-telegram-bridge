import urllib.request
import json
import sys
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import TG_BOT_TOKEN, get_active_chat_id
from tg_formatter import md_to_tg_html

test_cases = [
    ("**Жирный заголовок**", ["bold"]),
    ("*Курсивный текст*", ["italic"]),
    ("`строка_кода`", ["code"]),
    ("```bash\nssh-keygen -t ed25519\n```", ["pre"]),
    ("[Ссылка на GitHub](https://github.com)", ["text_link"]),
    ("<code>HTML код</code> и <a href=\"https://github.com\">HTML ссылка</a>", ["code", "text_link"]),
    ("Смешанный: **Жирный** с `кодом` и [ссылкой](https://github.com) & <опасные символы>", ["bold", "code", "text_link"])
]

chat_id = get_active_chat_id()
print(f"Running automated formatting verification against Telegram API (chat_id: {chat_id})...\n")

all_passed = True
for text, expected in test_cases:
    formatted = md_to_tg_html(text)
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": formatted, "parse_mode": "HTML"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            res = data.get("result", {})
            entities = [e.get("type") for e in res.get("entities", [])]
            msg_id = res.get("message_id")
            
            # Verify expected entity types are present
            missing = [exp for exp in expected if exp not in entities]
            if missing:
                print(f"❌ FAIL: {text}\n  Expected: {expected}\n  Got entities: {entities}\n  Formatted: {formatted}")
                all_passed = False
            else:
                print(f"✅ PASS: {text[:35]:<35} -> Entities: {entities}")

            # Delete the test message immediately to keep the chat clean
            del_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/deleteMessage"
            del_payload = {"chat_id": chat_id, "message_id": msg_id}
            del_req = urllib.request.Request(del_url, data=json.dumps(del_payload).encode(), headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(del_req, timeout=5)
            except Exception:
                pass
    except Exception as e:
        print(f"❌ HTTP ERROR on \"{text}\": {e}")
        all_passed = False

if all_passed:
    print("\n🎉 ALL 7 TEST CASES PASSED WITH 100% SUCCESS!")
else:
    print("\n⚠️ SOME TEST CASES FAILED!")
    sys.exit(1)
