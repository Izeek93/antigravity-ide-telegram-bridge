import os
import sys
import unittest
import json
import time

tg_dir = os.path.dirname(os.path.abspath(__file__))
if tg_dir not in sys.path:
    sys.path.insert(0, tg_dir)
shared_dir = os.path.abspath(os.path.join(tg_dir, "..", "shared_ai"))
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from remote_approval_manager import request_remote_approval, resolve_approval, get_pending_approval, APPROVAL_FILE

class TestRemoteApproval(unittest.TestCase):
    def setUp(self):
        if os.path.exists(APPROVAL_FILE):
            try:
                os.remove(APPROVAL_FILE)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(APPROVAL_FILE):
            try:
                os.remove(APPROVAL_FILE)
            except Exception:
                pass

    def test_remote_approval_flow(self):
        req = request_remote_approval("Тестовое действие: деплой на прод")
        self.assertIsNotNone(req)
        self.assertEqual(req["status"], "PENDING")
        
        pending = get_pending_approval()
        self.assertIsNotNone(pending)
        self.assertEqual(pending["action"], "Тестовое действие: деплой на прод")

        # Resolve with approve
        res = resolve_approval(True)
        self.assertTrue(res)

        # Pending should now be cleared
        pending_after = get_pending_approval()
        self.assertIsNone(pending_after)

        # Check raw file status
        with open(APPROVAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "APPROVED")
        print("\n✅ Remote Approval autotest passed 100%!")

if __name__ == "__main__":
    unittest.main()
