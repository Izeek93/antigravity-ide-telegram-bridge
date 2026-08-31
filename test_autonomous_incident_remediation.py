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

import incident_manager

class TestAutonomousIncidentSystem(unittest.TestCase):

    def test_01_incident_reporting_fallback(self):
        """Test that incident manager safely queues alerts if receiver is offline."""
        incidents_file = os.path.join(os.path.dirname(incident_manager.__file__), "incidents.json")
        if os.path.exists(incidents_file):
            try:
                os.remove(incidents_file)
            except Exception:
                pass

        # Report simulated VK and TG errors
        incident_manager.report_bridge_incident("VK_TEST", "Simulated Photo Upload Failure 100", "Traceback line 42")
        incident_manager.report_bridge_incident("TG_TEST", "Simulated Telegram 502 Bad Gateway", "Traceback line 88")

        self.assertTrue(os.path.exists(incidents_file), "Incidents file should be created as fallback queue")
        with open(incidents_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["service"], "VK_TEST")
        self.assertEqual(data[1]["service"], "TG_TEST")

        # Cleanup
        try:
            os.remove(incidents_file)
        except Exception:
            pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
