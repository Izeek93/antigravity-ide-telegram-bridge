import unittest
import os
import sys
import json
import time

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import config
import tg_formatter
import queue_manager
import screenshot
import limits_checker
import tasks_checker
import voice_engine
import send_tg

class TestTelegramBridgeSuite(unittest.TestCase):
    
    def test_01_config_and_voice_settings(self):
        """Test configuration loading and dynamic voice preference toggle."""
        self.assertTrue(len(config.TG_BOT_TOKEN) > 10, "Bot token should be loaded from .env")
        
        orig = config.is_voice_enabled()
        config.set_voice_enabled(False)
        self.assertFalse(config.is_voice_enabled(), "Voice should be disabled")
        config.set_voice_enabled(True)
        self.assertTrue(config.is_voice_enabled(), "Voice should be enabled")
        config.set_voice_enabled(orig)

    def test_02_tg_formatter(self):
        """Test Markdown-to-HTML formatter edge cases and safety."""
        sample_md = "**Bold** and *Italic* and `code` and [Link](https://google.com)"
        html = tg_formatter.md_to_tg_html(sample_md)
        self.assertIn("<b>Bold</b>", html)
        self.assertIn("<i>Italic</i>", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn('<a href="https://google.com">Link</a>', html)

        # Header conversion
        header_md = "# Header 1\n## Header 2"
        h_html = tg_formatter.md_to_tg_html(header_md)
        self.assertIn("<b>Header 1</b>", h_html)

    def test_03_queue_manager(self):
        """Test FIFO Queue operations (push, pop_messages)."""
        # Drain queue first
        queue_manager.pop_messages()

        payload1 = {"chat_id": 1001, "user": "test_user", "text": "Hello 1", "timestamp": time.time()}
        payload2 = {"chat_id": 1001, "user": "test_user", "text": "Hello 2", "timestamp": time.time()}

        queue_manager.push_message(payload1)
        queue_manager.push_message(payload2)

        messages = queue_manager.pop_messages()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["text"], "Hello 1")
        self.assertEqual(messages[1]["text"], "Hello 2")

        # After pop, inbox should be empty
        self.assertEqual(len(queue_manager.pop_messages()), 0)

    def test_04_limits_checker(self):
        """Test limits and quota reporting format."""
        report = limits_checker.format_limits_report()
        self.assertIsInstance(report, str)
        self.assertIn("Gemini", report)
        self.assertTrue(len(report) > 50)

    def test_05_tasks_checker(self):
        """Test background tasks checker."""
        report = tasks_checker.get_background_tasks_report()
        self.assertIsInstance(report, str)
        self.assertIn("фоновые", report.lower())

    def test_06_voice_phonetics(self):
        """Test phonetic replacement engine for clean natural speech."""
        text = "Тестируем Whisper, RTX 3060, LoRA, ComfyUI и OpenAI."
        clean = voice_engine.clean_and_normalize_for_speech(text)
        self.assertIn("Виспер", clean)
        self.assertIn("тридцать шестьдесят", clean)
        self.assertIn("Комфи Ю Ай", clean)
        self.assertIn("Опен Эй Ай", clean)

    def test_07_telegram_api_connection(self):
        """Test live connection to Telegram Bot API."""
        me = send_tg.tg_api_post("getMe", {})
        self.assertTrue(me.get("ok"), f"Telegram getMe failed: {me}")
        result = me.get("result", {})
        self.assertIn("username", result)
        self.assertTrue(result.get("is_bot"))

    def test_08_desktop_screenshot_capture(self):
        """Test desktop screenshot capture function."""
        test_shot = "test_screen_capture.png"
        try:
            out = screenshot.capture_desktop(test_shot)
            self.assertTrue(os.path.exists(out), "Screenshot file should exist")
            self.assertTrue(os.path.getsize(out) > 1000, "Screenshot file should not be empty")
        finally:
            if os.path.exists(test_shot):
                os.remove(test_shot)

    def test_09_command_dispatch_simulation(self):
        """Simulate command handling logic to prevent syntax or runtime crashes."""
        test_commands = [
            "/start", "/help", "/status", "/limits", "/tasks", "/voice", "/voice on", "/voice off"
        ]
        from tg_bridge import handle_message
        
        chat_id = config.get_active_chat_id() or 1059761599
        # Test simulated command messages
        for cmd in test_commands:
            sim_msg = {
                "message_id": 99999,
                "from": {"id": chat_id, "username": "test_dev"},
                "chat": {"id": chat_id, "type": "private"},
                "date": int(time.time()),
                "text": cmd
            }
            # Mock send_message to avoid spamming actual TG
            orig_send = send_tg.send_message
            try:
                send_tg.send_message = lambda *args, **kwargs: {"ok": True}
                handle_message(sim_msg)
            finally:
                send_tg.send_message = orig_send

if __name__ == "__main__":
    unittest.main(verbosity=2)
