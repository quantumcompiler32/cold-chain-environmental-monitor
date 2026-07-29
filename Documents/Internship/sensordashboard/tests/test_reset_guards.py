import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reset_demo.py"


class ResetGuardTests(unittest.TestCase):
    def run_reset(self, *args, **env_overrides):
        env = os.environ.copy()
        env.update(env_overrides)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_reset_requires_explicit_confirmation(self):
        result = self.run_reset(APP_ENV="development")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-reset", result.stderr)

    def test_reset_refuses_production_even_with_confirmation(self):
        result = self.run_reset("--confirm-reset", APP_ENV="production")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be development", result.stderr)

    def test_reset_refuses_non_local_host(self):
        result = self.run_reset("--confirm-reset", APP_ENV="demo", POSTGRES_HOST="database.example")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-local PostgreSQL host", result.stderr)


if __name__ == "__main__":
    unittest.main()
