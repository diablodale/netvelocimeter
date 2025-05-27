"""Tests for CLI main and global options."""

from pathlib import Path
import subprocess
import sys
import unittest


class TestMainModule(unittest.TestCase):
    """Test cases for the main module of NetVelocimeter."""

    def test_main_module_runs(self):
        """Test that the main module can be run as a script."""
        pkg_dir = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "netvelocimeter", "--help"],
            cwd=str(pkg_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertRegex(
            result.stdout, r"Usage:(.|\n)+--help(.|\n)+--config-root(.|\n)+--version(.|\n)+server"
        )
