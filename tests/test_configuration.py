"""Regression tests for configuration that must not silently become unsafe."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from django.test import override_settings

from detector.services.openrouter_client import _load_api_key

ROOT = Path(__file__).resolve().parent.parent


class ConfigurationTests(unittest.TestCase):
    def _import_with_settings(self, debug, secret):
        env = {**os.environ, "DEBUG": debug, "DJANGO_SECRET_KEY": secret}
        return subprocess.run(
            [sys.executable, "-c", "import fake_checker.settings"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_non_debug_mode_rejects_missing_secret(self):
        self.assertNotEqual(self._import_with_settings("False", "").returncode, 0)

    def test_non_debug_mode_rejects_placeholder_secret(self):
        self.assertNotEqual(self._import_with_settings("False", "change-me").returncode, 0)

    def test_non_debug_mode_accepts_configured_secret(self):
        result = self._import_with_settings("False", "example-not-a-real-production-secret-123456")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_local_debug_mode_can_use_dev_fallback(self):
        result = self._import_with_settings("True", "")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_txt_file_is_never_used_for_api_key(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "txt").write_text("old-key-should-not-load", encoding="utf-8")
            with override_settings(BASE_DIR=Path(folder), OPENROUTER_API_KEY=""):
                self.assertEqual(_load_api_key(), "")

    def test_explicit_openrouter_api_key_is_used(self):
        with override_settings(OPENROUTER_API_KEY="  local-demo-key  "):
            self.assertEqual(_load_api_key(), "local-demo-key")


if __name__ == "__main__":
    unittest.main()
