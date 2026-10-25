import subprocess
import sys
import unittest
from pathlib import Path


class MT4AutoTraderSafetyTests(unittest.TestCase):
    def test_demo_only_ea_static_safety_checks(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "validate_mt4_ea.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not a MetaEditor compile", result.stdout)


if __name__ == "__main__":
    unittest.main()
