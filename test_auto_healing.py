import unittest
import os
import sys
import time
import json

# Ensure UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import bridge_health_watchdog as watchdog
import queue_manager

class TestAutoHealingSystem(unittest.TestCase):

    def test_01_stale_lock_recovery(self):
        """Test that watchdog automatically removes stale lock files."""
        # Create simulated stale lock file
        lock_path = watchdog.LOCK_FILE
        with open(lock_path, "w") as f:
            f.write("stale_pid_99999")
            
        # Artificially age the file
        past_time = time.time() - 10.0
        os.utime(lock_path, (past_time, past_time))
        
        self.assertTrue(os.path.exists(lock_path), "Stale lock file should exist before check")
        
        # Trigger watchdog healing
        healed = watchdog.check_and_heal_lock_file(max_age_seconds=2.0)
        self.assertTrue(healed, "Watchdog should report lock healed")
        self.assertFalse(os.path.exists(lock_path), "Stale lock file should be removed")

    def test_02_health_check_routine(self):
        """Test full self-healing health check routine."""
        report = watchdog.run_self_healing_health_check()
        self.assertEqual(report["status"], "healthy")
        self.assertIn("lock_healed", report)
        self.assertIn("inbox_healed", report)

    def test_03_queue_recovery_under_stress(self):
        """Test queue operations survive simulated crashes."""
        queue_manager.pop_messages()
        
        # Push message
        queue_manager.push_message({"chat_id": 12345, "user": "tester", "text": "Stress test", "timestamp": time.time()})
        
        # Simulate lock collision
        with open(watchdog.LOCK_FILE, "w") as f:
            f.write("crash")
        past_time = time.time() - 10.0
        os.utime(watchdog.LOCK_FILE, (past_time, past_time))
        
        # Self-heal
        watchdog.run_self_healing_health_check()
        
        # Queue should be fully readable
        msgs = queue_manager.pop_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["text"], "Stress test")

if __name__ == "__main__":
    unittest.main(verbosity=2)
